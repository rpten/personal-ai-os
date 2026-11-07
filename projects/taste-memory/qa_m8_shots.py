"""Print do cartão de indicação no celular. Uso: python3 qa_m8_shots.py <arquivo-saida> (Worker SIMULADO)."""
import functools, http.server, threading, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
here = Path(__file__).parent; fx = here / "app" / "fixtures"; out = sys.argv[1]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = "https://taste-memory-recs.simulado.workers.dev"
LONG = "Um homem é libertado após 15 anos de cativeiro sem explicação e tem apenas cinco dias para descobrir quem o prendeu e por quê. Na busca, ele se envolve com uma jovem chef e mergulha numa trama de vingança, memória e segredos de família que desafia o que ele pensava saber sobre si mesmo."
SUG = [{"title": "Oldboy", "year": 2003, "synopsis": LONG, "why": "Você deu 5★ a Parasita e gosta de thrillers coreanos com reviravolta moral.", "refs": [{"title": "Parasita", "rating": 4.5}, {"title": "Amélie, a Fabulosa", "rating": 4}]}] * 3
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
    pg.click("[data-v=dados]"); pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("#csvmsg.ok")
    pg.click("[data-v=indicar]"); pg.click("#rec"); pg.wait_for_selector(".rec")
    pg.wait_for_timeout(800)
    pg.locator(".rec").first.screenshot(path=out)
    b.close()
