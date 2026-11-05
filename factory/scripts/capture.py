#!/usr/bin/env python3
"""Prints de evidência de um app estático, em desktop e celular.

Uso:
  python factory/scripts/capture.py <dir_estatico> <dir_saida> [caminho ...]
Ex.: python factory/scripts/capture.py projects/leituras/public projects/leituras/evidence/m1 / /index.html#lista

Sobe um servidor local, abre cada caminho no Chromium headless e salva
<nome>-desktop.png e <nome>-mobile.png. Erros de console vão para console.txt.
Para fluxos com cliques, escreva um script Playwright próprio no marco.
"""
import functools
import http.server
import re
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    paths = sys.argv[3:] or ["/"]
    out.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, viewport in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
            page = browser.new_page(viewport=viewport)
            page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: logs.append(f"[pageerror] {e}"))
            for path in paths:
                page.goto(base + path, wait_until="networkidle")
                name = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-") or "home"
                page.screenshot(path=str(out / f"{name}-{label}.png"), full_page=True)
            page.close()
        browser.close()
    srv.shutdown()
    (out / "console.txt").write_text("\n".join(logs) or "sem erros de console\n")
    print(f"prints em {out}; erros de console: {len(logs)}")


if __name__ == "__main__":
    main()
