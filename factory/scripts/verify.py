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
import re
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


FRONTEND_RE = re.compile(r"\.(html?|css|jsx?|tsx?|mjs|vue|svelte)$")
DESIGN_SECTIONS = {"design/brief.md": ["## Brief", "## Direção", "## UX"]}
REVIEW_SECTIONS = ["## Problemas", "## Correções", "## Revalidação"]


def git(*a):
    return subprocess.run(["git", "-C", str(common.ROOT), *a], capture_output=True, text=True)


def frontend_changed(slug, branch, base="origin/main"):
    names = git("diff", "--name-only", f"{base}...origin/{branch}").stdout.split()
    return [n for n in names if n.startswith(f"projects/{slug}/public/") or
            (n.startswith(f"projects/{slug}/") and FRONTEND_RE.search(n) and "/test" not in n and "/worker/" not in n)]


def design_gate(slug, n, read_file, run_qa):
    """Problemas do portão de design de um marco com mudança de interface. Lista vazia = ok.
    read_file(path) -> texto ou None; run_qa() -> relatório do visual_qa."""
    probs = []
    base = f"projects/{slug}/"
    brief = read_file(base + "design/brief.md")
    if brief is None:
        probs.append("falta design/brief.md (brief, direção e UX)")
    else:
        miss = [h for h in DESIGN_SECTIONS["design/brief.md"] if h not in brief]
        if miss:
            probs.append("design/brief.md sem as seções " + ", ".join(miss))
    flows = read_file(base + "design/flows.json")
    if flows is None:
        probs.append("falta design/flows.json (fluxos e estados para o QA visual)")
    else:
        try:
            json.loads(flows)
        except json.JSONDecodeError:
            probs.append("design/flows.json inválido")
    review = read_file(base + f"evidence/m{n}/design-review.md")
    if review is None:
        probs.append(f"falta evidence/m{n}/design-review.md (inspeção dos prints, correções e revalidação)")
    else:
        miss = [h for h in REVIEW_SECTIONS if h not in review]
        if miss:
            probs.append("design-review.md sem as seções " + ", ".join(miss))
    if flows is not None and not probs:
        rep = run_qa()
        if rep.get("blocking"):
            tops = sorted({i["rule"] for r in rep["results"] for i in r["issues"] if i["severity"] == "blocking"})
            probs.append(f"QA visual com {rep['blocking']} bloqueante(s): {', '.join(tops)}")
    return probs


def gate_applies(head_iso):
    """O portão vale para trabalho feito depois de config.design_gate_since."""
    from datetime import datetime
    since = common.CONFIG.get("design_gate_since")
    if not since or not head_iso:
        return True
    parse = lambda t: datetime.fromisoformat(t.replace("Z", "+00:00"))
    return parse(head_iso) >= parse(since)


def check_design(state):
    """Roda o portão no marco aguardando aprovação, se ele mexeu em interface. Retorna problemas."""
    waiting = [m for m in state.get("milestones", []) if m.get("status") == "awaiting_approval" and m.get("pr")]
    if not waiting:
        return []
    m = max(waiting, key=lambda m: m["n"])  # o marco mais recente é o desta execução
    slug, n = state["slug"], m["n"]
    branch = f"factory/{slug}/m{n}"
    if git("fetch", "-q", "origin", branch).returncode != 0:
        return []  # marco sem branch padrão (ex.: ajuste fora do fluxo); nada a conferir
    head_at = git("log", "-1", "--format=%cI", f"origin/{branch}").stdout.strip()
    if not gate_applies(head_at):
        return []  # marco anterior à Design Capability
    if not frontend_changed(slug, branch):
        return []
    wt = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "design-wt"
    git("worktree", "remove", "--force", str(wt))
    git("worktree", "add", "-q", "--detach", str(wt), f"origin/{branch}")

    def read_file(rel):
        f = wt / rel
        return f.read_text() if f.exists() else None

    def run_qa():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import visual_qa
        out = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "design-qa"
        sha = git("rev-parse", "--short", f"origin/{branch}").stdout.strip()
        rep = visual_qa.run(wt / f"projects/{slug}/public", out, wt / f"projects/{slug}/design/flows.json", sha)
        common.summary((out / "visual-qa.md").read_text())
        return rep

    try:
        return design_gate(slug, n, read_file, run_qa)
    finally:
        git("worktree", "remove", "--force", str(wt))


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


def agent_skills(path):
    """Skills disponíveis e efetivamente usadas pelo agente (do log do Claude Code)."""
    loaded, used = [], []
    try:
        for line in Path(path).read_text().splitlines():
            if not line.startswith("{"):
                continue
            ev = json.loads(line)
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                loaded = ev.get("skills") or [c for c in ev.get("slash_commands", []) if "design" in c or "ux" in c]
            for c in (ev.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                    used.append((c.get("input") or {}).get("skill") or (c.get("input") or {}).get("command"))
    except (OSError, json.JSONDecodeError):
        pass
    return {"skills_available": loaded, "skills_used": [u for u in used if u]} if (loaded or used) else {}


def main():
    env = os.environ.get
    repo, run_id = env("GITHUB_REPOSITORY", ""), env("GITHUB_RUN_ID", "local")
    run_url = f"{env('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{run_id}"
    slug, issue = env("SLUG", ""), env("ISSUE", "")
    outcome, reason, state = evaluate(env("AGENT_OUTCOME", ""), slug, env("EXPECT_ISSUE", ""),
                                      env("PREV_STATUS", ""), run_id, env("INBOX_PATH", ""), main_states())
    if outcome in ("done", "waiting") and state and not os.environ.get("FACTORY_DRY"):
        probs = check_design(state)
        if probs:
            outcome, reason = "failed", "portão de design do marco: " + "; ".join(probs)
    skills = agent_skills(Path(env("RUNNER_TEMP", "/tmp")) / "agent.jsonl")
    slug = slug or (state or {}).get("slug", "")
    issue = issue or (state or {}).get("issue") or ""

    icon = {"done": "✅", "waiting": "👉", "blocked": "⛔", "failed": "❌"}[outcome]
    common.summary(f"### {icon} Desfecho: **{outcome}**\n- Projeto: `{slug or '-'}`\n- {reason}")
    common.react(env("REACT_PATH", ""), "confused" if outcome == "failed" else "rocket")
    common.append_ledger({"run_id": run_id, "event": env("EVENT", ""), "key": env("KEY", ""), "slug": slug,
                          "issue": int(issue) if str(issue).isdigit() else None, "outcome": outcome, "summary": reason,
                          **skills})

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
