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


const ICO = {
  want: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg>',
  seen: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7"/></svg>',
  no: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/></svg>',
  spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/></svg>',
  mark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 20V10M12 20V4M19 20v-7"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>',
};
const VIEWS = [["indicar", "Indicar", "spark"], ["backlog", "Backlog", "mark"], ["gosto", "Gosto", "chart"], ["dados", "Dados", "gear"]];
let view = "indicar";
const MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const fmtDate = (d) => { const m = /(\d{4})[-/](\d{2})[-/](\d{2})/.exec(d || ""); return m ? `${+m[3]} ${MES[+m[2] - 1]} ${m[1]}` : d || ""; };
const num = (n) => String(n).replace(".", ",");
const stars = (r) => (r ? `${num(r)}★` : "");
const kindWord = () => (tab === "film" ? "filmes" : "livros");
function cover(title, year, type, sm) {
  let h = 0; for (const c of String(title)) h = (h * 31 + c.charCodeAt(0)) % 360;
  const ini = (String(title).match(/[A-Za-zÀ-ÿ0-9]/) || ["?"])[0].toUpperCase();
  return `<div class="cover ${type === "book" ? "book" : ""} ${sm ? "sm" : ""}" style="--h:${h}" aria-hidden="true"><b>${esc(ini)}</b><small>${year || (type === "book" ? "LIVRO" : "FILME")}</small></div>`;
}
const meta = (o) => [o.year, o.author].filter(Boolean).map(esc).join(" · ");
let toastT;
function toast(t) { const e = $("toast"); e.textContent = t; e.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => e.classList.remove("on"), 2500); }

