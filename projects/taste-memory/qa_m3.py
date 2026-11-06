"""QA do M3 no navegador: Gemini simulado, feedback, persistência e backup."""
import functools, http.server, threading, json
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).parent; fx = here / "app" / "fixtures"
out = here / "evidence" / "m3"; out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; errors = []; prompts = []
SUG = [{"title": f"Filme Novo {n}", "year": 2000 + n, "why": f"Combina com suas notas altas (sugestão {n})."} for n in range(1, 6)]
def gem(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    prompts.append(r.request.post_data)
    r.fulfill(status=200, headers={**h, "Content-Type": "application/json"}, body=json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(SUG)}]}}]}))

with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp, accept_downloads=True); pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body="")) 
        pg.route("https://generativelanguage.googleapis.com/**", gem)
        pg.goto(base)
        pg.click("#settings summary"); pg.fill("#gkey", "AIzaFAKE")
        pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
        pg.screenshot(path=str(out / f"01-resumo-{label}.png"), full_page=True)
        pg.click("#rec"); pg.wait_for_selector(".sug")
        btn = lambda n, k: pg.locator(f'button[data-n="{n}"][data-k="{k}"]')
        btn(0, "seen").click(); btn(1, "want").click(); btn(2, "no").click()
        assert "on" in btn(1, "want").get_attribute("class")
        pg.screenshot(path=str(out / f"02-feedback-{label}.png"), full_page=True)
        pg.reload()
        pg.click("#rec"); pg.wait_for_selector(".sug")
        p2 = prompts[-1]
        assert "Filme Novo 1" in p2 and "Filme Novo 3" in p2 and "Quer ver" in p2 and "Filme Novo 2" in p2
        titles = pg.locator(".sug b").all_inner_texts()
        assert titles == ["Filme Novo 4", "Filme Novo 5"], titles  # já vi/quero/não curto não voltam
        assert pg.locator("#wants li").count() == 1
        pg.screenshot(path=str(out / f"03-depois-{label}.png"), full_page=True)
        with pg.expect_download() as d: pg.click("#export")
        f = out / f"backup-{label}.json"; d.value.save_as(str(f))
        assert "SEGREDO" not in f.read_text() and "AIzaFAKE" not in f.read_text()
        pg.evaluate("localStorage.clear()"); pg.reload()
        assert pg.locator("#wants li").count() == 0
        pg.set_input_files("#import", str(f)); pg.wait_for_selector("text=Backup restaurado")
        assert pg.locator(".stat b").first.inner_text() == "3"
        pg.screenshot(path=str(out / f"04-backup-{label}.png"), full_page=True)
        pg.set_input_files("#import", str(fx / "ratings.csv")); pg.wait_for_selector("text=backup inválido")
        ctx.close()
    b.close()
(out / "console.txt").write_text("\n".join(e for e in errors if "404" not in e) or "sem erros de console (além dos 404 simulados do RSS)\n")
print("QA OK; erros:", errors)
