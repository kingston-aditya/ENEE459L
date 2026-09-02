#!/usr/bin/env python3
"""Generate the Lab 01 student starter from the instructor solution.

    python3 make_starter.py          # rebuild starter/ from solution/
    python3 make_starter.py --check  # verify starter/ is current and leak-free

A wrapper. The generator is `instructor/labkit/starter.py`; what it does for this
lab — which functions are stubbed, what hints they carry, which strings would
count as a leak — is declared in `labconfig.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "instructor"))

from labkit import config, starter  # noqa: E402


def main() -> int:
    cfg = config.load(HERE)
    if "--check" in sys.argv[1:]:
        return starter.check(cfg)
    starter.build(cfg)
    return starter.check(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
