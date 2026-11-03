"""python -m contentos.scenekit {styles|validate|recommend|plan} [SPEC.yaml]  (no rendering, no network)"""
import json
import sys

import yaml

from . import planner, styles


def main(argv):
    cmd = argv[0] if argv else "styles"
    if cmd == "styles":
        for sid, s in styles.STYLES.items():
            a = styles.axes_of(sid)
            print(f"{sid:24} v{s['version']}  {a['layout']:16} {a['motion']:8} {a['ground']:5}  {s['summary']}")
        p = styles.validate()
        print("problems:", p or "none")
        return 1 if p else 0
    spec = yaml.safe_load(open(argv[1]))
    if cmd == "validate":
        errs = planner.validate_spec_visuals(spec)
        print("\n".join(errs) or "ok")
        return 1 if errs else 0
    if cmd == "recommend":
        print(json.dumps(planner.recommend(spec), indent=1))
        return 0
    if cmd == "plan":
        pl = planner.plan(spec)
        print(json.dumps({"plan": pl, "variety": planner.variety_report(pl)}, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
