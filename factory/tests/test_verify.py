"""Verificação do resultado: verde só quando o trabalho foi registrado de verdade."""
import json

import pytest

from conftest import REPO_ROOT


def st(env, status="awaiting_plan_approval", run_id="99", owner="rafael", **kw):
    s = {"slug": "a", "title": "A", "issue": 1, "status": status, "milestones": [],
         "next_action": {"owner": owner, "text": "fazer x"},
         "last_event": {"run_id": run_id, "at": "2026-11-06T10:00:00Z", "summary": "plano postado"}}
    s.update(kw)
    return s


def ev(env, states, agent="success", slug="a", expect="", prev="discovery", inbox=""):
    return env.v.evaluate(agent, slug, expect, prev, "99", inbox, states)


def test_agente_falhou(env):
    assert ev(env, [st(env)], agent="failure")[0] == "failed"


def test_sem_registro_desta_execucao_falha(env):
    o, why, _ = ev(env, [st(env, run_id="12")])
    assert o == "failed" and "last_event" in why


def test_transicao_invalida_falha(env):
    o, why, _ = ev(env, [st(env, status="delivered")], prev="discovery")
    assert o == "failed" and "transição" in why


def test_next_action_vazio_falha(env):
    s = st(env); s["next_action"] = {"owner": "rafael", "text": ""}
    assert ev(env, [s])[0] == "failed"


def test_aguardando_rafael(env):
    assert ev(env, [st(env)])[0] == "waiting"


def test_concluido_com_agente(env):
    assert ev(env, [st(env, status="executing", owner="agente")], prev="awaiting_plan_approval")[0] == "done"


def test_bloqueado(env):
    assert ev(env, [st(env, status="blocked")])[0] == "blocked"


def test_ideia_nao_virou_projeto(env):
    o, why, _ = ev(env, [], slug="", expect="7", prev="")
    assert o == "failed" and "#7" in why


def test_ideia_virou_projeto(env):
    s = st(env, status="discovery"); s["issue"] = 7
    assert ev(env, [s], slug="", expect="7", prev="")[0] == "waiting"


def test_instrucao_nao_apagada_falha(env):
    (env.root / "factory/inbox").mkdir()
    (env.root / "factory/inbox/001.md").write_text("x")
    assert ev(env, [st(env)], inbox="factory/inbox/001.md")[0] == "failed"


@pytest.mark.parametrize("old,new,ok", [
    (None, "discovery", True), ("discovery", "awaiting_plan_approval", True),
    ("discovery", "delivered", False), ("awaiting_milestone_approval", "executing", True),
    ("delivered", "awaiting_milestone_approval", True), ("closed", "executing", False),
])
def test_transicoes(env, old, new, ok):
    assert env.c.valid_transition(old, new) is ok


def test_estados_reais_do_repo_sao_validos(env):
    """Regressão: todo state.json versionado respeita o schema atual."""
    import common
    for p in sorted((REPO_ROOT / "projects").glob("*/state.json")):
        s = json.loads(p.read_text())
        errs = [e for e in common.validate_state(s) if not (s["status"] == "closed" and e == "next_action vazio")]
        assert errs == [], f"{p}: {errs}"
