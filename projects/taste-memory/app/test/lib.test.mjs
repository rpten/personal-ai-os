import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseLetterboxdRss, parseGoodreadsRss, parseCsv, parseCsvHistory, merge, summarize } from "../../public/lib.js";

const fx = (n) => readFileSync(new URL(`../fixtures/${n}`, import.meta.url), "utf8");

test("RSS Letterboxd: ignora itens que não são filme e decodifica entidades", () => {
  const r = parseLetterboxdRss(fx("letterboxd.xml"));
  assert.equal(r.length, 3);
  assert.deepEqual([r[0].title, r[0].year, r[0].rating, r[0].date], ["Parasita", 2019, 5, "2026-11-02"]);
  assert.equal(r[2].title, "Filme Ruim & Cia");
});

test("RSS Goodreads: CDATA, nota 0 vira sem nota, data cai para date_added", () => {
  const r = parseGoodreadsRss(fx("goodreads.xml"));
  assert.equal(r.length, 3);
  assert.equal(r[0].author, "Machado de Assis");
  assert.equal(r[0].date, "2026-10-10");
  assert.equal(r[1].date, "2026-01-05");
  assert.equal(r[2].rating, null);
});

test("CSV: aspas, vírgulas e linhas vazias", () => {
  const rows = parseCsv(fx("ratings.csv"));
  assert.equal(rows.length, 3);
  assert.equal(rows[1].Name, "Amélie, a Fabulosa");
});

test("CSV Letterboxd e Goodreads detectados pelo cabeçalho; to-read é ignorado", () => {
  const f = parseCsvHistory(fx("ratings.csv"));
  assert.equal(f.type, "film"); assert.equal(f.items.length, 3);
  const b = parseCsvHistory(fx("goodreads.csv"));
  assert.equal(b.type, "book"); assert.equal(b.items.length, 2);
  assert.equal(parseCsvHistory("a,b\n1,2").type, null);
});

test("merge: CSV + RSS não duplica; RSS prevalece; sync repetido não muda nada", () => {
  const csv = parseCsvHistory(fx("ratings.csv")).items;
  const rss = parseLetterboxdRss(fx("letterboxd.xml"));
  const m1 = merge(csv, rss);
  assert.equal(m1.items.filter((i) => i.title === "Parasita").length, 1);
  assert.equal(m1.items.find((i) => i.title === "Parasita").rating, 5);
  assert.equal(m1.items.length, 5);
  const m2 = merge(m1.items, rss);
  assert.equal(m2.added, 0); assert.equal(m2.updated, 0); assert.equal(m2.items.length, 5);
});

test("merge de livros: mesmo Book Id do CSV e do RSS é o mesmo livro", () => {
  const m = merge(parseCsvHistory(fx("goodreads.csv")).items, parseGoodreadsRss(fx("goodreads.xml")));
  assert.equal(m.items.filter((i) => i.title === "Dom Casmurro").length, 1);
  assert.equal(m.items.find((i) => i.title === "Dom Casmurro").rating, 5);
});

test("resumo: média, histograma, favoritos e década", () => {
  const items = merge(parseCsvHistory(fx("ratings.csv")).items, parseLetterboxdRss(fx("letterboxd.xml"))).items;
  const s = summarize(items, "film");
  assert.equal(s.total, 5); assert.equal(s.rated, 4);
  assert.equal(s.average, 3.75);
  assert.equal(s.favorites[0].title, "Parasita");
  assert.equal(s.disliked[0].title, "Filme Ruim & Cia");
  assert.equal(s.top[0][0], "2000s");
  assert.equal(summarize([], "book").average, null);
});


import { buildPrompt, parseSuggestions, recommend, geminiError } from "../../public/lib.js";
const hist = () => [...parseLetterboxdRss(fx("letterboxd.xml")), ...parseGoodreadsRss(fx("goodreads.xml"))];

test("M2 prompt: inclui gostos, humor e lista de já vistos; só o tipo pedido", () => {
  const p = buildPrompt(hist(), "film", "algo leve");
  assert.match(p, /Parasita/); assert.match(p, /algo leve/); assert.match(p, /NÃO recomende/); assert.doesNotMatch(p, /Dom Casmurro/);
});

test("M2 parse: aceita cercas ```json, descarta já vistos e limita a 5", () => {
  const raw = "```json\n" + JSON.stringify([{ title: "Parasita", year: 2019, why: "x" }, ...[1, 2, 3, 4, 5, 6].map((n) => ({ title: `Novo ${n}`, year: 2000 + n, why: "porque sim" }))]) + "\n```";
  const r = parseSuggestions(raw, hist(), "film");
  assert.equal(r.length, 5); assert.ok(!r.some((s) => s.title === "Parasita"));
});