function renderNav() {
  $("nav").innerHTML = VIEWS.map(([v, t, i]) => `<button type="button" data-v="${v}" ${v === view ? 'aria-current="page"' : ""}>${ICO[i]}<span>${t}</span></button>`).join("");
  document.querySelectorAll("[data-view]").forEach((s) => (s.hidden = s.dataset.view !== view));
  document.body.dataset.kind = tab;
  document.querySelectorAll("#kind button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.t === tab)));
  $("kindword").textContent = tab === "film" ? "assistir" : "ler";
}
function go(v, push = true) { view = VIEWS.some((x) => x[0] === v) ? v : "indicar"; if (push && location.hash !== "#" + view) history.replaceState(null, "", "#" + view); renderNav(); window.scrollTo(0, 0); }
$("nav").addEventListener("click", (e) => { const b = e.target.closest("button[data-v]"); if (b) go(b.dataset.v); });
document.addEventListener("click", (e) => { const b = e.target.closest("[data-go]"); if (b) go(b.dataset.go); });
window.addEventListener("hashchange", () => go(location.hash.slice(1), false));

function render() {
  const s = summarize(db.items, tab), kind = kindWord();
  $("summary").innerHTML = s.total === 0
    ? `<div class="empty"><h2>Nenhum dos seus ${kind} ainda</h2><p class="lead">Atualize ou importe o CSV na seção Dados.</p><button type="button" class="btn primary" data-go="dados">Ir para Dados</button></div>`
    : `<div class="stats"><div class="stat"><b>${s.total}</b><span>${kind}</span></div><div class="stat"><b>${s.rated}</b><span>com nota</span></div><div class="stat"><b>${s.average != null ? num(s.average) : "—"}</b><span>média</span></div></div>
<div class="panel"><h2>Suas notas</h2><div class="hist" role="list">${[5, 4, 3, 2, 1].map((n) => `<div role="listitem"><span>${n}★</span><span class="track"><i style="width:${s.rated ? (s.histogram[n] / s.rated) * 100 : 0}%"></i></span><span>${s.histogram[n]}</span></div>`).join("")}</div></div>
${s.top.length ? `<div class="panel"><h2>Você gosta de (nota ≥ 4)</h2><p class="note">${tab === "film" ? "Décadas" : "Autores"} com mais notas altas</p><p class="refs">${s.top.map(([k, n]) => `<span class="chip">${esc(k)} · ${n}</span>`).join("")}</p></div>` : ""}
${[["Favoritos", s.favorites], ["Não curtiu", s.disliked]].map(([t, l]) => l.length ? `<div class="panel"><h2>${t}</h2><ul class="lines">${l.map((i) => `<li><span class="t">${esc(i.title)}${i.year && i.type === "film" ? ` <span class="r">${i.year}</span>` : ""}</span><span class="r">${stars(i.rating)}</span></li>`).join("")}</ul></div>` : "").join("")}
<div class="panel"><h2>Recentes</h2><ul class="lines">${s.recent.map((i) => `<li><span class="t">${esc(i.title)}</span><span class="r">${[stars(i.rating), fmtDate(i.date)].filter(Boolean).join(" · ")}</span></li>`).join("")}</ul></div>`;
  $("status").textContent = db.lastSync ? `Última sincronização: ${db.lastSync}` : "Ainda não sincronizado.";
  const has = db.items.some((i) => i.type === tab);
  $("hero").hidden = !has; $("hero-empty").hidden = has;
  $("empty-txt").textContent = tab === "book" ? "Importe o export do Goodreads em Dados para eu aprender com os livros que você leu." : "Atualize os dados do Letterboxd (ou importe o CSV) em Dados para eu conhecer seus filmes.";
  renderNav();
}

async function fetchXml(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.text();
}

async function sync() {
  const st = $("status"), btn = $("sync");
  st.className = "note"; st.textContent = "Atualizando…"; btn.disabled = true;
  const jobs = [["Letterboxd", "./data/letterboxd.xml", parseLetterboxdRss], ["Goodreads", "./data/goodreads.xml", parseGoodreadsRss]];
  const msgs = []; let ok = 0;
  for (const [name, url, parse] of jobs) {
    try {
      const r = merge(db.items, parse(await fetchXml(url + "?t=" + Date.now())));
      db.items = r.items; ok++; msgs.push(`${name}: +${r.added} novos, ${r.updated} atualizados`);
    } catch (e) { msgs.push(`${name}: sem dados coletados ainda (${e.message}); use o CSV como alternativa`); }
  }
  if (ok) db.lastSync = new Date().toLocaleString("pt-BR");
  save(); render(); btn.disabled = false;
  st.className = "note " + (ok === jobs.length ? "ok" : "err"); st.textContent = msgs.join(" · ");
  if (ok) toast("Dados atualizados");
}

async function importCsv(file) {
  const msg = $("csvmsg");
  const { type, items } = parseCsvHistory(await file.text());
  if (!type) { msg.className = "note err"; msg.textContent = "Não reconheci o arquivo (esperado: ratings.csv do Letterboxd ou export do Goodreads)."; return; }
  const r = merge(db.items, items); db.items = r.items; save();
  tab = type; cur = []; render(); renderSugs();
  msg.className = "note ok"; msg.textContent = `${type === "film" ? "Filmes" : "Livros"}: +${r.added} novos, ${r.updated} atualizados.`;
}

document.querySelectorAll("#kind button").forEach((b) => b.addEventListener("click", () => { tab = b.dataset.t; cur = []; openChat = null; picks = []; rating = null; $("recmsg").innerHTML = ""; $("blmsg").innerHTML = ""; render(); renderSugs(); }));
save(); // grava já sem a chave antiga
let openChat = null, busy = false, rating = null, picks = [];
const notice = (cls, html, role) => `<div class="notice ${cls}" ${role ? `role="${role}"` : ""}>${html}</div>`;

function renderBacklog() {
  const list = backlog(db.feedback, tab), v = tab === "film" ? "Já vi" : "Já li";
  $("blpicks").innerHTML = picks.length ? `<div class="picks"><h2>Combina com você agora</h2>${picks.map((p) => `<div class="pick"><b>${esc(p.title)}</b><p>${esc(p.why)}</p></div>`).join("")}</div>` : "";
  $("blpick").hidden = !list.length;
  $("bllist").innerHTML = list.length ? list.map((w) => `<article class="item"><div class="item-head">${cover(w.title, w.year, tab, true)}<div><h3>${esc(w.title)}</h3><p class="meta">${meta(w)}</p></div></div>
${w.why ? `<p class="why">${esc(w.why)}</p>` : ""}
${rating === w.key ? `<div><p class="note">Que nota você dá?</p><div class="donebox">${[1, 2, 3, 4, 5].map((n) => `<button type="button" class="btn" data-bk="${esc(w.key)}" data-act="rate" data-n="${n}" aria-label="${n} estrelas">${n}★</button>`).join("")}<button type="button" class="btn quiet" data-bk="${esc(w.key)}" data-act="rate" data-n="0">Sem nota</button></div></div>`
  : `<div class="acts" style="grid-template-columns:1fr 1fr"><button type="button" class="btn primary" data-bk="${esc(w.key)}" data-act="done">${ICO.seen}${v}</button><button type="button" class="btn" data-bk="${esc(w.key)}" data-act="rm">Remover</button></div>`}</article>`).join("")
    : `<div class="empty"><h2 class="display sm">Backlog de ${kindWord()} vazio</h2><p class="lead">Toque em “Quero” numa indicação para guardar aqui.</p><button type="button" class="btn primary" data-go="indicar">Ver indicações</button></div>`;
}
$("bllist").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-act]"); if (!b) return; const k = b.dataset.bk;
  if (b.dataset.act === "done") rating = k;
  else if (b.dataset.act === "rate") { Object.assign(db, markDone(db, k, +b.dataset.n || null)); rating = null; picks = picks.filter((p) => p.title !== db.feedback[k]?.title); render(); toast(tab === "film" ? "Marcado como visto" : "Marcado como lido"); }
  else if (b.dataset.act === "rm") { db.feedback = removeFromBacklog(db.feedback, k); toast("Removido do backlog"); }
  save(); renderBacklog(); renderSugs();
});
$("blbtn").addEventListener("click", async () => {
  const m = $("blmsg"), btn = $("blbtn");
  if (!backlog(db.feedback, tab).length) { m.innerHTML = notice("err", "Seu backlog está vazio: marque “Quero” em alguma indicação primeiro.", "alert"); return; }
  btn.disabled = true; m.innerHTML = notice("", `Escolhendo do seu backlog…<div class="progress"><i></i></div>`);
  try { picks = await pickFromBacklog({ workerUrl, list: db.items, type: tab, mood: $("blmood").value, feedback: db.feedback }); m.innerHTML = ""; }
  catch (err) { picks = []; m.innerHTML = notice("err", `<p>${esc(err.message)}</p>`, "alert"); }
  btn.disabled = false; renderBacklog();
});
let cur = [];
const chatBox = (k) => { const msgs = db.chats[k] || [];
  return `<div class="chat" role="group" aria-label="Conversa sobre esta indicação">${msgs.length ? "" : '<p class="chat-hint">Pergunte, discorde ou peça outra opção.</p>'}${msgs.map((m) => `<div class="msg ${m.role}${m.error ? " error" : ""}">${esc(m.text)}</div>`).join("")}${busy ? '<div class="msg model wait">Pensando…</div>' : ""}
<form class="cf" data-k="${esc(k)}"><input maxlength="500" aria-label="Sua mensagem" placeholder="Ex.: tem algo mais leve?" autocomplete="off"><button class="btn primary" ${busy ? "disabled" : ""}>Enviar</button></form></div>`; };
function renderSugs() {
  const v = tab === "film" ? "Já vi" : "Já li";
  $("recs").innerHTML = cur.map((s, n) => { const k = sugKey(tab, s), st = db.feedback[k]?.status, pr = (a) => `aria-pressed="${st === a}"`;
    return `<article class="rec" style="animation-delay:${n * 60}ms"><div class="rec-head">${cover(s.title, s.year, tab)}<div><h3>${esc(s.title)}</h3><p class="meta">${meta(s)}</p></div></div>
${s.synopsis ? `<div class="syn"><span class="kicker">Sinopse</span><p>${esc(s.synopsis)}</p></div>` : ""}
<div class="why"><span class="kicker">Por que você gostaria</span><p>${esc(s.why)}</p></div>
${(s.refs || []).length ? `<div><span class="kicker">Do seu histórico</span><p class="refs">${s.refs.map((r) => `<span class="chip">${esc(r.title)}${r.rating ? ` · ${stars(r.rating)}` : ""}</span>`).join("")}</p></div>` : ""}
<div class="acts"><button type="button" class="btn primary" data-n="${n}" data-k="want" ${pr("want")}>${ICO.want}Quero</button><button type="button" class="btn" data-n="${n}" data-k="seen" ${pr("seen")}>${ICO.seen}${v}</button><button type="button" class="btn danger" data-n="${n}" data-k="no" ${pr("no")}>${ICO.no}Não curto</button>
<button type="button" class="btn chatb" data-n="${n}" data-chat="1" aria-expanded="${openChat === k}">${ICO.chat}${openChat === k ? "Fechar chat" : "Conversar"}</button></div>
${openChat === k ? chatBox(k) : ""}</article>`; }).join("");
  renderBacklog();
}
$("recs").addEventListener("click", (e) => {
  const c = e.target.closest("button[data-chat]");
  if (c) { const k = sugKey(tab, cur[+c.dataset.n]); openChat = openChat === k ? null : k; renderSugs(); $("recs").querySelector(".cf input")?.focus(); return; }
  const b = e.target.closest("button[data-k]"); if (!b) return;
  const before = db.feedback[sugKey(tab, cur[+b.dataset.n])]?.status;
  db.feedback = setFeedback(db.feedback, tab, cur[+b.dataset.n], b.dataset.k); save(); renderSugs();
  const after = db.feedback[sugKey(tab, cur[+b.dataset.n])]?.status;
  if (after !== before) toast({ want: "Guardado no backlog", seen: tab === "film" ? "Marcado como visto" : "Marcado como lido", no: "Não vou indicar de novo" }[after] || "Marcação removida");
});
$("recs").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target.closest(".cf"); if (!f || busy) return;
  const input = f.querySelector("input"), text = input.value.trim(), k = f.dataset.k; if (!text) return;
  const sug = cur.find((s) => sugKey(tab, s) === k), msgs = (db.chats[k] ||= []);
  msgs.push({ role: "user", text }); busy = true; save(); renderSugs();
  try {
    const r = await chat({ workerUrl, list: db.items, type: tab, feedback: db.feedback, suggestion: sug, messages: msgs.filter((m) => !m.error) });
    msgs.push({ role: "model", text: r });
  } catch (err) { msgs.push({ role: "model", text: err.message, error: true }); }
  busy = false; save(); renderSugs(); $("recs").querySelector(".cf input")?.focus();
});
$("export").addEventListener("click", () => {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([exportBackup(db)], { type: "application/json" }));
  a.download = `memoria-de-gosto-${new Date().toISOString().slice(0, 10)}.json`; a.click(); URL.revokeObjectURL(a.href);
  $("bkmsg").className = "note ok"; $("bkmsg").textContent = "Backup baixado."; toast("Backup baixado");
});
$("import").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return; const m = $("bkmsg");
  try { const r = importBackup(await f.text(), db); db.items = r.items; db.feedback = r.feedback; db.lastSync = r.lastSync; save(); render(); renderSugs(); m.className = "note ok"; m.textContent = `Backup restaurado (${r.items.length} itens, ${Object.keys(r.feedback).length} marcações).`; }
  catch (err) { m.className = "note err"; m.textContent = err.message; }
  e.target.value = "";
});
function skeleton() { return `<div class="sk" aria-hidden="true"><div class="b c"></div><div class="t"><div class="b l w"></div><div class="b l"></div><div class="b l"></div></div></div>`.repeat(3); }
async function rec() {
  const m = $("recmsg"), box = $("recs"), btn = $("rec"), kind = kindWord();
  if (!db.items.some((i) => i.type === tab)) { m.innerHTML = notice("err", `<p>Ainda não tenho nenhum dos seus ${kind}.</p><button type="button" class="btn" data-go="dados">Ir para Dados</button>`, "alert"); return; }
  const t0 = Date.now();
  btn.disabled = true; cur = []; openChat = null; box.innerHTML = skeleton();
  const tick = () => { const s = Math.round((Date.now() - t0) / 1000); $("reclabel").textContent = `Buscando… ${s}s`; m.innerHTML = notice("", `<p>Analisando seus ${kind} e escolhendo 5 indicações. Costuma levar de 5 a 20 segundos.</p><div class="progress"><i></i></div>`); };
  tick(); const timer = setInterval(tick, 1000);
  try {
    const list = await recommend({ workerUrl, list: db.items, type: tab, mood: $("mood").value, feedback: db.feedback });
    cur = list; renderSugs(); m.innerHTML = "";
    toast(`${list.length} indicações prontas`);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) { box.innerHTML = ""; m.innerHTML = notice("err", `<p><b>Não consegui buscar indicações.</b></p><p>${esc(e.message)}</p><button type="button" class="btn" id="retry">Tentar de novo</button>`, "alert"); }
  clearInterval(timer); $("reclabel").textContent = "Me indique 5"; btn.disabled = false;
}
$("recmsg").addEventListener("click", (e) => { if (e.target.closest("#retry")) rec(); });
$("rec").addEventListener("click", rec);
$("sync").addEventListener("click", sync);
$("csv").addEventListener("change", (e) => { if (e.target.files[0]) importCsv(e.target.files[0]); e.target.value = ""; });
$("rec").querySelector(".ic").innerHTML = ICO.spark;
go(location.hash.slice(1), false); render(); renderSugs();
