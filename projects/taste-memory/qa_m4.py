"""QA do M4 no navegador contra um Worker SIMULADO (sem Gemini e sem Cloudflare reais)."""
import functools, http.server, threading, json
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).parent; fx = here / "app" / "fixtures"
out = here / "evidence" / "m4"; out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(here / "public")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}/"; W = "https://taste-memory-recs.simulado.workers.dev"
errors = []; calls = []
SUG = [{"title": f"Filme Novo {n}", "year": 2000 + n, "synopsis": f"Sinopse curta do filme {n}, sem spoilers.", "why": "Você deu 4,5★ a Parasita; este tem a mesma crítica social.",
        "refs": [{"title": "Parasita", "year": 2019, "rating": 4.5}]} for n in range(1, 4)]
mode = {"chat": "ok"}
def worker(r):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if r.request.method == "OPTIONS": return r.fulfill(status=204, headers=h)
    body = json.loads(r.request.post_data); calls.append((r.request.url, body))
    j = {**h, "Content-Type": "application/json"}
    if r.request.url.endswith("/recs"): return r.fulfill(status=200, headers=j, body=json.dumps({"suggestions": SUG}))
    if mode["chat"] == "429": return r.fulfill(status=429, headers=j, body=json.dumps({"error": "Limite gratuito do Gemini atingido. Tente de novo em alguns minutos."}))
    r.fulfill(status=200, headers=j, body=json.dumps({"reply": "Entendo! Se violência pesa, tente outra comédia leve: leve e visual, parecido com o que você curtiu."}))

with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")
    for label, vp in (("desktop", {"width": 1280, "height": 800}), ("mobile", {"width": 390, "height": 844})):
        mode["chat"] = "ok"; calls.clear()
        ctx = b.new_context(viewport=vp); pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.route("**/data/*.xml*", lambda r: r.fulfill(status=404, body=""))
        pg.route("**/config.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"workerUrl": W})))
        pg.route(W + "/**", worker)
        pg.goto(base)
        # resto de versão antiga: chave no localStorage deve sumir
        pg.evaluate("localStorage.setItem('taste-memory:v1', JSON.stringify({items: [], cfg: {gkey: 'AIzaVELHA'}, feedback: {}}))"); pg.reload()
        assert "AIzaVELHA" not in pg.evaluate("localStorage.getItem('taste-memory:v1')")
        assert pg.locator("#gkey").count() == 0 and "chave" not in pg.inner_text("body").lower()
        pg.set_input_files("#csv", str(fx / "ratings.csv")); pg.wait_for_selector("text=Filmes: +3 novos")
        pg.fill("#mood", "algo leve"); pg.click("#rec"); pg.wait_for_selector(".sug")
        assert calls[0][0].endswith("/recs") and calls[0][1]["mood"] == "algo leve"
        assert any(i["title"] == "Parasita" and i["rating"] == 4.5 for i in calls[0][1]["profile"]["loved"])
        assert pg.locator(".syn").count() == 3 and pg.locator(".chip").first.inner_text().startswith("Parasita · 4.5")
        pg.screenshot(path=str(out / f"01-indicacoes-{label}.png"), full_page=True)
        pg.locator('button[data-chat]').first.click()
        pg.fill(".cf input", "Não gosto de violência. Tem algo mais leve?"); pg.press(".cf input", "Enter")
        pg.wait_for_selector(".msg.model:not(.muted)")
        assert "comédia leve" in pg.inner_text(".msg.model") and calls[-1][0].endswith("/chat")
        assert calls[-1][1]["suggestion"]["title"] == "Filme Novo 1" and calls[-1][1]["messages"][-1]["role"] == "user"
        pg.fill(".cf input", "Discordo, achei que combinava."); mode["chat"] = "429"; pg.press(".cf input", "Enter")
        pg.wait_for_selector("text=Limite gratuito")
        pg.screenshot(path=str(out / f"02-chat-{label}.png"), full_page=True)
        # feedback continua funcionando e o chat persiste ao recarregar
        pg.locator('button[data-k="want"]').first.click()
        assert "on" in pg.locator('button[data-k="want"]').first.get_attribute("class")
        st = pg.evaluate("localStorage.getItem('taste-memory:v1')"); assert "AIza" not in st and '"want"' in st and "comédia leve" in st
        # sem Worker publicado: mensagem clara
        pg.unroute("**/config.json*"); pg.route("**/config.json*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"workerUrl": ""}'))
        pg.reload(); pg.fill("#mood", ""); pg.click("#rec"); pg.wait_for_selector("text=ainda não foi publicado")
        pg.screenshot(path=str(out / f"03-sem-worker-{label}.png"), full_page=True)
        ctx.close()
    b.close()
(out / "console.txt").write_text("\n".join(e for e in errors if "404" not in e and "429" not in e) or "sem erros de console (além do 404 simulado do RSS e do 429 simulado do chat)\n")
print("QA OK; erros:", errors)
