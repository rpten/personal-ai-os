"""QA do M6: backlog por abas, Já vi/li com nota, remover, tirar do backlog (Worker SIMULADO)."""
import functools, http.server, threading, json
from pathlib import Path
from playwright.sync_api import sync_playwright
here = Path(__file__).parent; fx = here / "app" / "fixtures"
out = here / "evidence" / "m6"; out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = "https://taste-memory-recs.simulado.workers.dev"
calls = []
SUG = [{"title": f"Filme Novo {n}", "year": 2000 + n, "synopsis": "Sinopse curta.", "why": "Você deu 4,5★ a Parasita.", "refs": []} for n in range(1, 4)]
def worker(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    d = json.loads(r.request.post_data); calls.append((r.request.url, d))
    body = {"suggestions": SUG} if r.request.url.endswith("/recs") else {"picks": [{"title": "Filme Novo 2", "why": "Leve e curto, como você pediu."}]}
    r.fulfill(status=200, headers={**h, "Content-Type": "application/json"}, body=json.dumps(body))
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        calls.clear(); pg = b.new_context(viewport=vp).new_page()
        pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body=""))
        pg.route("**/config.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"workerUrl": W})))
        pg.route(W + "/**", worker); pg.goto(base)
        assert "Nada no backlog" in pg.inner_text("#bllist")
        pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
        pg.click("#rec"); pg.wait_for_selector(".sug")
        for n in (0, 1, 2): pg.click(f'#recs button[data-n="{n}"][data-k="want"]')
        assert pg.locator("#bllist .sug").count() == 3 and "Sinopse curta" in pg.inner_text("#bllist")
        pg.click('#bltabs button[data-t="book"]'); assert "Nada no backlog" in pg.inner_text("#bllist")
        pg.click('#bltabs button[data-t="film"]'); pg.screenshot(path=str(out / f"01-backlog-{label}.png"), full_page=True)
        pg.fill("#blmood", "algo leve"); pg.click("#blbtn"); pg.wait_for_selector(".pick")
        assert calls[-1][0].endswith("/pick") and calls[-1][1]["mood"] == "algo leve" and len(calls[-1][1]["profile"]["wants"]) == 3
        pg.screenshot(path=str(out / f"02-combina-{label}.png"), full_page=True)
        pg.click('#bllist button[data-act="done"] >> nth=0'); pg.wait_for_selector("text=Que nota?")
        pg.screenshot(path=str(out / f"03-nota-{label}.png"), full_page=True)
        pg.click('#bllist button[data-n="4"]'); assert pg.locator("#bllist .sug").count() == 2
        pg.click('#bllist button[data-act="rm"] >> nth=0'); assert pg.locator("#bllist .sug").count() == 1
        st = pg.evaluate("JSON.parse(localStorage.getItem('taste-memory:v1'))")
        assert any(i["source"] == "manual" and i["rating"] == 4 for i in st["items"])
        pg.reload(); pg.wait_for_selector("#bllist"); assert pg.locator("#bllist .sug").count() == 1  # persiste
        pg.screenshot(path=str(out / f"04-depois-{label}.png"), full_page=True)
    b.close()
print("QA M6 OK")
