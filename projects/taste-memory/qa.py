"""QA do M1 no navegador: sync simulado (Worker falso), CSV, persistência, prints."""
import functools, http.server, threading, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).parent
fx = here / "app" / "fixtures"
out = here / "evidence" / "m1"; out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"
errors = []

def route(r):
    u = r.request.url
    body = (fx / ("letterboxd.xml" if "/letterboxd" in u else "goodreads.xml")).read_text()
    r.fulfill(status=200, body=body, headers={"Access-Control-Allow-Origin": "*", "Content-Type": "application/xml"})

with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp); pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.route("https://fake-worker.test/**", route)
        pg.goto(base)
        assert "Nenhum dos seus filmes" in pg.inner_text("#summary")
        pg.click("#sync")  # sem Worker: aviso
        assert "URL do Worker" in pg.inner_text("#status")
        pg.screenshot(path=str(out / f"01-vazio-{label}.png"), full_page=True)
        pg.set_input_files("#csv", str(fx / "ratings.csv"))
        pg.wait_for_selector("text=Filmes: +3 novos")
        pg.fill("#worker", "https://fake-worker.test")
        pg.click("#sync"); pg.wait_for_selector("text=Letterboxd: +2 novos")
        assert "Goodreads: +3 novos" in pg.inner_text("#status")
        s = pg.inner_text("#summary"); assert s.count("Parasita") >= 1
        pg.click("#sync"); pg.wait_for_selector("text=Letterboxd: +0 novos, 0 atualizados")
        pg.screenshot(path=str(out / f"02-filmes-{label}.png"), full_page=True)
        pg.click("[data-t=book]"); assert "Dom Casmurro" in pg.inner_text("#summary")
        pg.set_input_files("#csv", str(fx / "goodreads.csv")); pg.wait_for_selector("text=Livros: +1 novos")
        pg.screenshot(path=str(out / f"03-livros-{label}.png"), full_page=True)
        pg.reload()  # persistência
        pg.click("[data-t=film]"); assert "Parasita" in pg.inner_text("#summary")
        pg.set_input_files("#csv", {"name": "x.csv", "mimeType": "text/csv", "buffer": b"a,b\n1,2"})
        pg.wait_for_selector("text=Não reconheci")
        # Worker fora do ar: erro tratado
        pg.unroute("https://fake-worker.test/**"); pg.route("https://fake-worker.test/**", lambda r: r.fulfill(status=502, body="x", headers={"Access-Control-Allow-Origin": "*"}))
        pg.click("#sync"); pg.wait_for_selector("text=falhou (HTTP 502)")
        pg.screenshot(path=str(out / f"04-erro-{label}.png"), full_page=True)
        ctx.close()
    b.close()
real = [e for e in errors if "502" not in e]
(out / "console.txt").write_text("\n".join(real) or "sem erros de console (além do 502 simulado)\n")
print("QA OK; erros de console:", real)
