"""Build a sector's retrieval index. Run this before the lesson, not during it.

D3's third rung and D5-A both retrieve from a per-sector Chroma collection. The
first build loads a sentence-transformers model and, on a machine that has
never run one, downloads it — several hundred megabytes. That is a fine thing to
do the night before and a catastrophic thing to discover at a projector, which
is why it is a command you run and not something the harness does on demand.

    python scripts/build_index.py --settore numismatics
    python scripts/build_index.py --tutti
    python scripts/build_index.py --stato

`--stato` reports without loading any model, which is the same check pre-flight
runs on every page load.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.server import corpus  # noqa: E402
from app.server.demos import sectors  # noqa: E402


def _state(sector: str) -> str:
    state = corpus.index_state(sector)
    mark = "OK  " if state["ready"] and state["chunks"] else "--  "
    detail = f"{state['chunks']} passaggi" if state["ready"] else "non costruito"
    return f"{mark}{sector:<22} {detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settore", "--sector", dest="sector")
    parser.add_argument("--tutti", "--all", dest="all_sectors", action="store_true")
    parser.add_argument("--stato", "--status", dest="status", action="store_true")
    args = parser.parse_args()

    known = [s["id"] for s in sectors()]

    if args.status or not (args.sector or args.all_sectors):
        print("Indici per settore:\n")
        for sector in known:
            print("  " + _state(sector))
        if not (args.sector or args.all_sectors):
            print("\nPer costruirne uno:  python scripts/build_index.py --settore <id>")
        return 0

    targets = known if args.all_sectors else [args.sector]
    failed = 0
    for sector in targets:
        if sector not in known:
            print(f"Settore sconosciuto: {sector}. Noti: {', '.join(known)}")
            failed += 1
            continue
        try:
            result = corpus.build_index(sector)
        except FileNotFoundError as exc:
            # A sector whose pack was never generated. Named, not a traceback:
            # three of the six ship without material and the console says so.
            print(f"--  {sector}: {exc}")
            failed += 1
            continue
        print(f"OK  {sector}: {result['chunks']} passaggi da "
              f"{len(result['documents'])} documenti")
        for document in result["documents"]:
            print(f"      {document}")
    return 1 if failed and failed == len(targets) else 0


if __name__ == "__main__":
    raise SystemExit(main())
