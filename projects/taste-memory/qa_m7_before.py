"""Prints 'antes' do M7 (app do M6 intacto, Worker simulado). Rodar ANTES do redesign."""
import functools, http.server, threading, json
from pathlib import Path
from playwright.sync_api import sync_playwright
here = Path(__file__).parent; fx = here / "app" / "fixtures"; out = here / "evidence" / "m7"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = "https://taste-memory-recs.simulado.workers.dev"
SUG = [{"title": "Oldboy", "year": 2003, "synopsis": "Um homem é libertado após 15 anos de cativeiro e tem cinco dias para descobrir quem o prendeu.", "why": "Você deu 5★ a Parasita e gosta de thrillers coreanos com reviravolta moral.", "refs": [{"title": "Parasita", "rating": 4.5}, {"title": "Amélie, a Fabulosa", "rating": 4}]}] * 3
def worker(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    r.fulfill(status=200, headers={**h, "Content-Type": "application/json"}, body=json.dumps({"suggestions": SUG}))
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    pg = b.new_context(viewport={"width": 390, "height": 844}).new_page()
    pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body=""))
    pg.route("**/config.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"workerUrl": W})))
    pg.route(W + "/**", worker); pg.goto(base)
    pg.screenshot(path=str(out / "antes-1-vazio-mobile.png"), full_page=True)
    pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
    pg.screenshot(path=str(out / "antes-2-com-dados-mobile.png"), full_page=True)
    pg.click("#rec"); pg.wait_for_selector(".sug"); pg.click('#recs button[data-n="0"][data-k="want"]')
    pg.screenshot(path=str(out / "antes-3-indicacoes-mobile.png"), full_page=True)
    b.close()
