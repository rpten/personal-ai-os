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

// ---- M2: recomendação com Gemini ----
export const GEMINI_MODEL = "gemini-2.5-flash";
const line = (i) => `- ${i.title}${i.year ? ` (${i.year})` : ""}${i.author ? ` — ${i.author}` : ""}${i.rating ? ` · nota ${i.rating}/5` : ""}`;

export function buildPrompt(list, type, mood = "") {
  const all = list.filter((i) => i.type === type), kind = type === "film" ? "filmes" : "livros";
  const rated = all.filter((i) => i.rating);
  const byRating = (a, b) => b.rating - a.rating;
  const loved = rated.filter((i) => i.rating >= 4).sort(byRating).slice(0, 25);
  const disliked = rated.filter((i) => i.rating <= 2.5).sort((a, b) => a.rating - b.rating).slice(0, 15);
  const seen = all.map((i) => i.title).slice(0, 400).join("; ");
  return `Você é um curador de ${kind}. Recomende exatamente 5 ${kind} para esta pessoa, com base no gosto dela.
Gostou muito:
${loved.map(line).join("\n") || "(sem dados)"}
Não gostou:
${disliked.map(line).join("\n") || "(sem dados)"}
Já ${type === "film" ? "viu" : "leu"} (NÃO recomende nenhum destes): ${seen || "(nada)"}
${mood.trim() ? `Humor/pedido de agora: ${mood.trim().slice(0, 200)}\n` : ""}Use apenas ${kind} que realmente existem; se não tiver certeza do ano ou autor, deixe o campo vazio.
Responda SOMENTE com JSON: [{"title":"","year":0,"author":"","why":"justificativa de 1-2 frases em português do Brasil ligada ao gosto dela"}] (author só para livros).`;
}

export function parseSuggestions(text, list = [], type = "film") {
  let t = String(text || "").trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  const a = t.indexOf("["), b = t.lastIndexOf("]");
  if (a < 0 || b < a) throw new Error("resposta sem lista de sugestões");
  let arr; try { arr = JSON.parse(t.slice(a, b + 1)); } catch { throw new Error("resposta em formato inválido"); }
  const seen = new Set(list.filter((i) => i.type === type).map((i) => norm(i.title)));
  const out = arr.filter((s) => s && typeof s.title === "string" && s.title.trim()).map((s) => ({
    title: s.title.trim(), year: num(String(s.year ?? "")), author: String(s.author || "").trim(), why: String(s.why || "").trim(),
  })).filter((s) => !seen.has(norm(s.title)));
  if (!out.length) throw new Error("nenhuma sugestão nova (todas já estavam no seu histórico)");
  return out.slice(0, 5);
}

export function geminiError(status, body = "") {
  if (status === 400 && /API key|API_KEY/i.test(body)) return "Chave do Gemini inválida. Confira em Configurações.";
  if (status === 401 || status === 403) return "Chave do Gemini recusada. Confira em Configurações.";
  if (status === 429) return "Limite gratuito do Gemini atingido. Tente de novo em alguns minutos.";
  if (status >= 500) return "O Gemini está fora do ar agora. Tente de novo em instantes.";
  return `Erro do Gemini (HTTP ${status}).`;
}

export async function recommend({ key, list, type, mood, fetchFn = fetch }) {
  if (!key) throw new Error("Informe a chave do Gemini em Configurações.");
  let r;
  try {
    r = await fetchFn(`https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`, {
      method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({ contents: [{ parts: [{ text: buildPrompt(list, type, mood) }] }], generationConfig: { responseMimeType: "application/json", temperature: 0.8 } }),
    });
  } catch { throw new Error("Sem conexão com o Gemini."); }
  if (!r.ok) throw new Error(geminiError(r.status, await r.text().catch(() => "")));
  const data = await r.json().catch(() => null);
  const text = data?.candidates?.[0]?.content?.parts?.map((p) => p.text).join("") || "";
  if (!text) throw new Error(data?.promptFeedback?.blockReason ? "O Gemini bloqueou o pedido. Mude o humor e tente de novo." : "O Gemini não devolveu resposta.");
  return parseSuggestions(text, list, type);
}
