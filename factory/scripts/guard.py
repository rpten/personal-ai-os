#!/usr/bin/env python3
"""Guarda da fábrica: decide, sem LLM, se o agente roda, para quê, e registra o porquê.

Regras:
- Só ações do dono do repositório acordam o agente.
- Toda issue aberta pelo dono é uma ideia (sem label), exceto `fabrica`.
- Limite de WIP: ideias acima do limite ganham `fila` e um comentário.
- Idempotência: um evento já concluído (mesma chave no ledger) não roda de novo.
- Limite de falhas: após 3 falhas seguidas num projeto, a reconciliação
  automática para de tentar e avisa uma vez; uma ação de Rafael reabre.
- Reconciliação (push em main, agendamento horário, execução manual), em ordem:
  1. caixa de entrada (factory/inbox/*.md);
  2. ideias abertas que ainda não viraram projeto;
  3. projetos ativos com atividade de Rafael posterior ao último evento
     registrado (eventos perdidos, falhas anteriores).
- Todo evento de Rafael que não roda gera registro no ledger com o motivo, e
  um comentário quando a intenção dele não pôde ser atendida.

Saídas em $GITHUB_OUTPUT: run, slug, prompt, max_turns, expect_issue, key,
react_path, prev_status, issue.

Testes: factory/tests/. Simulação sem rede: FACTORY_DRY=1,
FACTORY_FAKE_ISSUES=<json lista de issues>, FACTORY_FAKE_ACTIVITY=<json {slug: iso}>.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import ACTIVE, CONFIG, ROOT, gh  # noqa: E402

LABELS = {
    "ideia": "0e8a16", "fila": "c5def5", "discovery": "fbca04", "aprovado": "0e8a16",
    "pausado": "d4c5f9", "retomar": "bfdadc", "encerrado": "000000", "fabrica": "5319e7",
}
ACTION_LABELS = {"aprovado", "pausado", "retomar", "encerrado"}
CHECK_RE = re.compile(r"^\s*[-*] \[([ xX])\] (.+)$", re.M)
AUTOMATIC = ("push", "schedule", "workflow_dispatch")
MAX_FAILS = 3


class Skip(Exception):
    def __init__(self, reason, outcome="ignored", notify=None, slug="", issue=None):
        super().__init__(reason)
        self.reason, self.outcome, self.notify, self.slug, self.issue = reason, outcome, notify, slug, issue


# --- leitura do GitHub (com simulação para testes) ---------------------------

def open_issues(repo, owner):
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


def project_activity(repo, state):
    """Momento (ISO) da atividade mais recente na issue do projeto e nos PRs dos marcos."""
    fake = os.environ.get("FACTORY_FAKE_ACTIVITY")
    if fake:
        return json.loads(Path(fake).read_text()).get(state["slug"])
    if common.DRY:
        return None
    times = []
    out = gh("api", f"repos/{repo}/issues/{state['issue']}/comments?per_page=100", "-q", "[.[].updated_at]")
    times += json.loads(out or "[]")
    for m in state.get("milestones", []):
        if m.get("pr"):
            out = gh("api", f"repos/{repo}/pulls/{m['pr']}", "-q", "[.merged_at, .closed_at] | map(select(. != null))")
            times += json.loads(out or "[]")
    return max(times) if times else None


# --- helpers -----------------------------------------------------------------

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
    old = {t.strip() for c, t in CHECK_RE.findall(before or "") if c.lower() == "x"}
    return [t.strip() for c, t in CHECK_RE.findall(after or "") if c.lower() == "x" and t.strip() not in old]


def event_key(event_name, event):
    """Chave estável do evento, para idempotência."""
    a = event.get("action", "")
    if event_name == "issues":
        extra = event.get("label", {}).get("name", "") if a == "labeled" else ""
        return f"issue-{event['issue']['number']}-{a}{('-' + extra) if extra else ''}-{event['issue'].get('updated_at', '')}"
    if event_name == "issue_comment":
        c = event.get("comment", {})
        if a == "edited":
            h = hashlib.sha1(c.get("body", "").encode()).hexdigest()[:10]
            return f"comment-{c.get('id')}-edited-{h}"
        return f"comment-{c.get('id')}-{a}"
    if event_name == "pull_request":
        return f"pr-{event['pull_request']['number']}-{a}"
    if event_name == "pull_request_review":
        return f"review-{event.get('review', {}).get('id')}"
    return ""


def react_target(event_name, event, repo):
    if event_name == "issue_comment":
        cid = event.get("comment", {}).get("id")
        return f"repos/{repo}/issues/comments/{cid}/reactions" if cid else ""
    n = (event.get("issue") or event.get("pull_request") or {}).get("number")
    return f"repos/{repo}/issues/{n}/reactions" if n else ""


def fails_in_row(ledger, slug):
    n = 0
    for r in reversed([r for r in ledger if r.get("slug") == slug and r.get("outcome") != "ignored"]):
        if r.get("outcome") == "failed":
            n += 1
        else:
            break
    return n


def enqueue(repo, number, states, already_queued=False):
    if already_queued:
        return
    gh("issue", "edit", str(number), "--add-label", "ideia", "--add-label", "fila", "-R", repo)
    names = ", ".join(s["title"] for s in active_projects(states)) or "-"
    gh("issue", "comment", str(number), "-R", repo, "--body",
       f"📥 Ideia recebida e na fila. Limite de {CONFIG['wip_limit']} projeto(s) ativo(s) atingido ({names}). "
       "Começa sozinha quando houver vaga.\n\n⏳ **Comigo:** iniciar esta ideia quando houver vaga. Nada a fazer por enquanto.")


def start_idea(repo, issue):
    gh("issue", "edit", str(issue["number"]), "--add-label", "ideia", "--remove-label", "fila", "-R", repo)
    return (f"Nova ideia na issue #{issue['number']}: {issue.get('title')}\n\n{issue.get('body') or ''}\n\n"
            "Inicie o discovery desta ideia conforme o protocolo.")


def inbox_item():
    files = sorted((ROOT / "factory/inbox").glob("*.md"))
    if not files:
        return None
    f = files[0]
    text = f.read_text()
    m = re.search(r"^slug:\s*([a-z0-9-]+)\s*$", text, re.M)
    return f.relative_to(ROOT).as_posix(), text, (m.group(1) if m else "")


# --- decisão -----------------------------------------------------------------

def reconcile(repo, owner, states, ledger):
    """Retorna (detail, slug, expect_issue) ou levanta Skip."""
    item = inbox_item()
    if item:
        path, text, slug = item
        return (f"Instrução de Rafael (caixa de entrada `{path}`), trate como um comentário dele:\n\n{text}\n\n"
                f"Ao terminar, apague `{path}` (git rm) no mesmo commit do state.json."), slug, None

    linked = {s.get("issue") for s in states}
    pending = [i for i in open_issues(repo, owner) if i["number"] not in linked and "fabrica" not in i["labels"]]
    if pending:
        if len(active_projects(states)) >= CONFIG["wip_limit"]:
            for i in pending:
                enqueue(repo, i["number"], states, already_queued="fila" in i["labels"])
        else:
            first = pending[0]
            return start_idea(repo, first), "", first["number"]

    for s in active_projects(states):
        last = (s.get("last_event") or {}).get("at") or s.get("updated_at") or ""
        act = project_activity(repo, s)
        if act and act > last:
            if fails_in_row(ledger, s["slug"]) >= MAX_FAILS:
                continue
            return (f"Retomada automática: há atividade na issue #{s['issue']} ou nos PRs do projeto posterior ao "
                    f"último evento registrado ({last or 'nenhum'}). Leia a thread e os PRs, trate o que estiver "
                    "pendente de Rafael e registre o evento."), s["slug"], None
    raise Skip("nada pendente", outcome="noop")


def decide(event_name, event, repo, owner, states, ledger=None):
    """Retorna (detail, slug, expect_issue). Levanta Skip para não rodar."""
    ledger = ledger or []
    sender = event.get("sender", {}).get("login", "")
    automatic = event_name in AUTOMATIC
    if CONFIG.get("owner_only", True) and not automatic and sender != owner:
        raise Skip(f"ator {sender} não é o dono", outcome="noop")

    action = event.get("action", "")
    issue = event.get("issue") or {}
    pr = event.get("pull_request") or {}
    number = issue.get("number") or pr.get("number")
    branch = pr.get("head", {}).get("ref")
    if issue.get("pull_request") and not branch:
        branch = gh("pr", "view", str(number), "-R", repo, "--json", "headRefName", "-q", ".headRefName").strip() or None
    slug = find_slug(states, number, branch)
    state = next((s for s in states if s["slug"] == slug), None)
    labels = {l["name"] for l in issue.get("labels", [])}

    if automatic:
        instr = (event.get("inputs") or {}).get("instrucao")
        if instr:
            return instr, "", None
        return reconcile(repo, owner, states, ledger)

    if event_name == "issues" and action == "opened":
        if "fabrica" in labels:
            return f"Melhoria da fábrica, issue #{number}: {issue.get('title')}\n\n{issue.get('body') or ''}", "", None
        if len(active_projects(states)) >= CONFIG["wip_limit"]:
            enqueue(repo, number, states)
            raise Skip("WIP cheio, ideia enfileirada", outcome="queued", issue=number)
        return start_idea(repo, {**issue, "labels": labels}), "", number

    if event_name == "issues" and action == "labeled":
        label = event.get("label", {}).get("name", "")
        if label not in ACTION_LABELS:
            raise Skip(f"label {label} sem ação", issue=number)
        if not slug:
            raise Skip("label em issue sem projeto", issue=number,
                       notify=f"O label `{label}` foi ignorado: esta issue não está ligada a nenhum projeto da fábrica.")
        if label == "retomar" and state and state.get("status") == "paused":
            if len(active_projects(states)) >= CONFIG["wip_limit"]:
                gh("issue", "edit", str(number), "--remove-label", "retomar", "--add-label", "fila", "-R", repo)
                raise Skip("WIP cheio, retomada enfileirada", outcome="queued", slug=slug, issue=number,
                           notify="⏸️ Retomada na fila: o limite de projetos ativos está cheio. Começa sozinha quando houver vaga.")
        return f"Rafael aplicou o label `{label}` na issue #{number}.", slug, None

    if event_name == "issue_comment" and action == "edited":
        body = event.get("comment", {}).get("body", "")
        before = event.get("changes", {}).get("body", {}).get("from", "")
        if "<!-- factory:" not in body:
            raise Skip("edição fora de bloco da fábrica", slug=slug, issue=number)
        checked = newly_checked(before, body)
        if not checked:
            raise Skip("nenhuma opção nova marcada", slug=slug, issue=number)
        if not slug:
            raise Skip("bloco marcado em item sem projeto", issue=number,
                       notify="Sua marcação foi ignorada: este item não está ligado a nenhum projeto da fábrica.")
        marker = re.search(r"<!-- factory:(\S+) ([^>]*)-->", body)
        return (f"Rafael marcou no bloco `{marker.group(1)} {marker.group(2).strip()}` (#{number}): "
                + "; ".join(checked) + f"\n\nTexto completo do bloco:\n{body}"), slug, None

    if event_name == "issue_comment" and action == "created":
        if not slug:
            if not issue.get("pull_request") and "fabrica" not in labels:
                if len(active_projects(states)) >= CONFIG["wip_limit"]:
                    enqueue(repo, number, states, already_queued="fila" in labels)
                    raise Skip("WIP cheio, ideia enfileirada", outcome="queued", issue=number)
                return start_idea(repo, issue) + f"\n\nComentário de Rafael:\n{event['comment']['body']}", "", number
            raise Skip("comentário em item sem projeto", issue=number)
        return f"Rafael comentou em #{number}:\n\n{event['comment']['body']}", slug, None

    if event_name == "pull_request" and action == "closed":
        if not pr.get("merged"):
            raise Skip("PR fechado sem merge", slug=slug, issue=number)
        if not slug:
            raise Skip("PR fora da fábrica", issue=number)
        return f"Rafael mergeou o PR #{number} (branch {branch}) = marco aprovado.", slug, None

    if event_name == "pull_request_review":
        if not slug:
            raise Skip("review fora da fábrica", issue=number)
        review = event.get("review", {})
        return f"Rafael revisou o PR #{number} ({review.get('state')}):\n\n{review.get('body') or ''}", slug, None

    raise Skip(f"evento {event_name}/{action} não tratado", outcome="noop")


def build_prompt(repo, event_name, action, slug, detail, states, run_id):
    state = next((s for s in states if s["slug"] == slug), None)
    state_txt = json.dumps(state, ensure_ascii=False, indent=2) if state else "(projeto ainda não existe)"
    return f"""Você está operando a fábrica de projetos. Siga estritamente o CLAUDE.md da raiz do repositório.

