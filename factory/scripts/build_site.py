#!/usr/bin/env python3
"""Monta o site do GitHub Pages: painel de projetos + apps publicados.

_site/index.html     painel com status de cada projeto (lido dos state.json)
_site/<slug>/        cópia de projects/<slug>/public/
"""
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_site"
LABEL = {
    "discovery": ("Discovery", "#b08800"), "awaiting_plan_approval": ("Aguardando aprovação do plano", "#d1242f"),
    "executing": ("Em execução", "#0969da"), "awaiting_milestone_approval": ("Aguardando aprovação de marco", "#d1242f"),
    "blocked": ("Bloqueado: precisa de decisão", "#d1242f"), "delivered": ("Entregue", "#1a7f37"),
    "paused": ("Pausado", "#6e7781"), "closed": ("Encerrado", "#6e7781"),
}


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    cards = []
    for sp in sorted((ROOT / "projects").glob("*/state.json")):
        s = json.loads(sp.read_text())
        slug = s["slug"]
        pub = sp.parent / "public"
        if pub.is_dir():
            shutil.copytree(pub, OUT / slug)
        text, color = LABEL.get(s.get("status"), (s.get("status", "?"), "#6e7781"))
        ms = s.get("milestones", [])
        done = sum(1 for m in ms if m.get("status") == "done")
        link = f'<a href="{slug}/">Abrir app</a>' if pub.is_dir() else ""
        na = s.get("next_action") or {}
        nxt = ""
        if na.get("text"):
            who = "👉 Sua vez" if na.get("owner") == "rafael" else "⏳ Com o agente"
            cls = "you" if na.get("owner") == "rafael" else "agent"
            nxt = f'<p class="next {cls}"><b>{who}:</b> {html.escape(na["text"])}</p>'
        issue_link = f'<a href="https://github.com/rpten/personal-ai-os/issues/{s.get("issue")}">issue #{s.get("issue")}</a>'
        order = 0 if na.get("owner") == "rafael" else (1 if s.get("status") in LABEL and s.get("status") not in ("delivered","paused","closed") else 2)
        cards.append((order,
            f'<article><h2>{html.escape(s.get("title", slug))}</h2>'
            f'<p class="st" style="color:{color}">● {text}</p>'
            f'{nxt}<p>Marcos: {done}/{len(ms)} · {issue_link}</p>{link}</article>'
        ))
    body = "\n".join(c for _, c in sorted(cards, key=lambda x: x[0])) or "<p>Nenhum projeto ainda. Abra uma issue com o modelo “Nova ideia”.</p>"
    (OUT / "index.html").write_text(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Fábrica de projetos</title>
<style>:root{{color-scheme:light dark}}body{{font-family:system-ui,sans-serif;margin:0 auto;max-width:640px;padding:16px}}
article{{border:1px solid #8884;border-radius:10px;padding:12px 16px;margin:12px 0}}h2{{margin:.2em 0;font-size:1.1em}}
.st{{font-weight:600;margin:.3em 0}}.next{{padding:8px 10px;border-radius:8px;margin:.5em 0}}.you{{background:#fff3cd;color:#5c4400}}.agent{{background:#8881}}p{{margin:.3em 0}}</style></head>
<body><h1>Fábrica de projetos</h1>
<p><a href="https://github.com/rpten/personal-ai-os/issues/new?template=ideia.yml">➕ Nova ideia</a></p>{body}</body></html>""")
    (OUT / ".nojekyll").write_text("")
    print(f"site com {len(cards)} projeto(s) em {OUT}")


if __name__ == "__main__":
    main()
