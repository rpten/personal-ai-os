#!/usr/bin/env python3
"""Guarda da fábrica: decide se o evento do GitHub deve acordar o agente.

Responsabilidades (deterministas, sem LLM):
- só reagir a ações do dono do repositório;
- ignorar edições que não marcaram uma caixa de opção;
- aplicar o limite de WIP para novas ideias (label `fila`);
- localizar o projeto (slug) ligado à issue/PR;
- montar o prompt da execução.

Saídas em $GITHUB_OUTPUT: run=true|false, slug, prompt.
FACTORY_DRY=1 imprime comandos `gh` em vez de executá-los (testes).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "factory/config.json").read_text())
ACTIVE = {"discovery", "awaiting_plan_approval", "executing", "awaiting_milestone_approval", "blocked"}
LABELS = {
    "ideia": "0e8a16", "fila": "c5def5", "discovery": "fbca04", "aprovado": "0e8a16",
    "pausado": "d4c5f9", "retomar": "bfdadc", "encerrado": "000000", "fabrica": "5319e7",
}
ACTION_LABELS = {"aprovado", "pausado", "retomar", "encerrado"}
CHECK_RE = re.compile(r"^\s*[-*] \[([ xX])\] (.+)$", re.M)


def gh(*args):
    if os.environ.get("FACTORY_DRY"):
        print("DRY gh", " ".join(args), file=sys.stderr)
        return ""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"gh {' '.join(args)} falhou: {r.stderr.strip()}", file=sys.stderr)
    return r.stdout


def output(**kw):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = []
    for k, v in kw.items():
        v = str(v)
        if "\n" in v:
            lines.append(f"{k}<<__EOF__\n{v}\n__EOF__")
        else:
            lines.append(f"{k}={v}")
    text = "\n".join(lines) + "\n"
    if path:
        with open(path, "a") as f:
            f.write(text)
    else:
        print(text)


def skip(reason):
    print(f"skip: {reason}")
    output(run="false", slug="", prompt="")
    sys.exit(0)


def load_states():
    states = []
    for p in sorted((ROOT / "projects").glob("*/state.json")):
        try:
            states.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            print(f"state inválido: {p}", file=sys.stderr)
    return states


def find_slug(states, issue_number=None, branch=None):
    if branch:
        m = re.match(r"factory/([a-z0-9-]+)/m\d+", branch)
        if m:
            return m.group(1)
    for s in states:
        if issue_number and s.get("issue") == issue_number:
            return s["slug"]
        if issue_number and any(ms.get("pr") == issue_number for ms in s.get("milestones", [])):
            return s["slug"]
    return ""


def newly_checked(before, after):
    """Opções que passaram de [ ] para [x] numa edição de comentário."""
    old = {t.strip() for c, t in CHECK_RE.findall(before or "") if c.lower() == "x"}
    return [t.strip() for c, t in CHECK_RE.findall(after or "") if c.lower() == "x" and t.strip() not in old]


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    sender = event.get("sender", {}).get("login", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if CONFIG.get("owner_only", True) and sender != owner and event_name != "workflow_dispatch":
        skip(f"ator {sender} não é o dono")

    for name, color in LABELS.items():
        gh("label", "create", name, "--color", color, "--force", "-R", repo)

    states = load_states()
    action = event.get("action", "")
    issue = event.get("issue") or {}
    pr = event.get("pull_request") or {}
    number = issue.get("number") or pr.get("number")
    branch = pr.get("head", {}).get("ref")
    if issue.get("pull_request") and not branch:
        # comentário em PR: o nome do branch não vem no evento
        branch = gh("pr", "view", str(number), "-R", repo, "--json", "headRefName", "-q", ".headRefName").strip() or None
    slug = find_slug(states, number, branch)
    state = next((s for s in states if s["slug"] == slug), None)
    detail = ""

    if event_name == "issues" and action == "opened":
        labels = {l["name"] for l in issue.get("labels", [])}
        if "ideia" not in labels and "fabrica" not in labels:
            skip("issue sem label ideia/fabrica")
        if "ideia" in labels:
            active = [s for s in states if s.get("status") in ACTIVE]
            if len(active) >= CONFIG["wip_limit"]:
                gh("issue", "edit", str(number), "--add-label", "fila", "-R", repo)
                names = ", ".join(s["title"] for s in active)
                gh("issue", "comment", str(number), "-R", repo, "--body",
                   f"📥 Ideia na fila. Limite de {CONFIG['wip_limit']} projeto(s) ativo(s) atingido ({names}). "
                   "Começa automaticamente quando houver vaga.")
                skip("WIP cheio, ideia enfileirada")
        detail = f"Nova issue #{number}: {issue.get('title')}\n\n{issue.get('body') or ''}"

    elif event_name == "issues" and action == "labeled":
        label = event.get("label", {}).get("name", "")
        if label not in ACTION_LABELS:
            skip(f"label {label} sem ação")
        if not slug:
            skip("label em issue sem projeto")
        if label == "retomar" and state and state.get("status") == "paused":
            active = [s for s in states if s.get("status") in ACTIVE]
            if len(active) >= CONFIG["wip_limit"]:
                gh("issue", "edit", str(number), "--remove-label", "retomar", "--add-label", "fila", "-R", repo)
                skip("WIP cheio, retomada enfileirada")
        detail = f"Rafael aplicou o label `{label}` na issue #{number}."

    elif event_name == "issue_comment" and action == "edited":
        body = event.get("comment", {}).get("body", "")
        before = event.get("changes", {}).get("body", {}).get("from", "")
        if "<!-- factory:" not in body:
            skip("edição fora de bloco da fábrica")
        checked = newly_checked(before, body)
        if not checked:
            skip("nenhuma opção nova marcada")
        marker = re.search(r"<!-- factory:(\S+) ([^>]*)-->", body)
        detail = (f"Rafael marcou no bloco `{marker.group(1)} {marker.group(2).strip()}` (#{number}): "
                  + "; ".join(checked) + f"\n\nTexto completo do bloco:\n{body}")
        if not slug:
            skip("bloco marcado em item sem projeto")

    elif event_name == "issue_comment" and action == "created":
        if not slug:
            skip("comentário em item sem projeto")
        detail = f"Rafael comentou em #{number}:\n\n{event['comment']['body']}"

    elif event_name == "pull_request" and action == "closed":
        if not pr.get("merged"):
            skip("PR fechado sem merge")
        if not slug:
            skip("PR fora da fábrica")
        detail = f"Rafael mergeou o PR #{number} (branch {branch}) = marco aprovado."

    elif event_name == "pull_request_review":
        if not slug:
            skip("review fora da fábrica")
        review = event.get("review", {})
        detail = f"Rafael revisou o PR #{number} ({review.get('state')}):\n\n{review.get('body') or ''}"

    elif event_name == "workflow_dispatch":
        detail = (event.get("inputs") or {}).get("instrucao") or "Execução manual: verifique o estado de todos os projetos e avance o que estiver parado."

    else:
        skip(f"evento {event_name}/{action} não tratado")

    state_txt = json.dumps(state, ensure_ascii=False, indent=2) if state else "(projeto ainda não existe)"
    prompt = f"""Você está operando a fábrica de projetos. Siga estritamente o CLAUDE.md da raiz do repositório.

Repositório: {repo}
Evento: {event_name}/{action}
Projeto (slug): {slug or '(novo)'}

O que aconteceu:
{detail}

Estado atual do projeto:
{state_txt}

Faça o que o protocolo manda para esse evento, comunique-se com Rafael pela issue/PR usando `gh`, e termine com o state.json atualizado e commitado em main."""
    output(run="true", slug=slug, prompt=prompt)


if __name__ == "__main__":
    main()
