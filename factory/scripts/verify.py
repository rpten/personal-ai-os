#!/usr/bin/env python3
"""Verificação determinística do resultado de uma execução do agente.

Uma execução só conta como feita se, em origin/main:
- o state.json do projeto tem `last_event.run_id` igual a esta execução;
- o estado é válido (schema + next_action) e a transição de status é permitida;
- a ideia esperada (se houver) virou projeto;
- a instrução da caixa de entrada (se houver) foi apagada.

Desfechos: done (concluído), waiting (concluído, aguardando Rafael),
blocked (precisa de decisão), failed. Tudo vai para o ledger, para o resumo
da execução e para uma reação no item que Rafael tocou; falhas também
comentam na issue e deixam o job vermelho.

Uso (env): AGENT_OUTCOME, SLUG, EXPECT_ISSUE, PREV_STATUS, KEY, REACT_PATH,
ISSUE, EVENT, INBOX_PATH, GITHUB_RUN_ID, GITHUB_REPOSITORY.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def main_states(ref="origin/main"):
    """Estados como estão em main após a execução."""
    if os.environ.get("FACTORY_DRY"):
        return common.load_states()
    subprocess.run(["git", "-C", str(common.ROOT), "fetch", "-q", "origin", "main"], check=False)
    files = subprocess.run(["git", "-C", str(common.ROOT), "ls-tree", "-r", "--name-only", ref, "projects/"],
                           capture_output=True, text=True).stdout.split()
    out = []
    for f in files:
        if f.endswith("/state.json"):
            raw = subprocess.run(["git", "-C", str(common.ROOT), "show", f"{ref}:{f}"], capture_output=True, text=True).stdout
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                out.append({"slug": f.split("/")[1], "_invalid": True})
    return out


def path_exists_in_main(path, ref="origin/main"):
    if os.environ.get("FACTORY_DRY"):
        return (common.ROOT / path).exists()
    return subprocess.run(["git", "-C", str(common.ROOT), "cat-file", "-e", f"{ref}:{path}"],
                          capture_output=True).returncode == 0


def evaluate(agent_outcome, slug, expect_issue, prev_status, run_id, inbox_path, states):
    """Retorna (outcome, motivo, estado_do_projeto_ou_None). Pura: testável."""
    if agent_outcome != "success":
        return "failed", f"o agente terminou com status `{agent_outcome or 'desconhecido'}`", None
    if inbox_path and path_exists_in_main(inbox_path):
        return "failed", f"a instrução `{inbox_path}` continua na caixa de entrada", None

    state = None
    if slug:
        state = next((s for s in states if s.get("slug") == slug), None)
    elif expect_issue:
        state = next((s for s in states if str(s.get("issue")) == str(expect_issue)), None)
        if not state:
            return "failed", f"a ideia #{expect_issue} não virou projeto", None
    if state is None:
        if slug:
            return "failed", f"o projeto `{slug}` não tem state.json em main", None
        return "done", "execução sem projeto associado (fábrica/instrução geral)", None

    if state.get("_invalid"):
        return "failed", "state.json inválido (JSON quebrado)", state
    if str((state.get("last_event") or {}).get("run_id")) != str(run_id):
        return "failed", "o agente terminou sem registrar esta execução no state.json (last_event)", state
    errors = common.validate_state(state)
    if errors:
        return "failed", "estado inválido: " + "; ".join(errors[:3]), state
    if not common.valid_transition(prev_status or None, state["status"]):
        return "failed", f"transição de status inválida: {prev_status or '(novo)'} → {state['status']}", state
    if state["status"] == "blocked":
        return "blocked", state["last_event"].get("summary", ""), state
    if (state.get("next_action") or {}).get("owner") == "rafael":
        return "waiting", state["last_event"].get("summary", ""), state
    return "done", state["last_event"].get("summary", ""), state


def main():
    env = os.environ.get
    repo, run_id = env("GITHUB_REPOSITORY", ""), env("GITHUB_RUN_ID", "local")
    run_url = f"{env('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{run_id}"
    slug, issue = env("SLUG", ""), env("ISSUE", "")
    outcome, reason, state = evaluate(env("AGENT_OUTCOME", ""), slug, env("EXPECT_ISSUE", ""),
                                      env("PREV_STATUS", ""), run_id, env("INBOX_PATH", ""), main_states())
    slug = slug or (state or {}).get("slug", "")
    issue = issue or (state or {}).get("issue") or ""

    icon = {"done": "✅", "waiting": "👉", "blocked": "⛔", "failed": "❌"}[outcome]
    common.summary(f"### {icon} Desfecho: **{outcome}**\n- Projeto: `{slug or '-'}`\n- {reason}")
    common.react(env("REACT_PATH", ""), "confused" if outcome == "failed" else "rocket")
    common.append_ledger({"run_id": run_id, "event": env("EVENT", ""), "key": env("KEY", ""), "slug": slug,
                          "issue": int(issue) if str(issue).isdigit() else None, "outcome": outcome, "summary": reason})

    if outcome == "failed":
        from guard import MAX_FAILS, fails_in_row
        fails = fails_in_row(common.read_ledger(), slug) if slug else 1
        if fails < MAX_FAILS:
            tail = ("A fábrica tenta de novo sozinha na próxima reconciliação (em até 1 hora).\n\n"
                    "⏳ **Comigo:** nova tentativa automática. Nada a fazer por enquanto.")
        else:
            tail = ("Parei as tentativas automáticas após 3 falhas seguidas.\n\n"
                    "👉 **Sua vez:** comente aqui **tentar de novo** quando quiser (o diagnóstico já está salvo).")
        if issue:
            common.gh("issue", "comment", str(issue), "-R", repo, "--body",
                      f"❌ **A fábrica falhou nesta execução:** {reason}.\n\n{tail}\n\n<sub>[execução]({run_url})</sub>")
        sys.exit(1)


if __name__ == "__main__":
    main()
