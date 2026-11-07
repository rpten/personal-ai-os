import { parseLetterboxdRss, parseGoodreadsRss, parseCsvHistory, merge, summarize, recommend, chat, setFeedback, sugKey, exportBackup, importBackup, backlog, markDone, removeFromBacklog, pickFromBacklog } from "./lib.js";

const KEY = "taste-memory:v1";
const load = () => { let d; try { d = { items: [], feedback: {}, chats: {}, lastSync: null, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch { d = { items: [], feedback: {}, chats: {}, lastSync: null }; }
  delete d.cfg; return d; }; // M4: a chave do Gemini não existe mais no navegador; apaga qualquer resto de versões antigas
let workerUrl = "";
fetch("./config.json?t=" + Date.now()).then((r) => r.json()).then((c) => { workerUrl = c.workerUrl || ""; }).catch(() => {});
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

document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => { tab = b.dataset.t; cur = []; render(); renderSugs(); }));
save(); // grava já sem a chave antiga
let openChat = null, busy = false, blTab = "film", rating = null, picks = [];
function renderBacklog() {
  const list = backlog(db.feedback, blTab), v = blTab === "film" ? "Já vi" : "Já li";
  document.querySelectorAll("#bltabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === blTab));
  $("blpicks").innerHTML = picks.length ? `<h2>Combina com você agora</h2>${picks.map((p) => `<p class="pick"><b>${esc(p.title)}</b> — ${esc(p.why)}</p>`).join("")}` : "";
  $("bllist").innerHTML = list.length ? list.map((w) => `<div class="sug"><b>${esc(w.title)}</b>${w.year ? ` (${w.year})` : ""}${w.author ? ` — ${esc(w.author)}` : ""}
${w.synopsis ? `<p class="syn">${esc(w.synopsis)}</p>` : ""}${w.why ? `<p><span class="tag">Por que você gostaria</span> ${esc(w.why)}</p>` : ""}
${rating === w.key ? `<p class="muted">Que nota? <span class="stars">${[1, 2, 3, 4, 5].map((n) => `<button data-bk="${esc(w.key)}" data-act="rate" data-n="${n}">${n}★</button>`).join("")}<button data-bk="${esc(w.key)}" data-act="rate" data-n="0">Sem nota</button></span></p>`
  : `<div class="fb"><button data-bk="${esc(w.key)}" data-act="done">${v}</button><button data-bk="${esc(w.key)}" data-act="rm">Remover</button></div>`}</div>`).join("")
    : `<p class="muted">Nada no backlog de ${blTab === "film" ? "filmes" : "livros"}. Toque em “Quero” nas indicações para guardar aqui.</p>`;
}
document.querySelectorAll("#bltabs button").forEach((b) => b.addEventListener("click", () => { blTab = b.dataset.t; rating = null; picks = []; $("blmsg").textContent = ""; renderBacklog(); }));
$("bllist").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-act]"); if (!b) return; const k = b.dataset.bk;
  if (b.dataset.act === "done") rating = k;
  else if (b.dataset.act === "rate") { Object.assign(db, markDone(db, k, +b.dataset.n || null)); rating = null; picks = picks.filter((p) => p.title !== db.feedback[k]?.title); render(); }
  else if (b.dataset.act === "rm") { db.feedback = removeFromBacklog(db.feedback, k); }
  save(); renderBacklog(); renderSugs();
});
$("blbtn").addEventListener("click", async () => {
  const m = $("blmsg"), btn = $("blbtn");
  if (!backlog(db.feedback, blTab).length) { m.className = "err"; m.textContent = "Seu backlog está vazio: marque “Quero” em alguma indicação primeiro."; return; }
  btn.disabled = true; m.className = "muted"; m.textContent = "Escolhendo do seu backlog…";
  try { picks = await pickFromBacklog({ workerUrl, list: db.items, type: blTab, mood: $("blmood").value, feedback: db.feedback }); m.className = "ok"; m.textContent = `${picks.length} do seu backlog:`; }
  catch (err) { picks = []; m.className = "err"; m.textContent = err.message; }
  btn.disabled = false; renderBacklog();
});
let cur = [];
const chatBox = (k) => { const msgs = db.chats[k] || [];
  return `<div class="chat">${msgs.map((m) => `<div class="msg ${m.role}">${esc(m.text)}</div>`).join("")}${busy ? '<div class="msg model muted">Pensando…</div>' : ""}
<form class="cf" data-k="${esc(k)}"><input maxlength="500" placeholder="Pergunte, discorde ou peça outra opção" autocomplete="off"><button class="primary" ${busy ? "disabled" : ""}>Enviar</button></form></div>`; };
function renderSugs() {
  $("recs").innerHTML = cur.map((s, n) => { const k = sugKey(tab, s), st = db.feedback[k]?.status;
    return `<div class="sug"><b>${esc(s.title)}</b>${s.year ? ` (${s.year})` : ""}${s.author ? ` — ${esc(s.author)}` : ""}
${s.synopsis ? `<p class="syn">${esc(s.synopsis)}</p>` : ""}<p><span class="tag">Por que você gostaria</span> ${esc(s.why)}</p>
${(s.refs || []).length ? `<p class="refs">${s.refs.map((r) => `<span class="chip">${esc(r.title)}${r.rating ? ` · ${r.rating}★` : ""}</span>`).join("")}</p>` : ""}
<div class="fb">${[["seen", tab === "film" ? "Já vi" : "Já li"], ["want", "Quero"], ["no", "Não curto"]].map(([kk, t]) => `<button data-n="${n}" data-k="${kk}" class="${st === kk ? "on " + kk : ""}">${t}</button>`).join("")}<button data-n="${n}" data-chat="1" class="${openChat === k ? "on chatb" : ""}">💬 Conversar</button></div>
${openChat === k ? chatBox(k) : ""}</div>`; }).join("");
  renderBacklog();
}
$("recs").addEventListener("click", (e) => {
  const c = e.target.closest("button[data-chat]");
  if (c) { const k = sugKey(tab, cur[+c.dataset.n]); openChat = openChat === k ? null : k; renderSugs(); $("recs").querySelector(".cf input")?.focus(); return; }
  const b = e.target.closest("button[data-k]"); if (!b) return;
  db.feedback = setFeedback(db.feedback, tab, cur[+b.dataset.n], b.dataset.k); save(); renderSugs();
});
$("recs").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target.closest(".cf"); if (!f || busy) return;
  const input = f.querySelector("input"), text = input.value.trim(), k = f.dataset.k; if (!text) return;
  const sug = cur.find((s) => sugKey(tab, s) === k), msgs = (db.chats[k] ||= []);
  msgs.push({ role: "user", text }); busy = true; save(); renderSugs();
  try {
    const r = await chat({ workerUrl, list: db.items, type: tab, feedback: db.feedback, suggestion: sug, messages: msgs.filter((m) => !m.error) });
    msgs.push({ role: "model", text: r });
  } catch (err) { msgs.push({ role: "model", text: "⚠️ " + err.message, error: true }); }
  busy = false; save(); renderSugs(); $("recs").querySelector(".cf input")?.focus();
});
$("export").addEventListener("click", () => {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([exportBackup(db)], { type: "application/json" }));
  a.download = `memoria-de-gosto-${new Date().toISOString().slice(0, 10)}.json`; a.click(); URL.revokeObjectURL(a.href);
  $("bkmsg").className = "ok"; $("bkmsg").textContent = "Backup baixado.";
});
$("import").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return; const m = $("bkmsg");
  try { const r = importBackup(await f.text(), db); db.items = r.items; db.feedback = r.feedback; db.lastSync = r.lastSync; save(); render(); renderSugs(); m.className = "ok"; m.textContent = `Backup restaurado (${r.items.length} itens, ${Object.keys(r.feedback).length} marcações).`; }
  catch (err) { m.className = "err"; m.textContent = err.message; }
  e.target.value = "";
});
async function rec() {
  const m = $("recmsg"), box = $("recs"), btn = $("rec"), kind = tab === "film" ? "filmes" : "livros";
  if (!db.items.some((i) => i.type === tab)) { m.className = "err"; m.textContent = `Ainda não tenho nenhum dos seus ${kind}. ${tab === "book" ? "Importe o CSV do Goodreads (seção abaixo)" : "Toque em “Atualizar agora” ou importe o CSV"} e tente de novo.`; return; }
  const t0 = Date.now(), label = btn.textContent;
  btn.disabled = true; box.innerHTML = ""; m.className = "muted";
  const tick = () => { const s = Math.round((Date.now() - t0) / 1000); btn.textContent = `⏳ Buscando… ${s}s`; m.textContent = `Analisando seus ${kind} e escolhendo 5 indicações (costuma levar de 5 a 20 segundos)…`; };
  tick(); const timer = setInterval(tick, 1000);
  try {
    const list = await recommend({ workerUrl, list: db.items, type: tab, mood: $("mood").value, feedback: db.feedback });
    cur = list; openChat = null; renderSugs();
    m.className = "ok"; m.textContent = `Pronto: ${list.length} indicações de ${kind} em ${Math.round((Date.now() - t0) / 1000)}s.`;
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) { m.className = "err"; m.textContent = e.message; }
  clearInterval(timer); btn.textContent = label; btn.disabled = false;
}
$("rec").addEventListener("click", rec);
$("sync").addEventListener("click", sync);
$("csv").addEventListener("change", (e) => e.target.files[0] && importCsv(e.target.files[0]));
render(); renderSugs();