Repositório: {repo}
Execução (run_id): {run_id}
Evento: {event_name}/{action}
Projeto (slug): {slug or '(novo)'}

O que aconteceu:
{detail}

Estado atual do projeto:
{state_txt}

Antes de agir, leia a thread da issue e dos PRs do projeto: trate também qualquer ação de Rafael posterior a `last_event.at` que ainda não tenha sido atendida.

Ao terminar, o state.json do projeto em main deve ter `last_event` = {{"run_id": "{run_id}", "at": "<agora, ISO UTC>", "summary": "<uma frase em português do que foi feito>"}} e `next_action` preenchido. Sem isso a execução é marcada como falha."""


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    for name, color in LABELS.items():
        gh("label", "create", name, "--color", color, "--force", "-R", repo)

    states = common.load_states()
    ledger = common.read_ledger()
    automatic = event_name in AUTOMATIC
    key = "" if automatic else event_key(event_name, event)
    react = "" if automatic else react_target(event_name, event, repo)

    try:
        prior = [r for r in ledger if key and r.get("key") == key]
        if prior and prior[-1].get("outcome") in common.FINAL_OUTCOMES | {"queued"}:
            raise Skip(f"evento já processado ({prior[-1]['outcome']} em {prior[-1]['at']})", outcome="duplicate")
        detail, slug, expect = decide(event_name, event, repo, owner, states, ledger)
    except Skip as e:
        common.summary(f"### Fábrica: não executou\n- Evento: `{event_name}/{event.get('action', '')}`\n"
                       f"- Desfecho: **{e.outcome}**\n- Motivo: {e.reason}")
        if e.notify and e.issue:
            gh("issue", "comment", str(e.issue), "-R", repo, "--body", f"ℹ️ {e.notify}")
        if not automatic and e.outcome not in ("noop", "duplicate"):
            common.append_ledger({"run_id": run_id, "event": f"{event_name}/{event.get('action', '')}", "key": key,
                                  "slug": e.slug, "issue": e.issue, "outcome": e.outcome, "summary": e.reason})
            gh("workflow", "run", "pages.yml", "-R", repo)  # histórico do painel
        common.write_output(run="false", slug="", prompt="", max_turns=CONFIG["max_turns"], expect_issue="",
                            key=key, react_path="", prev_status="", issue="", inbox_path="", event="")
        return

    state = next((s for s in states if s["slug"] == slug), None)
    issue = (state or {}).get("issue") or expect or (event.get("issue") or event.get("pull_request") or {}).get("number") or ""
    prompt = build_prompt(repo, event_name, event.get("action", ""), slug, detail, states, run_id)
    common.summary(f"### Fábrica: executando\n- Evento: `{event_name}/{event.get('action', '')}`\n"
                   f"- Projeto: `{slug or '(novo)'}`\n- Motivo: {detail.splitlines()[0]}")
    inbox = ""
    if automatic and not (event.get("inputs") or {}).get("instrucao") and inbox_item():
        inbox = inbox_item()[0]
    common.write_output(run="true", slug=slug, prompt=prompt, max_turns=CONFIG["max_turns"], expect_issue=expect or "",
                        key=key, react_path=react, prev_status=(state or {}).get("status", ""), issue=issue,
                        inbox_path=inbox, event=f"{event_name}/{event.get('action', '')}")


if __name__ == "__main__":
    main()
