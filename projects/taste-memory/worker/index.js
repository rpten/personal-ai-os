// Worker taste-memory-recs: a chave do Gemini (env.GEMINI_API_KEY) existe só aqui.
// POST /recs  {type, mood, profile}                      -> {suggestions:[{title,year,author,synopsis,why,refs}]}
// POST /chat  {type, suggestion, messages, profile}      -> {reply}
// profile: {loved:[{title,year,author,rating}], disliked:[...], seen:[títulos], wants:[títulos], nos:[títulos]}
export const ALLOWED_ORIGIN = "https://rpten.github.io";
export const MODEL = "gemini-3.1-flash-lite";
const MAX_BODY = 80_000;

const norm = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const str = (s, n) => String(s ?? "").slice(0, n);
const yr = (y) => { const n = parseInt(y, 10); return n > 0 ? n : null; };
const line = (i) => `- ${i.title}${i.year ? ` (${i.year})` : ""}${i.author ? ` — ${i.author}` : ""}${i.rating ? ` · nota ${i.rating}/5` : ""}`;

export function cleanProfile(p = {}) {
  const items = (a, n) => (Array.isArray(a) ? a : []).slice(0, n).map((i) => ({ title: str(i?.title, 200), year: yr(i?.year), author: str(i?.author, 200), rating: Number(i?.rating) || null })).filter((i) => i.title);
  const names = (a, n) => (Array.isArray(a) ? a : []).slice(0, n).map((t) => str(t, 200)).filter(Boolean);
  return { loved: items(p.loved, 40), disliked: items(p.disliked, 20), seen: names(p.seen, 500), wants: names(p.wants, 100), nos: names(p.nos, 100) };
}

export function buildRecsPrompt(type, mood, profile) {
  const kind = type === "film" ? "filmes" : "livros", verb = type === "film" ? "viu" : "leu";
  return `Você é um curador de ${kind}. Recomende exatamente 5 ${kind} para esta pessoa, com base no gosto dela.
Gostou muito:
${profile.loved.map(line).join("\n") || "(sem dados)"}
Não gostou:
${profile.disliked.map(line).join("\n") || "(sem dados)"}
Já ${verb} (NÃO recomende nenhum destes): ${profile.seen.join("; ") || "(nada)"}
${profile.wants.length ? `Quer ${type === "film" ? "ver" : "ler"} (NÃO repita; use como sinal de gosto): ${profile.wants.join("; ")}\n` : ""}${profile.nos.length ? `Sugestões anteriores que ela NÃO curtiu (evite estilo parecido): ${profile.nos.join("; ")}\n` : ""}${mood ? `Humor/pedido de agora: ${str(mood, 200)}\n` : ""}Use apenas ${kind} que realmente existem; se não tiver certeza do ano ou autor, deixe o campo vazio.
Para cada um: "synopsis" = sinopse de 1-2 frases sem spoilers; "why" = por que ela gostaria, em 1-2 frases, citando itens REAIS da lista "Gostou muito" (e a nota dela); "refs" = títulos exatos dessa lista que você citou no "why". Nunca cite item que não esteja na lista.
Responda SOMENTE com JSON: [{"title":"","year":0,"author":"","synopsis":"","why":"","refs":[""]}] (author só para livros). Português do Brasil.`;
}

export function parseSuggestions(text, profile) {
  const t = String(text || "").trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  const a = t.indexOf("["), b = t.lastIndexOf("]");
  if (a < 0 || b < a) throw new Error("resposta sem lista de sugestões");
  let arr; try { arr = JSON.parse(t.slice(a, b + 1)); } catch { throw new Error("resposta em formato inválido"); }
  const seen = new Set([...profile.seen, ...profile.wants, ...profile.nos, ...profile.loved.map((i) => i.title), ...profile.disliked.map((i) => i.title)].map(norm));
  const known = new Map([...profile.loved, ...profile.disliked].map((i) => [norm(i.title), i]));
  const out = (Array.isArray(arr) ? arr : []).filter((s) => s && typeof s.title === "string" && s.title.trim() && !seen.has(norm(s.title))).map((s) => ({
    title: str(s.title.trim(), 200), year: yr(s.year), author: str(s.author, 200).trim(), synopsis: str(s.synopsis, 600).trim(), why: str(s.why, 800).trim(),
    // só referências que existem de verdade no histórico dele, com a nota real
    refs: (Array.isArray(s.refs) ? s.refs : []).map((r) => known.get(norm(r))).filter(Boolean).slice(0, 4).map((i) => ({ title: i.title, year: i.year, rating: i.rating })),
  }));
  if (!out.length) throw new Error("nenhuma sugestão nova (todas já estavam no seu histórico)");
  return out.slice(0, 5);
}

