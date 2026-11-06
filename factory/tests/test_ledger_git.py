"""Ledger com git de verdade: publica em main e sobrevive a corrida entre execuções."""
import importlib
import json
import subprocess


def sh(*a, cwd=None):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


def clone(origin, dest):
    sh("git", "clone", "-q", str(origin), str(dest))
    sh("git", "config", "user.email", "t@t", cwd=dest)
    sh("git", "config", "user.name", "t", cwd=dest)


def test_append_publica_e_resiste_a_corrida(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    sh("git", "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    clone(origin, seed)
    (seed / "factory").mkdir()
    (seed / "factory/config.json").write_text(json.dumps({"wip_limit": 1, "max_turns": 10}))
    sh("git", "add", ".", cwd=seed)
    sh("git", "commit", "-qm", "seed", cwd=seed)
    sh("git", "push", "-q", "origin", "HEAD:main", cwd=seed)

    a, b = tmp_path / "a", tmp_path / "b"
    clone(origin, a)
    clone(origin, b)
    monkeypatch.delenv("FACTORY_DRY", raising=False)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    import common

    monkeypatch.setenv("FACTORY_ROOT", str(a))
    importlib.reload(common)
    common.append_ledger({"key": "k1", "outcome": "done"})
    # b está desatualizado (não viu k1): o push precisa rebasear e não perder nada
    monkeypatch.setenv("FACTORY_ROOT", str(b))
    importlib.reload(common)
    common.append_ledger({"key": "k2", "outcome": "failed"})

    check = tmp_path / "check"
    clone(origin, check)
    monkeypatch.setenv("FACTORY_ROOT", str(check))
    importlib.reload(common)
    keys = [r["key"] for r in common.read_ledger()]
    assert keys == ["k1", "k2"]
    # a cópia de trabalho dos jobs não é tocada
    assert not (b / "factory/events").exists()
