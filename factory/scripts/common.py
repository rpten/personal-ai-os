"""Base compartilhada da fábrica: configuração, gh, estado, transições e ledger.

Ledger (factory/events/AAAA-MM.jsonl): um registro por evento de Rafael com
o desfecho final — ignored, queued, done, waiting (concluído e aguardando
Rafael), blocked, failed. É a memória de execução da fábrica: alimenta a
idempotência, o limite de falhas, o histórico do painel e a auditoria.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("FACTORY_ROOT", Path(__file__).resolve().parents[2]))
CONFIG = json.loads((ROOT / "factory/config.json").read_text())
DRY = bool(os.environ.get("FACTORY_DRY"))
GH_LOG = []  # comandos gh emitidos (inspecionado pelos testes)

ACTIVE = {"discovery", "awaiting_plan_approval", "executing", "awaiting_milestone_approval", "blocked"}
STATUSES = ACTIVE | {"delivered", "paused", "closed"}

# Transições permitidas (de -> para). Mesmo status é sempre permitido.
TRANSITIONS = {
    None: {"discovery"},
    "discovery": {"awaiting_plan_approval", "blocked", "paused", "closed"},
    "awaiting_plan_approval": {"discovery", "executing", "awaiting_milestone_approval", "blocked", "paused", "closed"},
    "executing": {"awaiting_milestone_approval", "blocked", "delivered", "paused", "closed"},
    "awaiting_milestone_approval": {"executing", "delivered", "blocked", "paused", "closed"},
    "blocked": ACTIVE | {"delivered", "paused", "closed"},
    "delivered": {"awaiting_milestone_approval", "executing", "discovery", "closed", "paused"},
    "paused": ACTIVE | {"closed"},
    "closed": {"discovery"},
}
FINAL_OUTCOMES = {"done", "waiting", "blocked"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gh(*args, check=False):
    GH_LOG.append(list(args))
    if DRY:
        return ""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"gh {' '.join(args)} falhou: {r.stderr.strip()}", file=sys.stderr)
        if check:
            raise RuntimeError(r.stderr)
    return r.stdout


def valid_transition(old, new):
    return old == new or new in TRANSITIONS.get(old, set())


def load_states(root=None):
    root = root or ROOT
    states = []
    for p in sorted((root / "projects").glob("*/state.json")):
        try:
            states.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            print(f"state inválido: {p}", file=sys.stderr)
    return states


def validate_state(state):
    """Erros de schema + regras que o schema não expressa. Lista vazia = válido."""
    errors = []
    try:
        import jsonschema
        schema = json.loads((ROOT / "factory/state.schema.json").read_text())
        v = jsonschema.Draft202012Validator(schema)
        errors += [f"{'/'.join(map(str, e.path)) or '(raiz)'}: {e.message}" for e in v.iter_errors(state)]
    except ImportError:
        errors.append("jsonschema não instalado")
    if state.get("status") in ACTIVE | {"delivered"} and not (state.get("next_action") or {}).get("text"):
        errors.append("next_action vazio")
    return errors


# --- ledger ------------------------------------------------------------------

def ledger_dir(root=None):
    return (root or ROOT) / "factory/events"


def read_ledger(root=None):
    out = []
    for p in sorted(ledger_dir(root).glob("*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def append_ledger(record, push=True):
    """Acrescenta um registro e publica em main (com retry em caso de corrida)."""
    record = {"at": now(), **record}
    path = ledger_dir() / f"{record['at'][:7]}.jsonl"
    rel = path.relative_to(ROOT).as_posix()
    line = json.dumps(record, ensure_ascii=False)
    if DRY or not push:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line + "\n")
        return record
    # Worktree separado: não toca a cópia de trabalho do job (que pode ter
    # alterações do agente).
    wt = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "ledger-wt"
    git = ["git", "-C", str(ROOT)]
    for attempt in range(5):
        subprocess.run(git + ["worktree", "remove", "--force", str(wt)], capture_output=True)
        subprocess.run(git + ["fetch", "-q", "origin", "main"], check=False)
        subprocess.run(git + ["worktree", "add", "-q", "--detach", str(wt), "origin/main"], check=True)
        target = wt / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a") as f:
            f.write(line + "\n")
        g = ["git", "-C", str(wt)]
        subprocess.run(g + ["add", rel], check=True)
        subprocess.run(g + ["-c", "user.name=factory-bot",
                            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                            "commit", "-qm", f"ledger: {record.get('outcome')} {record.get('key', '')}"], check=True)
        if subprocess.run(g + ["push", "-q", "origin", "HEAD:main"]).returncode == 0:
            subprocess.run(git + ["worktree", "remove", "--force", str(wt)], capture_output=True)
            return record
        time.sleep(2 + attempt * 2)
    print("não foi possível gravar o ledger após 5 tentativas", file=sys.stderr)
    return record


def summary(text):
    """Escreve no resumo da execução (aba Summary do Actions)."""
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(text + "\n")
    print(text)


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


def react(path, content):
    """Reação de status no item que Rafael tocou: eyes (executando), rocket (ok), confused (falha)."""
    if path:
        gh("api", "-X", "POST", path, "-f", f"content={content}", "-H", "Accept: application/vnd.github+json")
