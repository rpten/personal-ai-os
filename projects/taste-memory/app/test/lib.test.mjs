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


import { buildProfile, recommend, chat } from "../../public/lib.js";
const hist = () => [...parseLetterboxdRss(fx("letterboxd.xml")), ...parseGoodreadsRss(fx("goodreads.xml"))];

test("M4 perfil: só o tipo pedido, com notas reais; nada de chave", () => {
  const p = buildProfile(hist(), "film", {});
  assert.ok(p.loved.some((i) => i.title === "Parasita" && i.rating === 5));
  assert.ok(!JSON.stringify(p).includes("Dom Casmurro"));
});

test("M4 feedback entra no perfil: já vi/não curto excluem, quero vira sinal, outro tipo fica de fora", () => {
  let fb = setFeedback({}, "film", { title: "Vi Esse", year: 1999 }, "seen");
  fb = setFeedback(fb, "film", { title: "Quero Esse", year: 2010 }, "want");
  fb = setFeedback(fb, "film", { title: "Odiei Esse", year: 2005 }, "no");
  fb = setFeedback(fb, "book", { title: "Livro X", author: "A" }, "seen");
  const p = buildProfile(hist(), "film", fb);
  assert.ok(p.seen.includes("Vi Esse") && p.seen.includes("Odiei Esse") && !p.seen.includes("Quero Esse"));
  assert.deepEqual(p.wants, ["Quero Esse"]); assert.deepEqual(p.nos, ["Odiei Esse"]);
  assert.ok(!JSON.stringify(p).includes("Livro X"));
});

const okJson = (body) => async (u, o) => ({ ok: true, status: 200, json: async () => body });
test("M4 recommend/chat: chamam o Worker (sem chave nenhuma) e tratam erros", async () => {
  const calls = [];
  const f = (body, status = 200) => async (u, o) => { calls.push([u, JSON.parse(o.body), o.headers]); return { ok: status === 200, status, json: async () => body }; };
  const s = await recommend({ workerUrl: "https://w.dev/", list: hist(), type: "film", mood: "leve", fetchFn: f({ suggestions: [{ title: "Novo" }] }) });
  assert.equal(s[0].title, "Novo"); assert.equal(calls[0][0], "https://w.dev/recs"); assert.equal(calls[0][1].mood, "leve");
  assert.ok(!JSON.stringify(calls[0]).match(/key|AIza/i));
  const r = await chat({ workerUrl: "https://w.dev", list: hist(), type: "film", suggestion: { title: "Novo" }, messages: [{ role: "user", text: "oi" }], fetchFn: f({ reply: "Olá" }) });
  assert.equal(r, "Olá"); assert.equal(calls[1][0], "https://w.dev/chat");
  await assert.rejects(recommend({ workerUrl: "", list: [], type: "film" }), /ainda não foi publicado/);
  await assert.rejects(recommend({ workerUrl: "https://w.dev", list: [], type: "film", fetchFn: f({ error: "Limite gratuito do Gemini atingido." }, 429) }), /Limite gratuito/);
  await assert.rejects(recommend({ workerUrl: "https://w.dev", list: [], type: "film", fetchFn: async () => { throw new Error("x"); } }), /Sem conexão/);
  await assert.rejects(recommend({ workerUrl: "https://w.dev", list: [], type: "film", fetchFn: f({ suggestions: [] }) }), /não devolveu/);
});

import { setFeedback, sugKey, exportBackup, importBackup } from "../../public/lib.js";

test("M3 feedback: marcar, trocar e desfazer", () => {
  const s = { title: "Novo", year: 2001 };
  let fb = setFeedback({}, "film", s, "want");
  assert.equal(fb[sugKey("film", s)].status, "want");
  fb = setFeedback(fb, "film", s, "no"); assert.equal(fb[sugKey("film", s)].status, "no");
  fb = setFeedback(fb, "film", s, "no"); assert.deepEqual(fb, {});
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

import { backlog, markDone, removeFromBacklog, pickFromBacklog } from "../../public/lib.js";
test("M6 backlog: lista por tipo, guarda sinopse, já vi com nota vira histórico, remover tira", () => {
  let fb = setFeedback({}, "film", { title: "Quero Esse", year: 2010, synopsis: "Sin.", why: "Pq." }, "want");
  fb = setFeedback(fb, "book", { title: "Livro Q", author: "Autor" }, "want");
  assert.equal(backlog(fb, "film").length, 1); assert.equal(backlog(fb, "film")[0].synopsis, "Sin."); assert.equal(backlog(fb, "book").length, 1);
  const key = backlog(fb, "film")[0].key;
  const d = markDone({ items: [], feedback: fb }, key, 4, "2026-11-06");
  assert.equal(backlog(d.feedback, "film").length, 0); assert.equal(d.feedback[key].status, "seen");
  assert.deepEqual([d.items[0].title, d.items[0].rating, d.items[0].source], ["Quero Esse", 4, "manual"]);
  const d2 = markDone({ items: [], feedback: fb }, key, null); assert.equal(d2.items[0].rating, null);
  assert.equal(backlog(removeFromBacklog(fb, key), "film").length, 0);
});
test("M6 pick: chama /pick com o perfil e devolve as escolhas", async () => {
  let sent; const fetchFn = async (u, o) => { sent = { u, b: JSON.parse(o.body) }; return new Response(JSON.stringify({ picks: [{ title: "Quero Esse", why: "x" }] }), { status: 200 }); };
  const fb = setFeedback({}, "film", { title: "Quero Esse" }, "want");
  const r = await pickFromBacklog({ workerUrl: "https://w", list: [], type: "film", mood: "leve", feedback: fb, fetchFn });
  assert.ok(sent.u.endsWith("/pick")); assert.deepEqual(sent.b.profile.wants, ["Quero Esse"]); assert.equal(r[0].title, "Quero Esse");
});
