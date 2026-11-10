"""Opt-in, metadata-only CEH discovery. Never invoked by the production pipeline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ceh_contract import load_catalog, select_capabilities


def recommend(*, path: Path | None = None, enabled: bool = False, expected_digest: str | None = None,
              task: str, renderer: str = "hyperframes", environment: dict | None = None) -> dict:
    """Caller supplies measured environment. No probes, downloads, skill reads or execution."""
    loaded = load_catalog(path, enabled=enabled, expected_digest=expected_digest)
    if not loaded["available"]:
        return {"available": False, "selected": [], "rejected": [], "errors": loaded["errors"],
                "fallback": "Use existing Video Factory routing; CEH supplies no selection."}
    try:
        result = select_capabilities(loaded["catalog"], task=task, renderer=renderer, **(environment or {}))
    except (TypeError, ValueError, AttributeError, OverflowError, RecursionError) as exc:
        return {"available": False, "selected": [], "rejected": [], "errors": [f"invalid environment: {exc}"],
                "fallback": "Use existing Video Factory routing; CEH supplies no selection."}
    return {"available": not bool(result["errors"]), **result, "catalog_digest": loaded["catalog"]["digest"],
            "execution": "metadata only; existing approval and QA gates remain required"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="opt in for this invocation only")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--trusted-digest", help="independently reviewed catalog digest")
    parser.add_argument("--task", required=True)
    parser.add_argument("--renderer", default="hyperframes")
    parser.add_argument("--environment", type=Path, help="JSON containing measured runtimes, dependencies and inputs")
    args = parser.parse_args(argv)
    try:
        environment = json.loads(args.environment.read_text()) if args.environment else {}
        allowed = {"runtimes", "dependencies", "inputs", "assets", "agent", "language", "output_format", "commercial"}
        if not isinstance(environment, dict) or set(environment) - allowed:
            raise ValueError("unknown environment fields")
        result = recommend(path=args.catalog, enabled=args.enable, expected_digest=args.trusted_digest,
                           task=args.task, renderer=args.renderer, environment=environment)
    except (OSError, ValueError, TypeError) as exc:
        result = {"available": False, "selected": [], "rejected": [], "errors": [str(exc)]}
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result.get("available") or not args.enable else 1


if __name__ == "__main__":
    raise SystemExit(main())