test("M2 parse: erros claros", () => {
  assert.throws(() => parseSuggestions("oi", [], "film"), /sem lista/);
  assert.throws(() => parseSuggestions("[{oops]", [], "film"), /inválido/);
  assert.throws(() => parseSuggestions('[{"title":"Parasita"}]', hist(), "film"), /nenhuma sugestão nova/);
});

test("M2 recommend: API simulada ok, chave inválida, cota, rede e bloqueio", async () => {
  const ok = async (u, o) => { assert.match(o.headers["x-goog-api-key"], /K/); return { ok: true, json: async () => ({ candidates: [{ content: { parts: [{ text: '[{"title":"Novo","year":2001,"why":"a"}]' }] } }] }) }; };
  assert.equal((await recommend({ key: "K", list: hist(), type: "film", fetchFn: ok }))[0].title, "Novo");
  const st = (s, b = "") => async () => ({ ok: false, status: s, text: async () => b });
  await assert.rejects(recommend({ key: "K", list: [], type: "film", fetchFn: st(400, "API key not valid") }), /inválida/);
  await assert.rejects(recommend({ key: "K", list: [], type: "film", fetchFn: st(429) }), /Limite gratuito/);
  await assert.rejects(recommend({ key: "K", list: [], type: "film", fetchFn: async () => { throw new Error("x"); } }), /Sem conexão/);
  await assert.rejects(recommend({ key: "K", list: [], type: "film", fetchFn: async () => ({ ok: true, json: async () => ({ promptFeedback: { blockReason: "SAFETY" } }) }) }), /bloqueou/);
  await assert.rejects(recommend({ key: "", list: [], type: "film" }), /chave/);
  assert.match(geminiError(503), /fora do ar/);
});

import { setFeedback, sugKey, exportBackup, importBackup } from "../../public/lib.js";

test("M3 feedback: marcar, trocar e desfazer", () => {
  const s = { title: "Novo", year: 2001 };
  let fb = setFeedback({}, "film", s, "want");
  assert.equal(fb[sugKey("film", s)].status, "want");
  fb = setFeedback(fb, "film", s, "no"); assert.equal(fb[sugKey("film", s)].status, "no");
  fb = setFeedback(fb, "film", s, "no"); assert.deepEqual(fb, {});
});

test("M3 feedback muda o próximo pedido: já vi/não curto entram na exclusão, quero vira sinal, e sugestões marcadas não voltam", () => {
  let fb = setFeedback({}, "film", { title: "Vi Esse", year: 1999 }, "seen");
  fb = setFeedback(fb, "film", { title: "Quero Esse", year: 2010 }, "want");
  fb = setFeedback(fb, "film", { title: "Odiei Esse", year: 2005 }, "no");
  fb = setFeedback(fb, "book", { title: "Livro X", author: "A" }, "seen");
  const p = buildPrompt(hist(), "film", "", fb);
  assert.match(p, /NÃO recomende[^\n]*Vi Esse/); assert.match(p, /NÃO recomende[^\n]*Odiei Esse/);
  assert.match(p, /Quer ver[^\n]*Quero Esse/); assert.match(p, /NÃO curtiu[^\n]*Odiei Esse/);
  assert.doesNotMatch(p, /Livro X/);
  const raw = JSON.stringify(["Vi Esse", "Quero Esse", "Odiei Esse", "Outro"].map((t) => ({ title: t, why: "x" })));
  assert.deepEqual(parseSuggestions(raw, [], "film", fb).map((s) => s.title), ["Outro"]);
});

test("M3 backup: exporta, restaura em banco vazio, sem a chave do Gemini; rejeita arquivo errado", () => {
  const db = { items: hist(), feedback: setFeedback({}, "film", { title: "Q", year: 2000 }, "want"), cfg: { gkey: "SEGREDO" }, lastSync: "x" };
  const txt = exportBackup(db);
  assert.ok(!txt.includes("SEGREDO"));
  const r = importBackup(txt, { items: [], feedback: {} });
  assert.equal(r.items.length, db.items.length); assert.deepEqual(r.feedback, db.feedback);
  assert.equal(importBackup(txt, { items: r.items, feedback: r.feedback }).added, 0);
  assert.throws(() => importBackup("nao json", {}), /inválido/);
  assert.throws(() => importBackup('{"a":1}', {}), /não é um backup/);
});
