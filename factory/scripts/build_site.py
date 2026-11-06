#!/usr/bin/env python3
"""Monta o site do GitHub Pages: painel da fábrica + apps publicados.

_site/index.html     painel (lido dos state.json e do ledger de eventos)
_site/<slug>/        cópia de projects/<slug>/public/
"""
import html
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

ROOT = common.ROOT
OUT = ROOT / "_site"
REPO = "rpten/personal-ai-os"
STATUS = {
    "discovery": ("Discovery", "warn"), "awaiting_plan_approval": ("Aguardando aprovação do plano", "you"),
    "executing": ("Em execução", "info"), "awaiting_milestone_approval": ("Aguardando aprovação de marco", "you"),
    "blocked": ("Bloqueado: precisa de decisão", "you"), "delivered": ("Entregue", "ok"),
    "paused": ("Pausado", "mute"), "closed": ("Encerrado", "mute"),
}
OUTCOME = {"done": "✅", "waiting": "👉", "blocked": "⛔", "failed": "❌", "ignored": "⚪", "queued": "📥"}
OUTCOME_TXT = {"done": "concluído", "waiting": "concluído, aguardando você", "blocked": "bloqueado",
               "failed": "falhou", "ignored": "ignorado", "queued": "na fila"}
import re


def e(text):
    """Escapa HTML e transforma URLs em links."""
    t = html.escape(str(text))
    return re.sub(r"(https?://[^\s<]+[^\s<.,;:)])", r'<a href="\1">\1</a>', t)


def when(iso):
    return (iso or "")[:16].replace("T", " ") + (" UTC" if iso else "")


def card(s, has_app):
    slug = s["slug"]
    label, tone = STATUS.get(s.get("status"), (s.get("status", "?"), "mute"))
    ms = s.get("milestones", [])
    done = sum(1 for m in ms if m.get("status") == "done")
    na = s.get("next_action") or {}
    le = s.get("last_event") or {}
    nxt = ""
    if na.get("text") and s.get("status") not in ("closed",):
        who = "👉 Sua vez" if na.get("owner") == "rafael" else "⏳ Com o agente"
        nxt = f'<p class="next {"you" if na.get("owner") == "rafael" else "agent"}"><b>{who}:</b> {e(na["text"])}</p>'
    last = f'<p class="muted">Último: {e(le.get("summary", ""))} · {when(le.get("at"))}</p>' if le else ""
    links = [f'<a href="https://github.com/{REPO}/issues/{s.get("issue")}">issue #{s.get("issue")}</a>']
    if has_app:
        links.append(f'<a href="{slug}/">abrir app</a>')
    return (f'<article><h3>{e(s.get("title", slug))}</h3><p class="pill {tone}">{label}</p>{nxt}'
            f'<p>Marcos: {done}/{len(ms)}</p>{last}<p>{" · ".join(links)}</p></article>')


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    states = common.load_states()
    titles = {s["slug"]: s.get("title", s["slug"]) for s in states}
    has_app = {}
    for s in states:
        pub = ROOT / "projects" / s["slug"] / "public"
        has_app[s["slug"]] = pub.is_dir()
        if pub.is_dir():
            shutil.copytree(pub, OUT / s["slug"])

    you = [s for s in states if s.get("status") not in ("closed", "paused")
           and (s.get("next_action") or {}).get("owner") == "rafael"]
    active = [s for s in states if s.get("status") in common.ACTIVE]
    done = [s for s in states if s.get("status") == "delivered"]
    other = [s for s in states if s.get("status") in ("paused", "closed")]
    ledger = common.read_ledger()
    queued = {r.get("issue") for r in ledger if r.get("outcome") == "queued"} - {s.get("issue") for s in states}
    failed_recent = [r for r in ledger[-10:] if r.get("outcome") == "failed"]

    need = "".join(
        f'<li><b>{e(s.get("title", s["slug"]))}:</b> {e(s["next_action"]["text"])}</li>' for s in you
    ) or "<li>Nada. A fábrica não precisa de você agora.</li>"

    hist = []
    for r in reversed(ledger[-25:]):
        proj = titles.get(r.get("slug"), "") or (f'issue #{r["issue"]}' if r.get("issue") else "fábrica")
        hist.append(f'<li><span class="muted">{when(r.get("at"))}</span> {OUTCOME.get(r.get("outcome"), "•")} '
                    f'<b>{e(proj)}</b>: {e(OUTCOME_TXT.get(r.get("outcome"), r.get("outcome", "")))}'
                    f'{" — " + e(r["summary"]) if r.get("summary") else ""}</li>')
    hist_html = "".join(hist) or "<li class='muted'>Sem eventos registrados ainda.</li>"

    def section(title, items):
        return f"<h2>{title} <span class='muted'>({len(items)})</span></h2>" + "".join(card(s, has_app[s["slug"]]) for s in items) if items else ""

    alert = (f'<p class="pill you">⚠️ {len(failed_recent)} falha(s) recente(s): ver histórico. A fábrica tenta de novo sozinha.</p>'
             if failed_recent else "")
    body = f"""
<header><h1>Fábrica</h1><a class="btn" href="https://github.com/{REPO}/issues/new?template=ideia.yml">➕ Nova ideia</a></header>
<p class="muted">Ativos {len(active)} · Na fila {len(queued)} · Entregues {len(done)}</p>{alert}
<section class="need"><h2>Preciso de você</h2><ul>{need}</ul></section>
{section("Ativos", active)}{section("Entregues", done)}{section("Pausados e encerrados", other)}
<h2>Histórico</h2><ul class="hist">{hist_html}</ul>"""

    (OUT / "index.html").write_text(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Fábrica</title>
<style>
:root{{--bg:#fff;--fg:#1f2328;--mute:#656d76;--line:#d0d7de;--you:#fff3cd;--youfg:#5c4400;--ok:#dafbe1;--okfg:#116329;--info:#ddf4ff;--infofg:#0550ae}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1117;--fg:#e6edf3;--mute:#8d96a0;--line:#30363d;--you:#3b2e00;--youfg:#f2cc60;--ok:#033a16;--okfg:#7ee787;--info:#0c2d6b;--infofg:#79c0ff}}}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,sans-serif;margin:0 auto;max-width:680px;padding:16px;line-height:1.4}}
header{{display:flex;justify-content:space-between;align-items:center}}h1{{margin:.2em 0}}h2{{font-size:1.05em;margin:1.4em 0 .4em}}
h3{{margin:.1em 0;font-size:1em}}a{{color:var(--infofg)}}.btn{{background:var(--fg);color:var(--bg);padding:8px 12px;border-radius:8px;text-decoration:none;font-weight:600}}
article{{border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:10px 0}}p{{margin:.3em 0}}
.muted{{color:var(--mute);font-size:.9em}}.pill{{display:inline-block;padding:2px 8px;border-radius:99px;font-size:.85em;font-weight:600}}
.you{{background:var(--you);color:var(--youfg)}}.ok{{background:var(--ok);color:var(--okfg)}}.info,.warn{{background:var(--info);color:var(--infofg)}}.mute{{background:var(--line)}}
.next{{padding:8px 10px;border-radius:8px}}.agent{{background:var(--line)}}
.need{{border:2px solid var(--youfg);border-radius:10px;padding:4px 14px}}.need ul,.hist{{padding-left:18px}}.hist li{{margin:.35em 0}}
</style></head><body>{body}</body></html>""")
    (OUT / ".nojekyll").write_text("")
    print(f"site com {len(states)} projeto(s) e {len(ledger)} evento(s) em {OUT}")


if __name__ == "__main__":
    main()
