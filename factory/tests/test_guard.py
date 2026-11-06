"""Testes da guarda da fábrica: cada evento real que importa tem um caso aqui."""
import importlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPO, OWNER = "rpten/personal-ai-os", "rpten"


@pytest.fixture
def env(tmp_path, monkeypatch):
    (tmp_path / "factory").mkdir()
    cfg = json.loads((SCRIPTS.parent / "config.json").read_text())
    (tmp_path / "factory/config.json").write_text(json.dumps(cfg))
    (tmp_path / "projects").mkdir()
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    monkeypatch.setenv("FACTORY_DRY", "1")
    monkeypatch.delenv("FACTORY_FAKE_ISSUES", raising=False)
    sys.path.insert(0, str(SCRIPTS))
    import guard
    importlib.reload(guard)

    class E:
        g = guard
        root = tmp_path

        def project(self, slug, issue, status="discovery", prs=()):
            d = tmp_path / "projects" / slug
            d.mkdir()
            (d / "state.json").write_text(json.dumps({
                "slug": slug, "title": slug, "issue": issue, "status": status,
                "milestones": [{"n": i + 1, "title": "m", "status": "pending", "pr": p} for i, p in enumerate(prs)]}))

        def issues(self, items):
            p = tmp_path / "issues.json"
            p.write_text(json.dumps(items))
            monkeypatch.setenv("FACTORY_FAKE_ISSUES", str(p))

        def decide(self, name, event):
            event.setdefault("sender", {"login": OWNER})
            return guard.decide(name, event, REPO, OWNER, guard.load_states())

    return E()


def issue_ev(n, labels=(), action="opened"):
    return {"action": action, "issue": {"number": n, "title": f"Ideia {n}", "body": "texto",
                                        "labels": [{"name": l} for l in labels]}}


# --- entrada de ideias ---------------------------------------------------

def test_issue_sem_label_vira_ideia(env):
    detail, slug, expect = env.decide("issues", issue_ev(1))
    assert expect == 1 and slug == "" and "#1" in detail


def test_issue_do_formulario_vira_ideia(env):
    assert env.decide("issues", issue_ev(1, ["ideia"]))[2] == 1


def test_issue_de_outra_pessoa_ignorada(env):
    ev = issue_ev(1)
    ev["sender"] = {"login": "estranho"}
    with pytest.raises(env.g.Skip):
        env.decide("issues", ev)


def test_wip_cheio_enfileira_com_comentario(env):
    env.project("a", 1)
    with pytest.raises(env.g.Skip):
        env.decide("issues", issue_ev(2))
    cmds = [" ".join(c) for c in env.g.GH_LOG]
    assert any("--add-label fila" in c for c in cmds)
    assert any(c.startswith("issue comment 2") for c in cmds)


def test_issue_fabrica_roda_sem_expectativa_de_projeto(env):
    env.project("a", 1)  # WIP cheio não bloqueia melhoria da fábrica
    assert env.decide("issues", issue_ev(2, ["fabrica"]))[2] is None


def test_comentario_em_ideia_nao_iniciada_inicia(env):
    ev = issue_ev(1, action="created")
    ev["comment"] = {"body": "e aí?"}
    assert env.decide("issue_comment", ev)[2] == 1


# --- reconciliação -------------------------------------------------------

def test_push_inicia_ideia_esquecida(env):
    env.issues([{"number": 1, "title": "x", "body": "", "labels": []}])
    detail, slug, expect = env.decide("push", {})
    assert expect == 1


def test_reconcilia_mais_antiga_primeiro(env):
    env.issues([{"number": 5, "labels": []}, {"number": 3, "labels": [{"name": "fila"}]}])
    assert env.decide("schedule", {})[2] == 3


def test_reconcilia_ignora_ja_vinculadas_e_fabrica(env):
    env.project("a", 1, status="delivered")
    env.issues([{"number": 1, "labels": []}, {"number": 2, "labels": [{"name": "fabrica"}]}])
    with pytest.raises(env.g.Skip):
        env.decide("push", {})


def test_reconcilia_com_wip_cheio_enfileira(env):
    env.project("a", 1)
    env.issues([{"number": 1, "labels": []}, {"number": 2, "labels": []}])
    with pytest.raises(env.g.Skip):
        env.decide("schedule", {})
    assert any("--add-label" in " ".join(c) and c[2] == "2" for c in env.g.GH_LOG)


def test_reconcilia_nao_recomenta_quem_ja_esta_na_fila(env):
    env.project("a", 1)
    env.issues([{"number": 2, "labels": [{"name": "fila"}]}])
    with pytest.raises(env.g.Skip):
        env.decide("schedule", {})
    assert not any(c[:2] == ["issue", "comment"] for c in env.g.GH_LOG)


def test_dispatch_com_instrucao(env):
    assert env.decide("workflow_dispatch", {"inputs": {"instrucao": "faça X"}})[0] == "faça X"


# --- respostas e aprovações ---------------------------------------------

BLOCK = "<!-- factory:question id=q1 -->\n**Pergunta 1**\n- [{a}] A) sim\n- [{b}] B) não\n"


def edit_ev(n, before, after):
    return {"action": "edited", "issue": {"number": n, "labels": []},
            "comment": {"body": after}, "changes": {"body": {"from": before}}}


def test_marcar_caixa_dispara(env):
    env.project("a", 1)
    detail, slug, _ = env.decide("issue_comment", edit_ev(1, BLOCK.format(a=" ", b=" "), BLOCK.format(a=" ", b="x")))
    assert slug == "a" and detail.split("\n")[0].endswith(": B) não")


def test_edicao_sem_nova_marcacao_ignorada(env):
    env.project("a", 1)
    same = BLOCK.format(a="x", b=" ")
    with pytest.raises(env.g.Skip):
        env.decide("issue_comment", edit_ev(1, same, same))


def test_edicao_de_comentario_comum_ignorada(env):
    env.project("a", 1)
    with pytest.raises(env.g.Skip):
        env.decide("issue_comment", edit_ev(1, "- [ ] x", "- [x] x"))


def test_merge_de_pr_do_marco(env):
    env.project("a", 1, status="awaiting_milestone_approval", prs=[7])
    ev = {"action": "closed", "pull_request": {"number": 7, "merged": True, "head": {"ref": "factory/a/m1"}}}
    assert env.decide("pull_request", ev)[1] == "a"


def test_pr_fechado_sem_merge_ignorado(env):
    ev = {"action": "closed", "pull_request": {"number": 7, "merged": False, "head": {"ref": "factory/a/m1"}}}
    with pytest.raises(env.g.Skip):
        env.decide("pull_request", ev)


def test_label_aprovado(env):
    env.project("a", 1, status="awaiting_plan_approval")
    ev = issue_ev(1, action="labeled")
    ev["label"] = {"name": "aprovado"}
    assert env.decide("issues", ev)[1] == "a"


# --- caixa de entrada -----------------------------------------------------

def test_inbox_tem_prioridade_e_traz_slug(env):
    d = env.root / "factory/inbox"; d.mkdir()
    (d / "001-x.md").write_text("slug: taste-memory\nFaça Y")
    env.issues([{"number": 9, "labels": []}])
    detail, slug, expect = env.decide("push", {})
    assert slug == "taste-memory" and "Faça Y" in detail and "factory/inbox/001-x.md" in detail and expect is None


def test_inbox_vazia_segue_reconciliacao(env):
    (env.root / "factory/inbox").mkdir()
    env.issues([{"number": 9, "labels": []}])
    assert env.decide("push", {})[2] == 9
