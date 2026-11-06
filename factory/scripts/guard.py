#!/usr/bin/env python3
"""Guarda da fábrica: decide, sem LLM, se o agente deve rodar e para quê.

Regras:
- Só ações do dono do repositório acordam o agente.
- Toda issue aberta pelo dono é uma ideia (sem label obrigatório), exceto
  as marcadas `fabrica` (melhorias da própria fábrica).
- Limite de WIP: ideias acima do limite ganham `fila` e um comentário.
- Reconciliação (push em main, agendamento horário, execução manual):
  encontra ideias abertas que ainda não viraram projeto e inicia a mais
  antiga se houver vaga. Nenhuma ideia fica esquecida.
- Nada é ignorado em silêncio quando envolve uma ideia sua: ou roda,
  ou entra na fila com comentário.

Saídas em $GITHUB_OUTPUT: run, slug, prompt, max_turns, expect_issue.
`expect_issue` = número da ideia que precisa ter virado projeto ao final;
o passo de verificação da workflow falha (vermelho) e avisa se não virou.

Testes: factory/tests/test_guard.py. Para simular sem rede:
FACTORY_DRY=1 (não chama gh) e FACTORY_FAKE_ISSUES=<json> (lista de issues).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("FACTORY_ROOT", Path(__file__).resolve().parents[2]))
CONFIG = json.loads((ROOT / "factory/config.json").read_text())
ACTIVE = {"discovery", "awaiting_plan_approval", "executing", "awaiting_milestone_approval", "blocked"}
LABELS = {
    "ideia": "0e8a16", "fila": "c5def5", "discovery": "fbca04", "aprovado": "0e8a16",
    "pausado": "d4c5f9", "retomar": "bfdadc", "encerrado": "000000", "fabrica": "5319e7",
}
ACTION_LABELS = {"aprovado", "pausado", "retomar", "encerrado"}
CHECK_RE = re.compile(r"^\s*[-*] \[([ xX])\] (.+)$", re.M)
DRY = bool(os.environ.get("FACTORY_DRY"))
GH_LOG = []  # comandos gh emitidos (inspecionado pelos testes)


class Skip(Exception):
    pass


def gh(*args):
    GH_LOG.append(list(args))
    if DRY:
        return ""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"gh {' '.join(args)} falhou: {r.stderr.strip()}", file=sys.stderr)
    return r.stdout


def open_issues(repo, owner):
    """Issues abertas do dono (exclui PRs), da mais antiga para a mais nova."""
    fake = os.environ.get("FACTORY_FAKE_ISSUES")
    if fake:
        data = json.loads(Path(fake).read_text())
    else:
        out = gh("issue", "list", "-R", repo, "--state", "open", "--author", owner, "--limit", "100",
                 "--json", "number,title,body,labels,createdAt")
        data = json.loads(out or "[]")
    for i in data:
        i["labels"] = {l["name"] if isinstance(l, dict) else l for l in i.get("labels", [])}
    return sorted(data, key=lambda i: i["number"])


def load_states():
    states = []
    for p in sorted((ROOT / "projects").glob("*/state.json")):
        try:
            states.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            print(f"state inválido: {p}", file=sys.stderr)
    return states


def active_projects(states):
    return [s for s in states if s.get("status") in ACTIVE]


def find_slug(states, number=None, branch=None):
    if branch:
        m = re.match(r"factory/([a-z0-9-]+)/m\d+", branch)
        if m:
            return m.group(1)
    for s in states:
        if number and s.get("issue") == number:
            return s["slug"]
        if number and any(ms.get("pr") == number for ms in s.get("milestones", [])):
            return s["slug"]
    return ""


def newly_checked(before, after):
    """Opções que passaram de [ ] para [x] numa edição de comentário."""
    old = {t.strip() for c, t in CHECK_RE.findall(before or "") if c.lower() == "x"}
    return [t.strip() for c, t in CHECK_RE.findall(after or "") if c.lower() == "x" and t.strip() not in old]


def enqueue(repo, number, states, already_queued=False):
    if already_queued:
        return
    gh("issue", "edit", str(number), "--add-label", "ideia", "--add-label", "fila", "-R", repo)
    names = ", ".join(s["title"] for s in active_projects(states)) or "-"
    gh("issue", "comment", str(number), "-R", repo, "--body",
       f"📥 Ideia recebida e na fila. Limite de {CONFIG['wip_limit']} projeto(s) ativo(s) atingido ({names}). "
       "Começa sozinha quando houver vaga.")


def start_idea(repo, issue):
    gh("issue", "edit", str(issue["number"]), "--add-label", "ideia", "--remove-label", "fila", "-R", repo)
    return (f"Nova ideia na issue #{issue['number']}: {issue.get('title')}\n\n{issue.get('body') or ''}\n\n"
            "Inicie o discovery desta ideia conforme o protocolo.")


def reconcile(repo, owner, states):
    """Inicia a ideia pendente mais antiga, se houver vaga. Retorna (detalhe, issue) ou levanta Skip."""
    linked = {s.get("issue") for s in states}
    pending = [i for i in open_issues(repo, owner) if i["number"] not in linked and "fabrica" not in i["labels"]]
    if not pending:
        raise Skip("nenhuma ideia pendente")
    if len(active_projects(states)) >= CONFIG["wip_limit"]:
        for i in pending:
            enqueue(repo, i["number"], states, already_queued="fila" in i["labels"])
        raise Skip(f"{len(pending)} ideia(s) pendente(s), WIP cheio")
    first = pending[0]
    return start_idea(repo, first), first["number"]


def inbox_item():
    """Instrução pendente em factory/inbox/*.md (enviada por Rafael ou em nome dele)."""
    files = sorted((ROOT / "factory/inbox").glob("*.md"))
    if not files:
        return None
    f = files[0]
    text = f.read_text()
    m = re.search(r"^slug:\s*([a-z0-9-]+)\s*$", text, re.M)
    return f.relative_to(ROOT).as_posix(), text, (m.group(1) if m else "")


def decide(event_name, event, repo, owner, states):
    """Retorna (detail, slug, expect_issue). Levanta Skip para não rodar."""
    sender = event.get("sender", {}).get("login", "")
    automatic = event_name in ("push", "schedule", "workflow_dispatch")
    if CONFIG.get("owner_only", True) and not automatic and sender != owner:
        raise Skip(f"ator {sender} não é o dono")

    action = event.get("action", "")
    issue = event.get("issue") or {}
    pr = event.get("pull_request") or {}
    number = issue.get("number") or pr.get("number")
    branch = pr.get("head", {}).get("ref")
    if issue.get("pull_request") and not branch:
        branch = gh("pr", "view", str(number), "-R", repo, "--json", "headRefName", "-q", ".headRefName").strip() or None
    slug = find_slug(states, number, branch)
    state = next((s for s in states if s["slug"] == slug), None)

    if automatic:
        instr = (event.get("inputs") or {}).get("instrucao")
        if instr:
            return instr, "", None
        item = inbox_item()
        if item:
            path, text, slug = item
            return (f"Instrução de Rafael (caixa de entrada `{path}`), trate como um comentário dele:\n\n{text}\n\n"
                    f"Ao terminar, apague `{path}` (git rm) no mesmo commit do state.json."), slug, None
        detail, n = reconcile(repo, owner, states)
        return detail, "", n

    if event_name == "issues" and action == "opened":
        labels = {l["name"] for l in issue.get("labels", [])}
        if "fabrica" in labels:
            return f"Melhoria da fábrica, issue #{number}: {issue.get('title')}\n\n{issue.get('body') or ''}", "", None
        if len(active_projects(states)) >= CONFIG["wip_limit"]:
            enqueue(repo, number, states)
            raise Skip("WIP cheio, ideia enfileirada")
        return start_idea(repo, {**issue, "labels": labels}), "", number

    if event_name == "issues" and action == "labeled":
        label = event.get("label", {}).get("name", "")
        if label not in ACTION_LABELS:
            raise Skip(f"label {label} sem ação")
        if not slug:
            raise Skip("label em issue sem projeto")
        if label == "retomar" and state and state.get("status") == "paused":
            if len(active_projects(states)) >= CONFIG["wip_limit"]:
                gh("issue", "edit", str(number), "--remove-label", "retomar", "--add-label", "fila", "-R", repo)
                raise Skip("WIP cheio, retomada enfileirada")
        return f"Rafael aplicou o label `{label}` na issue #{number}.", slug, None

    if event_name == "issue_comment" and action == "edited":
        body = event.get("comment", {}).get("body", "")
        before = event.get("changes", {}).get("body", {}).get("from", "")
        if "<!-- factory:" not in body:
            raise Skip("edição fora de bloco da fábrica")
        checked = newly_checked(before, body)
        if not checked:
            raise Skip("nenhuma opção nova marcada")
        if not slug:
            raise Skip("bloco marcado em item sem projeto")
        marker = re.search(r"<!-- factory:(\S+) ([^>]*)-->", body)
        return (f"Rafael marcou no bloco `{marker.group(1)} {marker.group(2).strip()}` (#{number}): "
                + "; ".join(checked) + f"\n\nTexto completo do bloco:\n{body}"), slug, None

    if event_name == "issue_comment" and action == "created":
        if not slug:
            # comentário numa ideia que ainda não virou projeto: inicia-a
            if not issue.get("pull_request") and "fabrica" not in {l["name"] for l in issue.get("labels", [])}:
                if len(active_projects(states)) >= CONFIG["wip_limit"]:
                    enqueue(repo, number, states, already_queued="fila" in {l["name"] for l in issue.get("labels", [])})
                    raise Skip("WIP cheio, ideia enfileirada")
                return start_idea(repo, issue) + f"\n\nComentário de Rafael:\n{event['comment']['body']}", "", number
            raise Skip("comentário em item sem projeto")
        return f"Rafael comentou em #{number}:\n\n{event['comment']['body']}", slug, None

    if event_name == "pull_request" and action == "closed":
        if not pr.get("merged"):
            raise Skip("PR fechado sem merge")
        if not slug:
            raise Skip("PR fora da fábrica")
        return f"Rafael mergeou o PR #{number} (branch {branch}) = marco aprovado.", slug, None

    if event_name == "pull_request_review":
        if not slug:
            raise Skip("review fora da fábrica")
        review = event.get("review", {})
        return f"Rafael revisou o PR #{number} ({review.get('state')}):\n\n{review.get('body') or ''}", slug, None

    raise Skip(f"evento {event_name}/{action} não tratado")


def build_prompt(repo, event_name, action, slug, detail, states):
    state = next((s for s in states if s["slug"] == slug), None)
    state_txt = json.dumps(state, ensure_ascii=False, indent=2) if state else "(projeto ainda não existe)"
    return f"""Você está operando a fábrica de projetos. Siga estritamente o CLAUDE.md da raiz do repositório.

Repositório: {repo}
Evento: {event_name}/{action}
Projeto (slug): {slug or '(novo)'}

O que aconteceu:
{detail}

Estado atual do projeto:
{state_txt}

Faça o que o protocolo manda para esse evento, comunique-se com Rafael pela issue/PR usando `gh`, e termine com o state.json atualizado e commitado em main."""


def write_output(**kw):
    lines = []
    for k, v in kw.items():
        v = "" if v is None else str(v)
        lines.append(f"{k}<<__EOF__\n{v}\n__EOF__" if "\n" in v else f"{k}={v}")
    text = "\n".join(lines) + "\n"
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(text)
    else:
        print(text)


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    for name, color in LABELS.items():
        gh("label", "create", name, "--color", color, "--force", "-R", repo)
    states = load_states()
    try:
        detail, slug, expect = decide(event_name, event, repo, owner, states)
    except Skip as e:
        print(f"skip: {e}")
        write_output(run="false", slug="", prompt="", max_turns=CONFIG["max_turns"], expect_issue="")
        return
    prompt = build_prompt(repo, event_name, event.get("action", ""), slug, detail, states)
    print(f"run: slug={slug or '(novo)'} expect_issue={expect or '-'}")
    write_output(run="true", slug=slug, prompt=prompt, max_turns=CONFIG["max_turns"], expect_issue=expect or "")


if __name__ == "__main__":
    main()
