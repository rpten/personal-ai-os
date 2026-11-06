"""QA do M5: feedback de progresso e indicação sem pedir direcionamento (Worker SIMULADO, com atraso de 2,5s)."""
import functools, http.server, threading, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright
here = Path(__file__).parent; fx = here / "app" / "fixtures"
out = here / "evidence" / "m5"; out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = "https://taste-memory-recs.simulado.workers.dev"
calls = []
SUG = [{"title": f"Filme Novo {n}", "year": 2000 + n, "synopsis": "Sinopse curta.", "why": "Você deu 4,5★ a Parasita.", "refs": [{"title": "Parasita", "year": 2019, "rating": 4.5}]} for n in range(1, 4)]
def worker(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    calls.append(json.loads(r.request.post_data))
    r.fulfill(status=200, headers={**h, "Content-Type": "application/json"}, body=json.dumps({"suggestions": SUG}))
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        calls.clear(); pg = b.new_context(viewport=vp).new_page()
        pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body=""))
        pg.route("**/config.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"workerUrl": W})))
        pg.route(W + "/**", worker)
        pg.add_init_script("const f=window.fetch;window.fetch=(u,o)=>String(u).includes('simulado')&&o&&o.method==='POST'?new Promise(r=>setTimeout(r,2500)).then(()=>f(u,o)):f(u,o)")
        pg.goto(base)
        pg.click('#tabs button[data-t="book"]'); pg.click("#rec")
        assert "Goodreads" in pg.inner_text("#recmsg"); pg.screenshot(path=str(out / f"01-sem-livros-{label}.png"), full_page=True)
        pg.click('#tabs button[data-t="film"]')
        pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
        pg.click("#rec"); pg.wait_for_selector("text=Buscando")
        assert pg.is_disabled("#rec") and "Analisando" in pg.inner_text("#recmsg")
        pg.screenshot(path=str(out / f"02-buscando-{label}.png"), full_page=True)
        pg.wait_for_selector(".sug"); assert "Pronto: 3" in pg.inner_text("#recmsg") and pg.inner_text("#rec") == "Me indique 5" and not pg.is_disabled("#rec")
        assert calls[0]["mood"] == ""
        pg.screenshot(path=str(out / f"03-indicacoes-{label}.png"), full_page=True)
        pg.click("summary"); pg.fill("#mood", "algo leve"); pg.click("#rec"); pg.wait_for_selector("text=Pronto"); assert calls[1]["mood"] == "algo leve"
    b.close()
print("QA M5 OK")
