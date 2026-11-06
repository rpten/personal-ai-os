"""QA do M4 no navegador contra o Worker REAL (Cloudflare + Gemini reais).
O navegador roda em localhost; o proxy de rota repassa a chamada ao Worker com Origin do GitHub Pages (CORS só aceita essa origem)."""
import functools, http.server, threading, json, urllib.request, urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).parent; fx = here / "app" / "fixtures"
out = here / "evidence" / "m4"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = json.load(open(here / "public" / "config.json"))["workerUrl"]
errors = []; log = []
def proxy(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    req = urllib.request.Request(r.request.url, data=r.request.post_data.encode(), method="POST", headers={"User-Agent": "Mozilla/5.0", "Origin": "https://rpten.github.io", "Content-Type": "application/json"})
    try: resp = urllib.request.urlopen(req, timeout=90); st, body = resp.status, resp.read()
    except urllib.error.HTTPError as e: st, body = e.code, e.read()
    log.append((r.request.url.rsplit("/", 1)[1], st))
    r.fulfill(status=st, headers={**h, "Content-Type": "application/json"}, body=body)
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp); pg = ctx.new_page(); pg.set_default_timeout(90000)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body=""))
        pg.route(W + "/**", proxy)
        pg.goto(base)
        pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
        pg.fill("#mood", "algo leve"); pg.click("#rec")
        try: pg.wait_for_selector(".sug")
        except Exception: print(log, errors, pg.inner_text("body")[-600:]); raise
        assert pg.locator(".syn").count() >= 1
        pg.screenshot(path=str(out / f"real-01-indicacoes-{label}.png"), full_page=True)
        pg.locator('button[data-chat]').first.click()
        pg.fill(".cf input", "Por que acha que vou gostar?"); pg.press(".cf input", "Enter")
        pg.wait_for_selector(".msg.model:not(.muted)")
        pg.screenshot(path=str(out / f"real-02-chat-{label}.png"), full_page=True)
        assert "AIza" not in pg.evaluate("localStorage.getItem('taste-memory:v1')")
        ctx.close()
    b.close()
(out / "console-real.txt").write_text(f"chamadas ao Worker real: {log}\n" + ("\n".join(e for e in errors if "404" not in e) or "sem erros de console (além do 404 do RSS ausente na máquina local)") + "\n")
print("QA REAL OK", log, errors)
