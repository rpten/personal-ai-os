"""QA do M2 no navegador: Gemini simulado (sem chave real), erros e prints."""
import functools, http.server, threading, json
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).parent; fx = here / "app" / "fixtures"
out = here / "evidence" / "m2"; out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; errors = []; prompts = []
SUG = [{"title": f"Filme Novo {n}", "year": 2000 + n, "why": f"Combina com suas notas altas em dramas (sugestão {n})."} for n in range(1, 6)]
mode = {"v": "ok"}
def gem(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    prompts.append(r.request.post_data)
    if mode["v"] == "429": return r.fulfill(status=429, body="quota", headers=h)
    if mode["v"] == "400": return r.fulfill(status=400, body="API key not valid", headers=h)
    r.fulfill(status=200, headers={**h, "Content-Type": "application/json"}, body=json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(SUG)}]}}]}))

with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp); pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.route("https://generativelanguage.googleapis.com/**", gem)
        pg.goto(base)
        pg.click("#rec"); assert "chave do Gemini" in pg.inner_text("#recmsg")
        pg.fill("#gkey", "AIzaFAKE"); pg.click("#rec"); assert "histórico antes" in pg.inner_text("#recmsg")
        pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
        pg.fill("#mood", "algo leve"); pg.click("#rec"); pg.wait_for_selector(".sug")
        assert pg.locator(".sug").count() == 5
        assert "algo leve" in prompts[-1] and "Parasita" in prompts[-1]
        pg.screenshot(path=str(out / f"01-sugestoes-{label}.png"), full_page=True)
        mode["v"] = "429"; pg.click("#rec"); pg.wait_for_selector("text=Limite gratuito")
        pg.screenshot(path=str(out / f"02-cota-{label}.png"), full_page=True)
        mode["v"] = "400"; pg.click("#rec"); pg.wait_for_selector("text=Chave do Gemini inválida")
        mode["v"] = "ok"; pg.reload(); assert pg.input_value("#gkey") == "AIzaFAKE"  # chave persiste
        ctx.close()
    b.close()
real = [e for e in errors if "429" not in e and "400" not in e]
(out / "console.txt").write_text("\n".join(real) or "sem erros de console (além dos 429/400 simulados)\n")
print("QA OK; erros:", real)
