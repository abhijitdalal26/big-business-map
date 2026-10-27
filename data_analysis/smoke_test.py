"""Smoke test: build the context and run every analysis module."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import context as ctxmod  # noqa: E402
import analysis  # noqa: E402

# The console on Windows is cp1252 and cannot render the rho / sigma / mu
# glyphs the insight copy uses. Force UTF-8 so the smoke test can print them.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):       # pragma: no cover
        pass


def main() -> int:
    print("building context ...")
    ctx = ctxmod.build(verbose=True)
    print(f"universe rows: {len(ctx.universe):,} | reconciled: {len(ctx.reconciled):,}")

    failures = 0
    for mod in analysis.MODULES:
        print(f"\n=== {mod.KEY} ===")
        try:
            res = mod.run(ctx)
        except Exception:
            failures += 1
            traceback.print_exc()
            continue
        m = res["metrics"]
        try:
            json.dumps(m)
        except (TypeError, ValueError) as e:
            failures += 1
            print(f"  !! metrics not JSON-safe: {e}")
            continue
        print(f"  metrics keys: {len(m)} | tables: {list(res['tables'])}")
        try:
            ins = mod.insights(m)
        except Exception:
            failures += 1
            traceback.print_exc()
            continue
        for line in ins:
            print("  -", line[:190])

    print(f"\n\n{'ALL OK' if not failures else f'{failures} FAILURES'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
