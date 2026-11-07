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


# --- portão de design (Design Capability v1) -------------------------------

BRIEF = "## Brief\nx\n## Direção\ny\n## UX\nz\n"
REVIEW = "## Problemas\na\n## Correções\nb\n## Revalidação\nc\n"
QA_OK = {"blocking": 0, "results": []}
QA_BAD = {"blocking": 2, "results": [{"issues": [{"severity": "blocking", "rule": "contraste"},
                                                  {"severity": "blocking", "rule": "rolagem-horizontal"}]}]}


def gate(env, files, qa=QA_OK):
    calls = []

    def run_qa():
        calls.append(1)
        return qa
    probs = env.v.design_gate("a", 5, lambda p: files.get(p.replace("projects/a/", "")), run_qa)
    return probs, calls


def test_portao_completo_passa(env):
    probs, calls = gate(env, {"design/brief.md": BRIEF, "design/flows.json": "{}", "evidence/m5/design-review.md": REVIEW})
    assert probs == [] and calls == [1]


def test_portao_sem_artefatos_nao_roda_qa(env):
    probs, calls = gate(env, {})
    assert len(probs) == 3 and calls == []


def test_portao_secoes_faltando(env):
    probs, _ = gate(env, {"design/brief.md": "## Brief", "design/flows.json": "{}", "evidence/m5/design-review.md": "## Problemas"})
    assert any("Direção" in p for p in probs) and any("Revalidação" in p for p in probs)


def test_portao_qa_com_bloqueantes_falha(env):
    probs, _ = gate(env, {"design/brief.md": BRIEF, "design/flows.json": "{}", "evidence/m5/design-review.md": REVIEW}, QA_BAD)
    assert probs and "contraste" in probs[0] and "rolagem-horizontal" in probs[0]


def test_flows_invalido(env):
    probs, _ = gate(env, {"design/brief.md": BRIEF, "design/flows.json": "{x", "evidence/m5/design-review.md": REVIEW})
    assert any("inválido" in p for p in probs)


def test_skills_lidas_do_log(env, tmp_path):
    log = tmp_path / "agent.jsonl"
    log.write_text("\n".join([
        "lixo de npm",
        json.dumps({"type": "system", "subtype": "init", "skills": ["fabrica-design", "frontend-design", "ui-ux-pro-max"]}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "fabrica-design"}}]}}),
    ]))
    got = env.v.agent_skills(log)
    assert got["skills_used"] == ["fabrica-design"] and "ui-ux-pro-max" in got["skills_available"]
    assert env.v.agent_skills(tmp_path / "nao-existe") == {}


def test_skills_vendorizadas_intactas(env):
    """Regressão: as Skills externas são exatamente as auditadas (procedência em factory/design/vendor.json)."""
    import hashlib
    vendor = json.loads((REPO_ROOT / "factory/design/vendor.json").read_text())
    for name, meta in vendor.items():
        d = REPO_ROOT / ".claude/skills" / name
        for rel, sha in meta["files"].items():
            assert hashlib.sha256((d / rel).read_bytes()).hexdigest() == sha, f"{name}/{rel} mudou"


def test_fabrica_design_referencia_o_que_existe(env):
    skill = (REPO_ROOT / ".claude/skills/fabrica-design/SKILL.md").read_text()
    for path in ("factory/scripts/visual_qa.py", "factory/templates/design-brief.md", "factory/templates/design-review.md",
                 "factory/design/foundation.css", "factory/design/tokens.template.css"):
        assert path in skill and (REPO_ROOT / path).exists(), path


def test_portao_nao_retroage(env):
    import json as _j
    cfg = _j.loads((env.root / "factory/config.json").read_text())
    cfg["design_gate_since"] = "2026-11-07T03:30:00Z"
    (env.root / "factory/config.json").write_text(_j.dumps(cfg))
    import importlib
    importlib.reload(env.c)
    importlib.reload(env.v)
    assert env.v.gate_applies("2026-11-06T22:46:44+00:00") is False
    assert env.v.gate_applies("2026-11-07T05:00:00+00:00") is True
    assert env.v.gate_applies("") is True
