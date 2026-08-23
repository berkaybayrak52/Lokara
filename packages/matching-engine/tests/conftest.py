"""Make the shared, data-only Page 08 oracle importable from this package's tests.

`docs/15-bank-matching.md` line 11 names `packages/rules-store/tests/berkay_15_golden.py`
as the single location of the thirteen `BANKMATCH-F01`-`F13` cases.  The oracle is not
copied or moved here: moving it would make the approved document stale.  The rules-store
tests import it as a plain top-level module because pytest puts each rootless test
directory on `sys.path`.  This hook extends the same path so that

    uv run pytest packages/matching-engine/tests

resolves `berkay_15_golden` when this package is run on its own as well as inside the
full workspace suite.
"""

import sys
from pathlib import Path

_ORACLE_DIR = Path(__file__).resolve().parents[2] / "rules-store" / "tests"

if not _ORACLE_DIR.is_dir():  # pragma: no cover - defensive, keeps the failure legible
    raise RuntimeError(f"Page 08 oracle directory is missing: {_ORACLE_DIR}")

if str(_ORACLE_DIR) not in sys.path:
    sys.path.insert(0, str(_ORACLE_DIR))
