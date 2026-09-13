"""Test-wide guards.

**The suite must never write into `demo/data/`.** `runner.write_chain_file`
overwrites the handover file a beat produces, and several tests drive a whole
beat through `POST /api/run` without re-rooting the sector first. So running
`pytest` — which `AGENTS.md` §3 tells everyone to do — silently replaced the
shipped `demo/data/numismatica/demo/catena/d1-bozze.md` with stub output, in
English, 478 bytes where the shipped file is 2411.

Nothing fails at that moment. It fails in a room: PROJECT.md invariant 3 says
the chain never waits, and the shipped fallback is what D2 pastes when D1's live
run does not produce one. A trainer who ran the tests once would have handed the
room `draft t=1.0 turns=1`.

The fix is not to remember to re-root in each new test. Every test runs against a
*copy* of `demo/data/`: reads see the real material, writes land in a temporary
directory that is thrown away. A test that wants an empty or partial pack still
re-roots on top of this, as several already do.
"""

from __future__ import annotations

import shutil

import pytest

from app.server import demos, runner, runs


@pytest.fixture(autouse=True)
def demo_material_is_a_copy(tmp_path_factory, monkeypatch):
    """Point every sector root at a disposable copy of the shipped material.

    `runs` and `runner` bound `data_root` by name at import time, so patching
    `demos.data_root` alone would leave the two modules that actually write
    still pointing at the repository. All three are patched, which is also why
    no new module may import `data_root` by name without being added here.
    """
    real_root = demos.DB_PATH.parent / "data"
    if not real_root.is_dir():
        # A checkout with no generated packs. Nothing to protect, and
        # `data_root` still resolves — to a path that does not exist, which is
        # what pre-flight is built to report.
        return

    copy_root = tmp_path_factory.mktemp("demo-data") / "data"
    shutil.copytree(real_root, copy_root)

    original = demos.data_root

    def rerooted(sector: str):
        # Through the real resolver, so an unknown sector still raises KeyError
        # and the Italian folder name still comes from the database.
        return copy_root / original(sector).name

    for module in (demos, runs, runner):
        monkeypatch.setattr(module, "data_root", rerooted)
