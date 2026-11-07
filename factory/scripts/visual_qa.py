#!/usr/bin/env python3
"""QA visual automatizado: prints reais + detecção de problemas visuais.

Uso:
  python factory/scripts/visual_qa.py <dir_publico> <dir_saida> [--flows design/flows.json] [--commit SHA]

Para cada fluxo × viewport (celular 390×844, desktop 1280×800) abre o app num
Chromium headless, executa as ações do fluxo, tira print de página inteira e
mede, no DOM renderizado:

  bloqueantes  rolagem horizontal; elemento saindo da tela; texto < 12px;
               contraste < 4.5:1 (texto normal) ou < 3:1 (texto grande);
               controle sem nome acessível; imagem quebrada ou sem alt;
               erro de JavaScript/console; falta de meta viewport
  avisos       alvo de toque < 44px no celular; texto cortado sem reticências;
               controles interativos sobrepostos; linha de texto > 90 caracteres

Saídas em <dir_saida>: <fluxo>-<viewport>.png, visual-qa.json, visual-qa.md.
Código de saída 1 se houver bloqueante (ou fluxo que falhou ao executar).

Isto NÃO substitui a inspeção visual (hierarquia, composição, identidade):
quem implementa precisa olhar cada print (ver skill fabrica-design).

Formato de flows.json (opcional; sem ele, testa só "/"):
{
  "routes": [{"match": "**/config.json*", "status": 200, "json": {...}}],
  "flows": [
    {"name": "inicio", "path": "/", "steps": []},
    {"name": "erro", "path": "/", "routes": [{"match": "https://api.x/**", "status": 500, "json": {"error": "x"}}],
     "steps": [{"click": "#rec"}, {"wait_for": ".erro"}]},
    {"name": "carregando", "path": "/", "routes": [{"match": "https://api.x/**", "hold": true}],
     "steps": [{"click": "#rec"}, {"wait_ms": 400}]}
  ]
}
Passos: click, fill [seletor, texto], set_files [seletor, caminho relativo a flows.json],
wait_for, wait_ms, press [seletor, tecla], eval (JS).
"""
import argparse
import functools
import http.server
import json
import re
import sys
import threading
from pathlib import Path

VIEWPORTS = {"mobile": {"width": 390, "height": 844}, "desktop": {"width": 1280, "height": 800}}

