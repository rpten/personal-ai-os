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
        cards.append(
            f'<article><h2>{html.escape(s.get("title", slug))}</h2>'
            f'<p class="st" style="color:{color}">● {text}</p>'
            f'<p>Marcos: {done}/{len(ms)} · issue #{s.get("issue")}</p>{link}</article>'
        )
    body = "\n".join(cards) or "<p>Nenhum projeto ainda. Abra uma issue com o modelo “Nova ideia”.</p>"
    (OUT / "index.html").write_text(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Fábrica de projetos</title>
<style>:root{{color-scheme:light dark}}body{{font-family:system-ui,sans-serif;margin:0 auto;max-width:640px;padding:16px}}
article{{border:1px solid #8884;border-radius:10px;padding:12px 16px;margin:12px 0}}h2{{margin:.2em 0;font-size:1.1em}}
.st{{font-weight:600;margin:.3em 0}}p{{margin:.3em 0}}</style></head>
<body><h1>Fábrica de projetos</h1>{body}</body></html>""")
    (OUT / ".nojekyll").write_text("")
    print(f"site com {len(cards)} projeto(s) em {OUT}")


if __name__ == "__main__":
    main()
