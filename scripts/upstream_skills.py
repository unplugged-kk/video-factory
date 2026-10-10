#!/usr/bin/env python
"""Install, verify or remove the pinned third-party skills listed in config/upstream-skills.lock.json.

  python scripts/upstream_skills.py sync   [--record]   clone the pinned tag, check the commit, copy the listed skills
  python scripts/upstream_skills.py verify               re-hash installed skills against the lock (exit 1 on any problem)
  python scripts/upstream_skills.py remove               delete exactly the skills the lock lists

`--record` writes the installed tree hashes into the lock; do that once after reviewing a new pin, then commit the lock."""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from contentos import upstream_skills as us  # noqa: E402

LOCK = REPO / "config/upstream-skills.lock.json"
SKILLS = REPO / ".claude/skills"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sync", "verify", "remove"])
    ap.add_argument("--record", action="store_true", help="sync: store tree hashes in the lock")
    ap.add_argument("--lock", default=str(LOCK))
    ap.add_argument("--skills-dir", default=str(SKILLS))
    a = ap.parse_args()
    lock, skills = Path(a.lock), Path(a.skills_dir)
    if a.cmd == "sync":
        hashes = us.sync(lock, skills)
        print(json.dumps(hashes, indent=1))
        if a.record:
            data = json.loads(lock.read_text())
            for s in data["sources"]:
                s["tree_sha256"] = hashes.get(s["id"], s.get("tree_sha256", {}))
            lock.write_text(json.dumps(data, indent=2) + "\n")
            print("recorded in", lock)
        return 0
    if a.cmd == "verify":
        problems = us.verify(lock, skills)
        print("OK: installed skills match the lock" if not problems else "\n".join(problems))
        return 1 if problems else 0
    print("removed:", ", ".join(us.remove(lock, skills)) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
