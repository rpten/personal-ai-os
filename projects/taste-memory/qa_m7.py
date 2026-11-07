"""QA funcional do M7: fluxo principal ponta a ponta no app redesenhado (Worker SIMULADO)."""
import functools, http.server, threading, json
from pathlib import Path
from playwright.sync_api import sync_playwright
here = Path(__file__).parent; fx = here / "app" / "fixtures"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = "https://taste-memory-recs.simulado.workers.dev"
calls = []
SUG = [{"title": f"Filme Novo {n}", "year": 2000 + n, "synopsis": "Sinopse curta.", "why": "Você deu 4,5★ a Parasita.", "refs": [{"title": "Parasita", "rating": 4.5}]} for n in range(1, 4)]
def worker(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    d = json.loads(r.request.post_data); calls.append((r.request.url.rsplit("/", 1)[1], d))
    p = r.request.url.rsplit("/", 1)[1]
    body = {"recs": {"suggestions": SUG}, "chat": {"reply": "Resposta simulada."}, "pick": {"picks": [{"title": "Filme Novo 2", "why": "Leve."}]}}[p]
    r.fulfill(status=200, headers={**h, "Content-Type": "application/json"}, body=json.dumps(body))
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for vp in ({"width": 1280, "height": 800}, {"width": 390, "height": 844}):
        calls.clear(); pg = b.new_context(viewport=vp).new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body=""))
        pg.route("**/config.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"workerUrl": W})))
        pg.route(W + "/**", worker); pg.goto(base)
        assert pg.is_visible("#hero-empty") and not pg.is_visible("#rec")
        pg.click("[data-v=dados]"); pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("#csvmsg.ok")
        assert "Filmes: +3 novos" in pg.inner_text("#csvmsg")
        pg.click("[data-v=gosto]"); t = pg.inner_text("#summary"); assert "4,25" in t and "5 jan 2020" in t
        pg.click("[data-v=indicar]"); pg.click("#rec"); pg.wait_for_selector(".rec")
        assert pg.locator(".rec").count() == 3 and calls[-1][0] == "recs"
        pg.click('.rec >> nth=0 >> [data-k=want]'); pg.click('.rec >> nth=1 >> [data-k=no]')
        assert pg.get_attribute('.rec >> nth=0 >> [data-k=want]', "aria-pressed") == "true"
        pg.click(".rec >> nth=0 >> .chatb"); pg.fill(".cf input", "algo mais leve?"); pg.press(".cf input", "Enter"); pg.wait_for_selector(".msg.model")
        assert calls[-1][0] == "chat"
        pg.click("[data-v=backlog]"); assert pg.locator("#bllist .item").count() == 1
        pg.fill("#blmood", "leve"); pg.click("#blbtn"); pg.wait_for_selector(".pick"); assert calls[-1][0] == "pick"
        pg.click('#bllist [data-act=done]'); pg.click('#bllist [data-n="4"]'); assert pg.locator("#bllist .item").count() == 0
        st = pg.evaluate("JSON.parse(localStorage.getItem('taste-memory:v1'))")
        assert any(i["source"] == "manual" and i["rating"] == 4 for i in st["items"]) and not any(f["status"] == "want" for f in st["feedback"].values())
        pg.click("[data-v=dados]")
        with pg.expect_download() as dl: pg.click("#export")
        assert dl.value.suggested_filename.startswith("memoria-de-gosto-")
        pg.reload(); pg.click("[data-v=gosto]"); assert "Parasita" in pg.inner_text("#summary")  # persiste
        assert not errs, errs
    b.close()
print("QA funcional M7 OK")
