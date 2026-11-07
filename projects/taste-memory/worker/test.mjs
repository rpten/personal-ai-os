import test from "node:test";
import assert from "node:assert/strict";
import { handle, parseSuggestions, parsePicks, cleanProfile, cleanMessages, ALLOWED_ORIGIN } from "./index.js";

const profile = cleanProfile({ loved: [{ title: "Parasita", year: 2019, rating: 5 }, { title: "Cidade de Deus", year: 2002, rating: 4.5 }], disliked: [{ title: "Ruim", rating: 1 }], seen: ["Parasita", "Cidade de Deus", "Ruim"], wants: ["Quero Este"], nos: ["Nao Curto"] });
const req = (path, body, o = {}) => new Request("https://w.example" + path, { method: "POST", headers: { Origin: ALLOWED_ORIGIN, "Content-Type": "application/json", ...o.headers }, body: JSON.stringify(body), ...o });
const gem = (text, status = 200) => async (url, init) => { gem.calls.push({ url, init }); return new Response(status === 200 ? JSON.stringify({ candidates: [{ content: { parts: [{ text }] } }] }) : "err", { status }); };
gem.calls = [];
const env = { GEMINI_API_KEY: "SEGREDO-TESTE" };
const sugs = JSON.stringify([
  { title: "Oldboy", year: 2003, synopsis: "Vingança.", why: "Você deu 5★ a Parasita e 4,5★ a Cidade de Deus.", refs: ["Parasita", "Cidade de Deus", "Filme Inventado"] },
  { title: "Parasita", year: 2019, synopsis: "x", why: "x", refs: [] },
  { title: "Quero Este", synopsis: "x", why: "x", refs: [] },
]);

test("recs: sinopse + porquê; refs só do histórico real com a nota real; já visto/quero/não curto são filtrados", async () => {
  const r = await handle(req("/recs", { type: "film", mood: "suspense", profile }), env, gem(sugs));
  assert.equal(r.status, 200);
  const { suggestions } = await r.json();
  assert.equal(suggestions.length, 1);
  assert.equal(suggestions[0].synopsis, "Vingança.");
  assert.deepEqual(suggestions[0].refs.map((x) => [x.title, x.rating]), [["Parasita", 5], ["Cidade de Deus", 4.5]]);
  const sent = gem.calls.at(-1);
  assert.equal(sent.init.headers["x-goog-api-key"], "SEGREDO-TESTE");
  assert.match(sent.init.body, /suspense/); assert.match(sent.init.body, /Parasita \(2019\) · nota 5\/5/);
  assert.ok(!sent.url.includes("SEGREDO"));
});

test("a chave nunca aparece na resposta ao navegador", async () => {
  const r = await handle(req("/recs", { type: "film", profile }), env, gem(sugs));
  assert.ok(!JSON.stringify([...r.headers]).includes("SEGREDO") && !(await r.text()).includes("SEGREDO"));
});

test("CORS: só https://rpten.github.io; outras origens e sem origem levam 403", async () => {
  const ok = await handle(new Request("https://w.example/recs", { method: "OPTIONS", headers: { Origin: ALLOWED_ORIGIN } }), env);
  assert.equal(ok.status, 204); assert.equal(ok.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN);
  for (const o of ["https://evil.example", "https://rpten.github.io.evil.com", null]) {
    const r = await handle(req("/recs", { type: "film", profile }, { headers: o ? { Origin: o } : {} }), env, gem(sugs));
    if (o === null) { const h = new Headers(); const r2 = await handle(new Request("https://w.example/recs", { method: "POST", headers: h, body: "{}" }), env, gem(sugs)); assert.equal(r2.status, 403); continue; }
    assert.equal(r.status, 403); assert.equal(r.headers.get("Access-Control-Allow-Origin"), null);
  }
});

test("chat: manda sinopse, gosto e histórico da conversa; devolve só o texto", async () => {
  const r = await handle(req("/chat", { type: "film", profile, suggestion: { title: "Oldboy", year: 2003, synopsis: "Vingança.", why: "Porque sim." },
    messages: [{ role: "user", text: "Não gosto de violência." }, { role: "model", text: "Entendo." }, { role: "user", text: "Tem algo mais leve?" }] }), env, gem("Tente Amélie."));
  assert.equal(r.status, 200); assert.deepEqual(await r.json(), { reply: "Tente Amélie." });
  const body = JSON.parse(gem.calls.at(-1).init.body);
  assert.deepEqual(body.contents.map((c) => c.role), ["user", "model", "user"]);
  assert.match(body.contents[0].parts[0].text, /Oldboy/); assert.match(body.contents[0].parts[0].text, /Parasita/);
});

test("erros: 429 vira mensagem amigável; chave recusada não vaza; JSON/tipo inválidos; sem chave", async () => {
  let r = await handle(req("/recs", { type: "film", profile }), env, gem("", 429));
  assert.equal(r.status, 429); assert.match((await r.json()).error, /Limite gratuito/);
  r = await handle(req("/recs", { type: "film", profile }), env, gem("", 403));
  assert.equal(r.status, 502); assert.match((await r.json()).error, /chave.*servidor/);
  r = await handle(req("/recs", { type: "xx", profile }), env, gem(sugs)); assert.equal(r.status, 400);
  r = await handle(req("/recs", { type: "film", profile }), {}, gem(sugs)); assert.equal(r.status, 500);
  r = await handle(req("/recs", { type: "film", profile }), env, gem("sem json")); assert.equal(r.status, 502);
  r = await handle(req("/chat", { type: "film", profile, suggestion: { title: "X" }, messages: [] }), env, gem("ok")); assert.equal(r.status, 400);
  r = await handle(new Request("https://w.example/recs", { method: "POST", headers: { Origin: ALLOWED_ORIGIN }, body: "x".repeat(260000) }), env, gem(sugs)); assert.equal(r.status, 413);
});

test("cleanMessages: limita a 12, começa por 'user', termina por 'user'", () => {
  const m = Array.from({ length: 20 }, (_, i) => ({ role: i % 2 ? "model" : "user", text: "m" + i }));
  const c = cleanMessages(m.slice(0, 19)); assert.ok(c.length <= 12); assert.equal(c[0].role, "user"); assert.equal(c.at(-1).role, "user");
  assert.throws(() => cleanMessages([{ role: "model", text: "x" }]));
});

test("M6 /pick: escolhe só do backlog (títulos inventados caem) e exige backlog", async () => {
  const picks = JSON.stringify([{ title: "quero este", why: "Combina com Parasita." }, { title: "Inventado", why: "x" }]);
  const r = await handle(req("/pick", { type: "film", mood: "leve", profile }), env, gem(picks));
  assert.equal(r.status, 200);
  assert.deepEqual((await r.json()).picks, [{ title: "Quero Este", why: "Combina com Parasita." }]);
  assert.match(gem.calls.at(-1).init.body, /leve/);
  const e = await handle(req("/pick", { type: "film", profile: cleanProfile({}) }), env, gem(picks));
  assert.equal(e.status, 400);
  assert.throws(() => parsePicks("[]", profile));
});
test("M6: limites de 100 foram removidos", () => {
  const p = cleanProfile({ nos: Array.from({ length: 300 }, (_, i) => "T" + i), wants: Array.from({ length: 300 }, (_, i) => "W" + i) });
  assert.equal(p.nos.length, 300); assert.equal(p.wants.length, 300);
});
