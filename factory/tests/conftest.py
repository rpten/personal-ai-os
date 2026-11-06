import importlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPO_ROOT = SCRIPTS.parents[1]
REPO, OWNER = "rpten/personal-ai-os", "rpten"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def env(tmp_path, monkeypatch):
    (tmp_path / "factory").mkdir()
    for f in ("config.json", "state.schema.json"):
        (tmp_path / "factory" / f).write_text((SCRIPTS.parent / f).read_text())
    (tmp_path / "projects").mkdir()
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    monkeypatch.setenv("FACTORY_DRY", "1")
    for v in ("FACTORY_FAKE_ISSUES", "FACTORY_FAKE_ACTIVITY", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(v, raising=False)
    import common
    importlib.reload(common)
    import guard
    importlib.reload(guard)
    import verify
    importlib.reload(verify)

    class E:
        g, c, v, root = guard, common, verify, tmp_path

        def project(self, slug, issue, status="discovery", prs=(), last_at=None, **extra):
            d = tmp_path / "projects" / slug
            d.mkdir(exist_ok=True)
            st = {"slug": slug, "title": slug, "issue": issue, "status": status,
                  "milestones": [{"n": i + 1, "title": "m", "status": "pending", "pr": p} for i, p in enumerate(prs)],
                  "next_action": {"owner": "rafael", "text": "x"}}
            if last_at:
                st["last_event"] = {"run_id": "1", "at": last_at, "summary": "s"}
            st.update(extra)
            (d / "state.json").write_text(json.dumps(st))
            return st

        def issues(self, items):
            p = tmp_path / "issues.json"
            p.write_text(json.dumps(items))
            monkeypatch.setenv("FACTORY_FAKE_ISSUES", str(p))

        def activity(self, mapping):
            p = tmp_path / "activity.json"
            p.write_text(json.dumps(mapping))
            monkeypatch.setenv("FACTORY_FAKE_ACTIVITY", str(p))

        def ledger(self, records):
            d = tmp_path / "factory/events"
            d.mkdir(parents=True, exist_ok=True)
            (d / "2026-11.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))

        def decide(self, name, event):
            event.setdefault("sender", {"login": OWNER})
            return guard.decide(name, event, REPO, OWNER, common.load_states(), common.read_ledger())

        def run_main(self, name, event):
            """Roda guard.main() como na workflow e devolve as saídas."""
            event.setdefault("sender", {"login": OWNER})
            ev = tmp_path / "event.json"
            ev.write_text(json.dumps(event))
            out = tmp_path / "out.txt"
            out.write_text("")
            monkeypatch.setenv("GITHUB_EVENT_NAME", name)
            monkeypatch.setenv("GITHUB_EVENT_PATH", str(ev))
            monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
            monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", OWNER)
            monkeypatch.setenv("GITHUB_RUN_ID", "99")
            monkeypatch.setenv("GITHUB_OUTPUT", str(out))
            guard.main()
            res, lines, i = {}, out.read_text().splitlines(), 0
            while i < len(lines):
                k, _, v = lines[i].partition("=")
                if "<<" in lines[i] and "=" not in lines[i]:
                    k = lines[i].split("<<")[0]
                    j = lines.index("__EOF__", i + 1)
                    res[k] = "\n".join(lines[i + 1:j])
                    i = j + 1
                    continue
                res[k] = v
                i += 1
            return res

    return E()
