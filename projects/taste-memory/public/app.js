import { parseLetterboxdRss, parseGoodreadsRss, parseCsvHistory, merge, summarize, recommend } from "./lib.js";

const KEY = "taste-memory:v1";
const load = () => { try { return { items: [], cfg: {}, lastSync: null, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch { return { items: [], cfg: {}, lastSync: null }; } };
const save = () => localStorage.setItem(KEY, JSON.stringify(db));
const db = load();
let tab = "film";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const label = (i) => `${esc(i.title)}${i.year && i.type === "film" ? ` (${i.year})` : ""}${i.author ? ` — ${esc(i.author)}` : ""}${i.rating ? ` · ${i.rating}★` : ""}`;

function render() {
  const s = summarize(db.items, tab), kind = tab === "film" ? "filmes" : "livros";
  $("summary").innerHTML = s.total === 0
    ? `<div class="card"><p>Nenhum dos seus ${kind} ainda. Atualize ou importe o CSV abaixo.</p></div>`
    : `<div class="card"><div class="stats"><div class="stat"><b>${s.total}</b>${kind}</div><div class="stat"><b>${s.rated}</b>com nota</div><div class="stat"><b>${s.average ?? "—"}</b>média</div></div>
<div class="bars">${[5, 4, 3, 2, 1].map((n) => `<div class="bar"><span>${n}★</span><i style="width:${s.rated ? (s.histogram[n] / s.rated) * 70 : 0}%"></i><span>${s.histogram[n]}</span></div>`).join("")}</div>
${s.top.length ? `<h2>Mais gosta (nota ≥ 4): ${tab === "film" ? "décadas" : "autores"}</h2><ul>${s.top.map(([k, n]) => `<li>${esc(k)} · ${n}</li>`).join("")}</ul>` : ""}
${s.favorites.length ? `<h2>Favoritos</h2><ul>${s.favorites.map((i) => `<li>${label(i)}</li>`).join("")}</ul>` : ""}
${s.disliked.length ? `<h2>Não curtiu</h2><ul>${s.disliked.map((i) => `<li>${label(i)}</li>`).join("")}</ul>` : ""}
<h2>Recentes</h2><ul>${s.recent.map((i) => `<li>${label(i)}${i.date ? ` · ${i.date}` : ""}</li>`).join("")}</ul></div>`;
  $("status").textContent = db.lastSync ? `Última sincronização: ${db.lastSync}` : "Ainda não sincronizado.";
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === tab));
}

function readCfg() {
  db.cfg = { gkey: $("gkey").value.trim() };
  save();
}

async function fetchXml(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.text();
}

async function sync() {
  const st = $("status");
  st.className = "muted"; st.textContent = "Atualizando…";
  const jobs = [["Letterboxd", "./data/letterboxd.xml", parseLetterboxdRss], ["Goodreads", "./data/goodreads.xml", parseGoodreadsRss]];
  const msgs = []; let ok = 0;
  for (const [name, url, parse] of jobs) {
    try {
      const r = merge(db.items, parse(await fetchXml(url + "?t=" + Date.now())));
      db.items = r.items; ok++; msgs.push(`${name}: +${r.added} novos, ${r.updated} atualizados`);
    } catch (e) { msgs.push(`${name}: sem dados coletados ainda (${e.message}); use o CSV como alternativa`); }
  }
  if (ok) db.lastSync = new Date().toLocaleString("pt-BR");
  save(); render();
  st.className = ok === jobs.length ? "ok" : "err"; st.textContent = msgs.join(" · ");
}

async function importCsv(file) {
  const msg = $("csvmsg");
  const { type, items } = parseCsvHistory(await file.text());
  if (!type) { msg.className = "err"; msg.textContent = "Não reconheci o arquivo (esperado: ratings.csv do Letterboxd ou export do Goodreads)."; return; }
  const r = merge(db.items, items); db.items = r.items; save();
  tab = type; render();
  msg.className = "ok"; msg.textContent = `${type === "film" ? "Filmes" : "Livros"}: +${r.added} novos, ${r.updated} atualizados.`;
}

document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => { tab = b.dataset.t; render(); }));
if (db.cfg.gkey) $("gkey").value = db.cfg.gkey;
async function rec() {
  readCfg(); const m = $("recmsg"), box = $("recs"), btn = $("rec");
  if (!db.cfg.gkey) { m.className = "err"; m.textContent = "Informe a chave do Gemini em Configurações."; $("settings").open = true; return; }
  if (!db.items.some((i) => i.type === tab)) { m.className = "err"; m.textContent = "Sincronize ou importe seu histórico antes."; return; }
  btn.disabled = true; box.innerHTML = ""; m.className = "muted"; m.textContent = "Pensando…";
  try {
    const list = await recommend({ key: db.cfg.gkey, list: db.items, type: tab, mood: $("mood").value });
    box.innerHTML = list.map((s) => `<div class="sug"><b>${esc(s.title)}</b>${s.year ? ` (${s.year})` : ""}${s.author ? ` — ${esc(s.author)}` : ""}<p>${esc(s.why)}</p></div>`).join("");
    m.className = "ok"; m.textContent = `${list.length} sugestões para ${tab === "film" ? "filmes" : "livros"}.`;
  } catch (e) { m.className = "err"; m.textContent = e.message; }
  btn.disabled = false;
}
$("rec").addEventListener("click", rec);
$("sync").addEventListener("click", sync);
$("csv").addEventListener("change", (e) => e.target.files[0] && importCsv(e.target.files[0]));
render();
