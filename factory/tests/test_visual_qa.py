"""QA visual: detecta problemas reais e não acusa página boa."""
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
FX = Path(__file__).parent / "fixtures/visual"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import visual_qa  # noqa: E402


def rules(rep):
    return {i["rule"] for r in rep["results"] for i in r["issues"] if i["severity"] == "blocking"}


def test_pagina_boa_passa(tmp_path):
    rep = visual_qa.run(FX / "good", tmp_path)
    assert rep["blocking"] == 0, [(r["viewport"], i) for r in rep["results"] for i in r["issues"]]
    assert (tmp_path / "inicio-mobile.png").exists() and (tmp_path / "inicio-desktop.png").exists()
    assert json.loads((tmp_path / "visual-qa.json").read_text())["blocking"] == 0


def test_pagina_ruim_e_barrada(tmp_path):
    rep = visual_qa.run(FX / "bad", tmp_path)
    got = rules(rep)
    for r in ("sem-meta-viewport", "rolagem-horizontal", "texto-pequeno", "contraste", "recurso-falhou",
              "sem-nome-acessivel", "imagem-quebrada", "imagem-sem-alt", "erro-console", "sai-da-tela"):
        assert r in got, (r, got)


def test_fluxos_e_fluxo_quebrado(tmp_path):
    rep = visual_qa.run(FX / "good", tmp_path, FX / "good/flows.json", commit="abc")
    by = {(r["flow"], r["viewport"]): r for r in rep["results"]}
    assert not by[("resultado", "mobile")]["issues"]
    assert any(i["rule"] == "fluxo-falhou" for i in by[("quebrado", "desktop")]["issues"])
    assert rep["commit"] == "abc" and "Bloqueantes" in (tmp_path / "visual-qa.md").read_text()


def test_404_simulado_nao_conta_como_falha(tmp_path):
    flows = tmp_path / "flows.json"
    flows.write_text(json.dumps({"flows": [{"name": "vazio", "path": "/", "routes": [{"match": "**/dados.json", "status": 404, "body": ""}],
                                            "steps": [{"eval": "void fetch('dados.json')"}, {"wait_ms": 300}]}]}))
    import shutil
    shutil.copy(FX / "good/index.html", tmp_path / "index.html")
    rep = visual_qa.run(tmp_path, tmp_path / "out", flows)
    assert rep["blocking"] == 0, [(r["viewport"], i) for r in rep["results"] for i in r["issues"]]


def test_rota_simulada_entrega_json_e_hold_segura(tmp_path):
    (tmp_path / "index.html").write_text("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>t</title></head>
<body style="font:17px Georgia,serif;color:#111"><p id="s">carregando</p><button id="b">Buscar</button>
<script>document.getElementById('b').onclick=()=>fetch('https://api.x/dados').then(r=>r.json())
.then(d=>document.getElementById('s').textContent=d.msg)</script></body></html>""")
    flows = tmp_path / "flows.json"
    flows.write_text(json.dumps({"flows": [
        {"name": "ok", "path": "/", "routes": [{"match": "https://api.x/**", "json": {"msg": "pronto"}}],
         "steps": [{"click": "#b"}, {"wait_for": "text=pronto"}]},
        {"name": "carregando", "path": "/", "routes": [{"match": "https://api.x/**", "hold": True}],
         "steps": [{"click": "#b"}, {"wait_ms": 300}]}]}))
    rep = visual_qa.run(tmp_path, tmp_path / "out", flows)
    assert not any(i["rule"] == "fluxo-falhou" for r in rep["results"] for i in r["issues"]), rep


def test_espera_animacao_de_entrada(tmp_path):
    """Regressão: cartão com animação de entrada não pode sair invisível no print."""
    (tmp_path / "index.html").write_text("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>t</title>
<style>body{font:17px Georgia,serif;color:#111}.c{animation:r 900ms both}@keyframes r{from{opacity:0}to{opacity:1}}</style></head>
<body><p class="c" id="c">aparece</p></body></html>""")
    from playwright.sync_api import sync_playwright
    srv, base = visual_qa.serve(tmp_path)
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception:
                b = p.chromium.launch(channel="chrome")
            pg = b.new_page()
            pg.goto(base + "/")
            visual_qa.settle(pg)
            assert pg.evaluate("getComputedStyle(document.getElementById('c')).opacity") == "1"
            b.close()
    finally:
        srv.shutdown()


def test_barra_fixa_sem_folga_e_barrada(tmp_path):
    base = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>t</title>
<style>body{margin:0;font:17px Georgia,serif;color:#111;PAD}nav{position:fixed;bottom:0;left:0;right:0;height:70px;background:#eee}
p{height:1200px;margin:0}</style></head><body><p>conteúdo</p><button>Último</button><nav><a href="#">Início</a></nav></body></html>"""
    for pad, bad in (("", True), ("padding-bottom:90px", False)):
        d = tmp_path / ("ruim" if bad else "boa")
        d.mkdir()
        (d / "index.html").write_text(base.replace("PAD", pad))
        rep = visual_qa.run(d, d / "out")
        assert ("coberto-por-barra-fixa" in rules(rep)) is bad, rep
