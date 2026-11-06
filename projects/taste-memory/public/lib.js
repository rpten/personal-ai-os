// Parsers, mescla e resumo. Sem dependência de DOM (roda no navegador e no Node).
const decode = (s) => s
  .replace(/^<!\[CDATA\[([\s\S]*?)\]\]>$/, "$1")
  .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&amp;/g, "&")
  .trim();

const tag = (xml, name) => {
  const m = xml.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)</${name}>`));
  return m ? decode(m[1].trim()) : "";
};
const items = (xml) => [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((m) => m[1]);
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const num = (s) => { const n = parseFloat(s); return Number.isFinite(n) && n > 0 ? n : null; };
const isoDate = (s) => { const d = s && new Date(s.replace(/\//g, "-")); return d && !isNaN(d) ? d.toISOString().slice(0, 10) : ""; };

export const filmKey = (title, year) => `f:${norm(title)}:${year || ""}`;
export const bookKey = (title, author, id) => (id ? `b:gr${id}` : `b:${norm(title)}:${norm(author || "")}`);

export function parseLetterboxdRss(xml) {
  const out = [];
  for (const it of items(xml)) {
    const title = tag(it, "letterboxd:filmTitle");
    if (!title) continue; // listas e posts não têm filme
    const year = num(tag(it, "letterboxd:filmYear"));
    out.push({
      key: filmKey(title, year), type: "film", title, year, author: "",
      rating: num(tag(it, "letterboxd:memberRating")),
      date: tag(it, "letterboxd:watchedDate") || isoDate(tag(it, "pubDate")), source: "rss",
    });
  }
  return out;
}

export function parseGoodreadsRss(xml) {
  const out = [];
  for (const it of items(xml)) {
    const title = tag(it, "title");
    if (!title) continue;
    const author = tag(it, "author_name"), id = tag(it, "book_id");
    out.push({
      key: bookKey(title, author, id), type: "book", title, year: num(tag(it, "book_published")), author,
      rating: num(tag(it, "user_rating")), date: isoDate(tag(it, "user_read_at")) || isoDate(tag(it, "user_date_added")), source: "rss",
    });
  }
  return out;
}

export function parseCsv(text) {
  const rows = []; let row = [], cell = "", q = false;
  text = text.replace(/^﻿/, "");
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const [head, ...body] = rows.filter((r) => r.some((x) => x.trim()));
  if (!head) return [];
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h.trim(), (r[i] ?? "").trim()])));
}

// Detecta o tipo pelo cabeçalho: Letterboxd (ratings/diary/watched) ou Goodreads (export da biblioteca).
export function parseCsvHistory(text) {
  const rows = parseCsv(text);
  if (!rows.length) return { type: null, items: [] };
  const cols = Object.keys(rows[0]);
  if (cols.includes("Letterboxd URI")) {
    return { type: "film", items: rows.filter((r) => r.Name).map((r) => ({
      key: filmKey(r.Name, num(r.Year)), type: "film", title: r.Name, year: num(r.Year), author: "",
      rating: num(r.Rating), date: isoDate(r["Watched Date"] || r.Date), source: "csv",
    })) };
  }
  if (cols.includes("Exclusive Shelf") && cols.includes("Author")) {
    return { type: "book", items: rows.filter((r) => r.Title && r["Exclusive Shelf"] === "read").map((r) => ({
      key: bookKey(r.Title, r.Author, r["Book Id"]), type: "book", title: r.Title, year: num(r["Original Publication Year"] || r["Year Published"]),
      author: r.Author, rating: num(r["My Rating"]), date: isoDate(r["Date Read"] || r["Date Added"]), source: "csv",
    })) };
  }
  return { type: null, items: [] };
}

// Mescla por chave sem duplicar. O RSS (mais recente) prevalece, mas não apaga dados que só o CSV tem.
export function merge(existing, incoming) {
  const map = new Map(existing.map((i) => [i.key, i]));
  let added = 0, updated = 0;
  for (const n of incoming) {
    const o = map.get(n.key);
    if (!o) { map.set(n.key, n); added++; continue; }
    const next = n.source === "rss" || o.source !== "rss" ? { ...o, ...Object.fromEntries(Object.entries(n).filter(([, v]) => v !== null && v !== "")) } : o;
    if (JSON.stringify(next) !== JSON.stringify(o)) updated++;
    map.set(n.key, next);
  }
  return { items: [...map.values()], added, updated };
}

export function summarize(list, type) {
  const all = list.filter((i) => i.type === type);
  const rated = all.filter((i) => i.rating);
  const byDate = (a, b) => (b.date || "").localeCompare(a.date || "");
  const hist = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  rated.forEach((i) => { hist[Math.min(5, Math.max(1, Math.ceil(i.rating)))]++; });
  const sum = rated.reduce((s, i) => s + i.rating, 0);
  const count = (fn) => { const m = {}; rated.filter((i) => i.rating >= 4).forEach((i) => { const k = fn(i); if (k) m[k] = (m[k] || 0) + 1; }); return Object.entries(m).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5); };
  return {
    total: all.length, rated: rated.length, average: rated.length ? Math.round((sum / rated.length) * 100) / 100 : null, histogram: hist,
    favorites: rated.filter((i) => i.rating >= 4.5).sort((a, b) => b.rating - a.rating || byDate(a, b)).slice(0, 10),
    disliked: rated.filter((i) => i.rating <= 2).sort(byDate).slice(0, 5),
    recent: [...all].sort(byDate).slice(0, 5),
    top: type === "book" ? count((i) => i.author) : count((i) => (i.year ? `${Math.floor(i.year / 10) * 10}s` : "")),
  };
}

// ---- M3: feedback e backup ----
// feedback: { [chave]: { status: "seen"|"want"|"no", type, title, year, author } }
export const sugKey = (type, s) => (type === "film" ? filmKey(s.title, s.year) : bookKey(s.title, s.author));
export function setFeedback(fb, type, s, status) {
  const key = sugKey(type, s), next = { ...fb };
  if (!status || next[key]?.status === status) delete next[key]; // clicar de novo desfaz
  else next[key] = { status, type, title: s.title, year: s.year || null, author: s.author || "", synopsis: s.synopsis || next[key]?.synopsis || "", why: s.why || next[key]?.why || "" };
  return next;
}
// ---- M6: backlog (lista "Quero") ----
export const backlog = (fb, type) => Object.entries(fb).filter(([, f]) => f.status === "want" && f.type === type).map(([key, f]) => ({ key, ...f }));
export function removeFromBacklog(fb, key) { const n = { ...fb }; delete n[key]; return n; }
// "Já vi/li": sai do backlog, vira "visto" e (se tiver nota) entra no histórico como item manual
export function markDone(db, key, rating, today = new Date().toISOString().slice(0, 10)) {
  const f = db.feedback[key]; if (!f) return db;
  const feedback = { ...db.feedback, [key]: { ...f, status: "seen" } };
  const r = num(rating);
  const items = db.items.some((i) => i.key === key) ? db.items.map((i) => (i.key === key && r ? { ...i, rating: r } : i))
    : [...db.items, { key, type: f.type, title: f.title, year: f.year, author: f.author || "", rating: r, date: today, source: "manual" }];
  return { ...db, feedback, items };
}
export async function pickFromBacklog({ workerUrl, list, type, mood, feedback = {}, fetchFn }) {
  const d = await callWorker(workerUrl, "/pick", { type, mood: (mood || "").slice(0, 200), profile: buildProfile(list, type, feedback) }, fetchFn);
  if (!Array.isArray(d?.picks) || !d.picks.length) throw new Error("O servidor não escolheu nada do seu backlog.");
  return d.picks;
}
export function exportBackup(db) {
  return JSON.stringify({ app: "taste-memory", version: 1, exportedAt: new Date().toISOString(), items: db.items || [], feedback: db.feedback || {}, lastSync: db.lastSync || null }, null, 1);
}
export function importBackup(text, db) {
  let d; try { d = JSON.parse(text); } catch { throw new Error("Arquivo de backup inválido."); }
  if (d?.app !== "taste-memory" || !Array.isArray(d.items) || typeof d.feedback !== "object" || !d.feedback) throw new Error("Este arquivo não é um backup da Memória de gosto.");
  const r = merge(db.items || [], d.items);
  return { items: r.items, feedback: { ...(db.feedback || {}), ...d.feedback }, lastSync: db.lastSync || d.lastSync || null, added: r.added };
}

// ---- M4: Worker (a chave do Gemini fica só no servidor) ----
// Resumo do gosto enviado ao Worker: o que ele precisa para argumentar com itens e notas reais.
export function buildProfile(list, type, feedback = {}) {
  const all = list.filter((i) => i.type === type), rated = all.filter((i) => i.rating);
  const slim = (i) => ({ title: i.title, year: i.year, author: i.author, rating: i.rating });
  const fb = Object.values(feedback).filter((f) => f.type === type);
  return {
    loved: rated.filter((i) => i.rating >= 4).sort((a, b) => b.rating - a.rating).slice(0, 25).map(slim),
    disliked: rated.filter((i) => i.rating <= 2.5).sort((a, b) => a.rating - b.rating).slice(0, 15).map(slim),
    seen: [...all.map((i) => i.title), ...fb.filter((f) => f.status !== "want").map((f) => f.title)].slice(0, 400),
    wants: fb.filter((f) => f.status === "want").map((f) => f.title),
    nos: fb.filter((f) => f.status === "no").map((f) => f.title),
  };
}

export async function callWorker(workerUrl, path, payload, fetchFn = fetch) {
  if (!workerUrl) throw new Error("O servidor de recomendações ainda não foi publicado (falta o deploy do Worker).");
  let r;
  try { r = await fetchFn(workerUrl.replace(/\/$/, "") + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
  catch { throw new Error("Sem conexão com o servidor de recomendações."); }
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new Error(data?.error || `Erro do servidor (HTTP ${r.status}).`);
  return data;
}

export async function recommend({ workerUrl, list, type, mood, feedback = {}, fetchFn }) {
  const d = await callWorker(workerUrl, "/recs", { type, mood: (mood || "").slice(0, 200), profile: buildProfile(list, type, feedback) }, fetchFn);
  if (!Array.isArray(d?.suggestions) || !d.suggestions.length) throw new Error("O servidor não devolveu sugestões.");
  return d.suggestions;
}

export async function chat({ workerUrl, list, type, feedback = {}, suggestion, messages, fetchFn }) {
  const d = await callWorker(workerUrl, "/chat", { type, suggestion, messages: messages.slice(-12), profile: buildProfile(list, type, feedback) }, fetchFn);
  if (!d?.reply) throw new Error("O servidor não devolveu resposta.");
  return d.reply;
}
