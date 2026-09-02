#!/usr/bin/env python3
"""Prove the Lab 01 tests can fail.

    python3 mutation_check.py

A wrapper. The runner is `instructor/labkit/mutate.py`; the eleven mutants —
each a deliberate wrong implementation some test claims to catch — are declared
in `labconfig.py`. Exits 0 only if every one of them is caught.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "instructor"))

from labkit import config, mutate  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(mutate.run(config.load(HERE)))
