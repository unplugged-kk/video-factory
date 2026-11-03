"""Render one spec in several scenekit styles (same script, only `visual_style` + content_id change).

  PATH=/opt/homebrew/bin:$PATH ~/.contentos/venv/bin/python scripts/style_matrix.py examples/styles/kafka-events.yaml blueprint-architecture,editorial-magazine
  python scripts/style_matrix.py SPEC STYLES [--compose-only]

Writes variant specs under $VIDEO_FACTORY_WORKSPACE/experiments/style-evolution/specs/. Runs brief, script, voice,
compose, render, qa and NEVER export or publish. `--approve-private` is used because these are sample jobs whose
content_id starts with `sample-`; refused for any other id.
"""
import copy
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from contentos import storage  # noqa: E402

STAGES = ["brief", "script", "voice", "compose", "render", "qa"]


def main(argv):
    spec_path, styles = Path(argv[0]), argv[1].split(",")
    stages = STAGES[:4] if "--compose-only" in argv else STAGES
    base = yaml.safe_load(spec_path.read_text())
    if not base["content_id"].startswith("sample-"):
        sys.exit("refusing: only sample-* content ids may use the private approval shortcut")
    out = storage.workspace_root() / "experiments/style-evolution/specs"
    out.mkdir(parents=True, exist_ok=True)
    for sid in styles:
        spec = copy.deepcopy(base)
        spec["content_id"] = f"{base['content_id']}-{sid.split('-')[0]}"
        spec["visual_style"] = {**spec.get("visual_style", {}), "id": sid}
        p = out / f"{spec['content_id']}.yaml"
        p.write_text(yaml.safe_dump(spec, sort_keys=False))
        for st in stages:
            r = subprocess.run([str(ROOT / "contentos.sh"), "pipeline", "run", str(p), "--only", st, "--approve-private"])
            if r.returncode:
                sys.exit(f"{spec['content_id']}: stage {st} failed")


if __name__ == "__main__":
    main(sys.argv[1:])
