import functools, http.server, threading, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = Path("public").resolve(); out = Path("evidence/m1"); out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"
R = {"ideia": "Um app para organizar minhas leituras", "usuario": "Eu mesmo, no celular", "dor": "Esqueço o que li e o que quero ler",
     "fluxo": "Abro, adiciono um livro, marco como lido", "pronto": "Uso sem ajuda em 2 minutos", "fora": "Login; sincronização; recomendações"}
logs = []
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        pg = b.new_page(viewport=vp)
        pg.on("console", lambda m: logs.append(m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: logs.append(str(e)))
        pg.goto(base); pg.screenshot(path=str(out / f"1-formulario-{label}.png"), full_page=True)
        pg.click("button[type=submit]")  # vazio -> erro
        assert pg.is_visible("#erro") and pg.is_hidden("#saida"), "erro de validação não apareceu"
        pg.screenshot(path=str(out / f"2-erro-{label}.png"), full_page=True)
        for k, v in R.items(): pg.fill(f"#{k}", v)
        pg.click("button[type=submit]")
        t = pg.inner_text("#texto")
        for s in ["Resumo", "Menor versão útil", "Marcos", "Próximo passo", "Riscos", "Backlog", "Checklist de pronto"]:
            assert f"## {s}" in t, s
        assert pg.is_hidden("#erro")
        pg.wait_for_timeout(600)
        pg.screenshot(path=str(out / f"3-plano-{label}.png"), full_page=True)
        pg.close()
    b.close()
srv.shutdown()
(out / "console.txt").write_text("\n".join(logs) or "sem erros de console\n")
print("ok; erros de console:", len(logs))
