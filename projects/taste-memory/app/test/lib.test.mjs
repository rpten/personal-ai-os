import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseLetterboxdRss, parseGoodreadsRss, parseCsv, parseCsvHistory, merge, summarize } from "../../public/lib.js";
import worker, { buildTarget } from "../worker/worker.js";

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

test("Worker: valida rotas e parâmetros", async () => {
  assert.equal(buildTarget("https://w.dev/letterboxd?user=rafaeldez"), "https://letterboxd.com/rafaeldez/rss/");
  assert.match(buildTarget("https://w.dev/goodreads?id=196111676"), /list_rss\/196111676\?shelf=read/);
  assert.equal(buildTarget("https://w.dev/letterboxd?user=../etc"), null);
  assert.equal(buildTarget("https://w.dev/goodreads?id=abc"), null);
  assert.equal(buildTarget("https://w.dev/outra"), null);
  const r = await worker.fetch(new Request("https://w.dev/outra", { headers: { Origin: "https://rpten.github.io" } }));
  assert.equal(r.status, 400);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), "https://rpten.github.io");
});
