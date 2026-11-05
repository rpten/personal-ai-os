#!/usr/bin/env python3
"""Verifica o resultado de uma execução do agente e torna falhas visíveis.

Uso: verify.py <resultado_do_agente> [<issue_esperada>]
- Se o agente falhou: comenta na issue (se houver) e sai com erro.
- Se uma ideia deveria ter virado projeto e não virou (nenhum
  projects/*/state.json em origin/main aponta para ela): comenta e sai com erro.
Um job vermelho gera notificação do GitHub; o comentário mostra o motivo na issue.
"""
import json
import os
import subprocess
import sys

outcome = sys.argv[1] if len(sys.argv) > 1 else ""
issue = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
repo = os.environ["GITHUB_REPOSITORY"]
run_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def fail(msg):
    print(f"FALHA: {msg}")
    if issue:
        sh("gh", "issue", "comment", issue, "-R", repo, "--body",
           f"⚠️ A fábrica falhou nesta execução: {msg}\n\nNada a fazer da sua parte; a próxima reconciliação tenta de novo. Detalhes: {run_url}")
    sys.exit(1)


if outcome != "success":
    fail(f"o agente terminou com status `{outcome or 'desconhecido'}`.")

if issue:
    sh("git", "fetch", "-q", "origin", "main")
    files = sh("git", "ls-tree", "-r", "--name-only", "origin/main", "projects/").split()
    for f in files:
        if f.endswith("/state.json"):
            try:
                if json.loads(sh("git", "show", f"origin/main:{f}")).get("issue") == int(issue):
                    print(f"ok: ideia #{issue} virou projeto ({f})")
                    sys.exit(0)
            except json.JSONDecodeError:
                pass
    fail(f"a ideia #{issue} não virou projeto (nenhum state.json em main aponta para ela).")

print("ok")