export function buildChatPrompt(type, s, profile) {
  const kind = type === "film" ? "filmes" : "livros";
  return `Você é um curador de ${kind} conversando com a pessoa sobre UMA indicação que você fez. Responda em português do Brasil, curto (no máximo 4 frases), direto, sem rodeios.
Indicação: ${s.title}${s.year ? ` (${s.year})` : ""}${s.author ? ` — ${s.author}` : ""}
Sinopse: ${s.synopsis || "-"}
Por que indicou: ${s.why || "-"}
Gosto da pessoa — gostou muito:
${profile.loved.slice(0, 25).map(line).join("\n") || "(sem dados)"}
Não gostou:
${profile.disliked.slice(0, 15).map(line).join("\n") || "(sem dados)"}
Já ${type === "film" ? "viu" : "leu"} (não sugira de novo): ${profile.seen.slice(0, 300).join("; ") || "(nada)"}
Se ela discordar, considere o argumento com honestidade (pode admitir que errou). Se pedir alternativas, dê 1-3 ${kind} reais que ela ainda não ${type === "film" ? "viu" : "leu"}, com uma frase de motivo ligada ao gosto dela. Não invente ${kind}; na dúvida, diga que não tem certeza.`;
}

export function cleanMessages(m) {
  const out = (Array.isArray(m) ? m : []).slice(-12).map((x) => ({ role: x?.role === "model" ? "model" : "user", text: str(x?.text, 1000).trim() })).filter((x) => x.text);
  while (out.length && out[0].role !== "user") out.shift();
  if (!out.length || out[out.length - 1].role !== "user") throw new Error("mensagem vazia");
  return out;
}

class HttpError extends Error { constructor(status, msg) { super(msg); this.status = status; } }

export function geminiError(status, body = "") {
  if (status === 429) return [429, "Limite gratuito do Gemini atingido. Tente de novo em alguns minutos."];
  if ((status === 400 && /API key|API_KEY/i.test(body)) || status === 401 || status === 403) return [502, "A chave do Gemini no servidor foi recusada. Avise o Rafael."];
  if (status >= 500) return [502, "O Gemini está fora do ar agora. Tente de novo em instantes."];
  return [502, `Erro do Gemini (HTTP ${status}).`];
}

async function gemini(env, contents, json, fetchFn) {
  if (!env.GEMINI_API_KEY) throw new HttpError(500, "Servidor sem chave do Gemini configurada.");
  let r;
  try {
    r = await fetchFn(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
      method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
      body: JSON.stringify({ contents, generationConfig: json ? { responseMimeType: "application/json", temperature: 0.8 } : { temperature: 0.7 } }),
    });
  } catch { throw new HttpError(502, "Sem conexão com o Gemini."); }
  if (!r.ok) { const [s, m] = geminiError(r.status, await r.text().catch(() => "")); throw new HttpError(s, m); }
  const data = await r.json().catch(() => null);
  const text = data?.candidates?.[0]?.content?.parts?.map((p) => p.text).join("") || "";
  if (!text) throw new HttpError(502, data?.promptFeedback?.blockReason ? "O Gemini bloqueou o pedido. Reformule e tente de novo." : "O Gemini não devolveu resposta.");
  return text;
}

export async function handle(request, env, fetchFn = fetch) {
  const origin = request.headers.get("Origin");
  const cors = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400", Vary: "Origin" };
  const reply = (status, body, headers = cors) => new Response(body === null ? null : JSON.stringify(body), { status, headers: { ...headers, "Content-Type": "application/json" } });
  if (origin !== ALLOWED_ORIGIN) return reply(403, { error: "Origem não permitida." }, { Vary: "Origin" });
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  const path = new URL(request.url).pathname;
  if (request.method !== "POST" || !["/recs", "/chat"].includes(path)) return reply(404, { error: "Rota não encontrada." });
  try {
    const raw = await request.text();
    if (raw.length > MAX_BODY) throw new HttpError(413, "Pedido grande demais.");
    let body; try { body = JSON.parse(raw); } catch { throw new HttpError(400, "JSON inválido."); }
    const type = body?.type === "book" ? "book" : body?.type === "film" ? "film" : null;
    if (!type) throw new HttpError(400, "Tipo inválido (film ou book).");
    const profile = cleanProfile(body.profile);
    if (path === "/recs") {
      const text = await gemini(env, [{ role: "user", parts: [{ text: buildRecsPrompt(type, str(body.mood, 200).trim(), profile) }] }], true, fetchFn);
      let suggestions; try { suggestions = parseSuggestions(text, profile); } catch (e) { throw new HttpError(502, `Resposta do Gemini inutilizável: ${e.message}.`); }
      return reply(200, { suggestions });
    }
    const s = body.suggestion; if (!s?.title) throw new HttpError(400, "Indicação ausente.");
    let msgs; try { msgs = cleanMessages(body.messages); } catch (e) { throw new HttpError(400, e.message); }
    const sug = { title: str(s.title, 200), year: yr(s.year), author: str(s.author, 200), synopsis: str(s.synopsis, 600), why: str(s.why, 800) };
    const contents = msgs.map((m, i) => ({ role: m.role, parts: [{ text: i === 0 ? `${buildChatPrompt(type, sug, profile)}\n\nMensagem da pessoa: ${m.text}` : m.text }] }));
    return reply(200, { reply: (await gemini(env, contents, false, fetchFn)).trim() });
  } catch (e) {
    if (e instanceof HttpError) return reply(e.status, { error: e.message });
    return reply(500, { error: "Erro interno." });
  }
}

export default { fetch: (request, env) => handle(request, env) };
