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
    for r in ("sem-meta-viewport", "rolagem-horizontal", "texto-pequeno", "contraste",
              "sem-nome-acessivel", "imagem-quebrada", "imagem-sem-alt", "erro-console", "sai-da-tela"):
        assert r in got, (r, got)


def test_fluxos_e_fluxo_quebrado(tmp_path):
    rep = visual_qa.run(FX / "good", tmp_path, FX / "good/flows.json", commit="abc")
    by = {(r["flow"], r["viewport"]): r for r in rep["results"]}
    assert not by[("resultado", "mobile")]["issues"]
    assert any(i["rule"] == "fluxo-falhou" for i in by[("quebrado", "desktop")]["issues"])
    assert rep["commit"] == "abc" and "Bloqueantes" in (tmp_path / "visual-qa.md").read_text()