CHECK_JS = r"""
(isMobile) => {
  const out = [];
  const W = document.documentElement.clientWidth;
  const vis = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05 && r.width > 0 && r.height > 0; };
  const sel = el => { if (el.id) return '#' + el.id; let p = el.tagName.toLowerCase();
    if (el.classList.length) p += '.' + [...el.classList].slice(0, 2).join('.');
    const par = el.parentElement; return (par && par !== document.body ? sel(par) + ' > ' : '') + p; };
  const txt = el => (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 40);
  const add = (severity, rule, el, detail) => out.push({severity, rule, selector: el ? sel(el) : null, text: el ? txt(el) : '', detail});

  if (!document.querySelector('meta[name=viewport]')) add('blocking', 'sem-meta-viewport', null, 'falta <meta name="viewport">');
  const sw = document.scrollingElement.scrollWidth;
  if (sw > W + 1) add('blocking', 'rolagem-horizontal', null, `largura do conteúdo ${sw}px > tela ${W}px`);

  const scrollsX = el => { for (let p = el.parentElement; p; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return true; } return false; };

  // cor efetiva de fundo (sobe pelos ancestrais; ignora imagens/gradientes)
  const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
  const bgOf = el => { let layers = [];
    for (let p = el; p; p = p.parentElement) { const s = getComputedStyle(p);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null;
      const c = parse(s.backgroundColor); if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; } }
    let base = [255, 255, 255];
    for (const c of layers.reverse()) base = base.map((b, i) => c[i] * c[3] + b * (1 - c[3]));
    return base; };
  const lum = rgb => { const a = rgb.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2]; };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };

  const seenText = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode; if (!n.textContent.trim()) continue;
    const el = n.parentElement; if (!el || seenText.has(el) || !vis(el)) continue; seenText.add(el);
    if (el.closest('[aria-hidden=true], script, style, noscript')) continue;
    const s = getComputedStyle(el); const fs = parseFloat(s.fontSize);
    if (fs < 12) add('blocking', 'texto-pequeno', el, `fonte ${fs}px (< 12px)`);
    const fg = parse(s.color); const bg = bgOf(el);
    if (fg && bg) {
      const eff = fg.slice(0, 3).map((v, i) => v * fg[3] + bg[i] * (1 - fg[3]));
      const r = ratio(eff, bg); const large = fs >= 24 || (fs >= 18.66 && +s.fontWeight >= 700);
      const min = large ? 3 : 4.5;
      if (r < min && !el.closest('button:disabled, [aria-disabled=true]')) add('blocking', 'contraste', el, `contraste ${r.toFixed(2)}:1 (< ${min}:1)`);
    }
    const r = el.getBoundingClientRect();
    if (s.display !== 'inline' && r.width > 0) { const cpl = r.width / (fs * 0.5); if (cpl > 90 && n.textContent.trim().length > 120) add('warning', 'linha-longa', el, `~${Math.round(cpl)} caracteres por linha`); }
  }

  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if ((r.right > W + 1 || r.left < -1) && !scrollsX(el) && getComputedStyle(el).position !== 'fixed')
      add('blocking', 'sai-da-tela', el, `borda em ${Math.round(r.left)}–${Math.round(r.right)}px; tela ${W}px`);
    const s = getComputedStyle(el);
    if ((s.overflow === 'hidden' || s.overflowX === 'hidden') && s.textOverflow !== 'ellipsis' && el.scrollWidth > el.clientWidth + 2 && el.children.length === 0)
      add('warning', 'texto-cortado', el, `conteúdo ${el.scrollWidth}px em caixa de ${el.clientWidth}px`);
  }

  const inter = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [tabindex]:not([tabindex="-1"])')].filter(vis);
  for (const el of inter) {
    const r = el.getBoundingClientRect();
    const name = (el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || el.value || el.getAttribute('placeholder') || '').trim()
      || (el.id && document.querySelector(`label[for="${el.id}"]`)) || el.closest('label') || el.getAttribute('aria-labelledby');
    if (!name && el.type !== 'file') add('blocking', 'sem-nome-acessivel', el, 'controle sem rótulo/nome acessível');
    if (isMobile && (r.height < 43.5 || r.width < 43.5) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'))
      add('warning', 'alvo-pequeno', el, `${Math.round(r.width)}×${Math.round(r.height)}px (< 44px)`);
  }
  for (let i = 0; i < inter.length; i++) for (let j = i + 1; j < inter.length; j++) {
    const a = inter[i], b = inter[j]; if (a.contains(b) || b.contains(a)) continue;
    const p = a.getBoundingClientRect(), q = b.getBoundingClientRect();
    const ix = Math.max(0, Math.min(p.right, q.right) - Math.max(p.left, q.left));
    const iy = Math.max(0, Math.min(p.bottom, q.bottom) - Math.max(p.top, q.top));
    if (ix * iy > 0.25 * Math.min(p.width * p.height, q.width * q.height)) add('warning', 'sobreposicao', a, `sobrepõe ${sel(b)}`);
  }
  for (const img of document.images) {
    if (!vis(img)) continue;
    if (img.complete && img.naturalWidth === 0) add('blocking', 'imagem-quebrada', img, img.src.slice(0, 80));
    if (!img.hasAttribute('alt')) add('blocking', 'imagem-sem-alt', img, img.src.slice(0, 80));
  }
  // heurísticas de acabamento (avisos): padrões que denunciam interface genérica
  const ff = getComputedStyle(document.body).fontFamily.toLowerCase().split(',')[0].trim().replace(/["']/g, '');
  if (['system-ui', '-apple-system', 'arial', 'helvetica', 'sans-serif', 'serif', 'times new roman', 'roboto', 'inter'].includes(ff))
    add('warning', 'tipografia-padrao', null, `fonte do corpo é "${ff}": escolha deliberada de tipografia ausente`);
  const emojiRe = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
  for (const el of inter) if (emojiRe.test(el.innerText || '')) { add('warning', 'emoji-como-icone', el, 'use ícone SVG com rótulo'); }
  for (const el of seenText) { const s = getComputedStyle(el);
    if (s.textTransform === 'uppercase' && parseFloat(s.fontSize) < 14 && (el.innerText || '').trim().length > 3) add('warning', 'rotulo-caixa-alta', el, 'rótulo em caixa alta pequena (padrão genérico)'); }
  const H = document.scrollingElement.scrollHeight, VH = window.innerHeight;
  if (isMobile && H > 5 * VH) add('warning', 'pagina-longa', null, `página com ${(H / VH).toFixed(1)} telas no celular: falta hierarquia/navegação?`);
  return {issues: out, height: H, width: sw};
}
"""


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    handler = functools.partial(_QuietHandler, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def add_routes(page, routes, simulated=None):
    """Simula a rede: resposta fixa (status/json/body) ou `"hold": true` para segurar a
    requisição sem responder (estado de carregamento)."""
    for rt in routes or []:
        if rt.get("hold"):
            page.route(rt["match"], lambda route, request=None: None)
            continue

        def make_handler(rt):
            def handler(route, request=None):
                if simulated is not None:
                    simulated.add(route.request.url)
                headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
                if route.request.method == "OPTIONS":
                    return route.fulfill(status=204, headers=headers)
                body = json.dumps(rt["json"]) if "json" in rt else rt.get("body", "")
                ctype = "application/json" if "json" in rt else rt.get("content_type", "text/plain")
                route.fulfill(status=rt.get("status", 200), headers={**headers, "Content-Type": ctype}, body=body)
            return handler
        page.route(rt["match"], make_handler(rt))


def run_step(page, step, base_dir):
    if "click" in step:
        page.click(step["click"], timeout=10000)
    elif "fill" in step:
        page.fill(step["fill"][0], step["fill"][1], timeout=10000)
    elif "set_files" in step:
        page.set_input_files(step["set_files"][0], str(base_dir / step["set_files"][1]), timeout=10000)
    elif "wait_for" in step:
        page.wait_for_selector(step["wait_for"], timeout=15000)
    elif "wait_ms" in step:
        page.wait_for_timeout(step["wait_ms"])
    elif "press" in step:
        page.press(step["press"][0], step["press"][1])
    elif "eval" in step:
        page.evaluate(step["eval"])


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "pagina"


def run(public, out, flows_file=None, commit=""):
    from playwright.sync_api import sync_playwright

    public, out = Path(public).resolve(), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = {"flows": [{"name": "inicio", "path": "/", "steps": []}]}
    base_dir = public
    if flows_file and Path(flows_file).exists():
        cfg = json.loads(Path(flows_file).read_text())
        base_dir = Path(flows_file).resolve().parent
    srv, base = serve(public)
    results = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                browser = p.chromium.launch(channel="chrome")
            for flow in cfg["flows"]:
                for vp_name, vp in VIEWPORTS.items():
                    ctx = browser.new_context(viewport=vp, device_scale_factor=1, locale="pt-BR",
                                              is_mobile=vp_name == "mobile", has_touch=vp_name == "mobile")
                    page = ctx.new_page()
                    console = []
                    page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
                    page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
                    failed = []
                    page.on("response", lambda r: failed.append(f"HTTP {r.status} {r.url}")
                            if r.status >= 400 and not r.url.endswith("/favicon.ico") else None)
                    simulated = set()  # respostas simuladas de propósito (ex.: 404 para "sem dados")
                    add_routes(page, cfg.get("routes"), simulated)
                    add_routes(page, flow.get("routes"), simulated)
                    name = f"{slug(flow['name'])}-{vp_name}"
                    rec = {"flow": flow["name"], "viewport": vp_name, "screenshot": f"{name}.png", "issues": []}
                    try:
                        page.goto(base + flow.get("path", "/"), wait_until="load")
                        page.wait_for_timeout(300)
                        for step in flow.get("steps", []):
                            run_step(page, step, base_dir)
                        page.wait_for_timeout(250)
                        page.screenshot(path=str(out / rec["screenshot"]), full_page=True)
                        res = page.evaluate(CHECK_JS, vp_name == "mobile")
                        rec["issues"] = res["issues"]
                        rec["page_height"] = res["height"]
                    except Exception as e:  # fluxo quebrado é bloqueante
                        rec["issues"].append({"severity": "blocking", "rule": "fluxo-falhou", "selector": None,
                                              "text": "", "detail": str(e).splitlines()[0][:200]})
                        try:
                            page.screenshot(path=str(out / rec["screenshot"]), full_page=True)
                        except Exception:
                            pass
                    # "Failed to load resource" do console não diz a URL: usamos as respostas HTTP.
                    for msg in console:
                        if not msg.startswith("Failed to load resource"):
                            rec["issues"].append({"severity": "blocking", "rule": "erro-console", "selector": None,
                                                  "text": "", "detail": msg[:200]})
                    for msg in failed:
                        url = msg.split(" ", 2)[2]
                        if url not in simulated:
                            rec["issues"].append({"severity": "blocking", "rule": "recurso-falhou", "selector": None,
                                                  "text": "", "detail": msg[:200]})
                    results.append(rec)
                    ctx.close()
            browser.close()
    finally:
        srv.shutdown()

    # agrupa repetições (mesma regra + seletor) para o relatório ficar legível
    for r in results:
        seen, uniq = {}, []
        for i in r["issues"]:
            k = (i["rule"], i["selector"], i["detail"] if i["selector"] is None else "")
            if k in seen:
                seen[k]["count"] = seen[k].get("count", 1) + 1
            else:
                seen[k] = i
                uniq.append(i)
        r["issues"] = uniq
    blocking = sum(1 for r in results for i in r["issues"] if i["severity"] == "blocking")
    warnings = sum(1 for r in results for i in r["issues"] if i["severity"] == "warning")
    report = {"commit": commit, "blocking": blocking, "warnings": warnings, "results": results}
    (out / "visual-qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))

    lines = [f"# QA visual automatizado", "",
             f"Commit: `{commit or '-'}` · Bloqueantes: **{blocking}** · Avisos: **{warnings}**", "",
             "| Fluxo | Tela | Bloq. | Avisos | Print |", "|---|---|---|---|---|"]
    for r in results:
        b = sum(1 for i in r["issues"] if i["severity"] == "blocking")
        w = len(r["issues"]) - b
        lines.append(f"| {r['flow']} | {r['viewport']} | {b} | {w} | `{r['screenshot']}` |")
    for r in results:
        if r["issues"]:
            lines += ["", f"## {r['flow']} · {r['viewport']}"]
            for i in r["issues"]:
                cnt = f" (×{i['count']})" if i.get("count") else ""
                where = f"`{i['selector']}`" if i["selector"] else ""
                txt = f" “{i['text']}”" if i.get("text") else ""
                lines.append(f"- {'⛔' if i['severity'] == 'blocking' else '⚠️'} **{i['rule']}**{cnt} {where}{txt}: {i['detail']}")
    lines += ["", "Os checks medem problemas mensuráveis. Hierarquia, composição e identidade são avaliadas "
              "na inspeção dos prints (design-review.md)."]
    (out / "visual-qa.md").write_text("\n".join(lines) + "\n")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("public")
    ap.add_argument("out")
    ap.add_argument("--flows")
    ap.add_argument("--commit", default="")
    a = ap.parse_args()
    rep = run(a.public, a.out, a.flows, a.commit)
    print(f"QA visual: {rep['blocking']} bloqueante(s), {rep['warnings']} aviso(s) → {a.out}/visual-qa.md")
    sys.exit(1 if rep["blocking"] else 0)


if __name__ == "__main__":
    main()
