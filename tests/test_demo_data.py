"""Every demo's material, checked before a lesson rather than during one.

The failure this replaces is a missing-file error raised at Run time, in
Italian, in front of a room. These tests build packs on disk and assert that
pre-flight names exactly what is absent.
"""

from __future__ import annotations

import pytest

from app.server import demos, preflight

#: A complete numismatics pack, as `demo/kit/generate.py` produces one.
COMPLETE = {
    "_perito/ground-truth.csv": "file",
    "regole/regolamento-catalogazione.md": "file",
    "lotti/lotto-001.pdf": "file",
    "avvelenata/lotto-047.pdf": "file",
    "demo/m2-cinque-attributi.md": "file",
    "demo/m2-tre-candidati.md": "file",
    "demo/m4-grezzi.md": "file",
    "demo/catena/d1-bozze.md": "file",
    "demo/catena/d2-criteri.md": "file",
    "demo/catena/d3-fonte.md": "file",
    "demo/catena/d4-tabella.md": "file",
    "demo/catena/d5-verifiche-umane.md": "file",
}


def build(root, entries) -> None:
    for path in entries:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")


@pytest.fixture
def pack(tmp_path, monkeypatch):
    """A sector pack under our control, with `data_root` pointed at it.

    Mirrors the real resolver: every declared sector maps to a folder under one
    root, and a sector whose pack was never generated resolves to a path that
    does not exist. Only a sector id absent from the database raises.
    """
    folders = {s["id"]: s["data"]["folder"] for s in demos.load()["sectors"]}

    def fake_root(sector: str):
        if sector not in folders:
            raise KeyError(sector)
        return tmp_path / folders[sector]

    monkeypatch.setattr(demos, "data_root", fake_root)
    root = tmp_path / folders["numismatics"]
    root.mkdir()
    return root


def test_a_complete_pack_passes_for_every_demo(pack):
    build(pack, COMPLETE)
    state = preflight.demo_data("numismatics")
    assert state["ok"] is True
    assert len(state["demos"]) == 5
    assert all(d["ok"] for d in state["demos"].values())


def test_a_missing_pack_is_reported_with_the_command_that_fixes_it(pack, monkeypatch):
    monkeypatch.setattr(demos, "data_root", lambda s: pack / "does-not-exist")
    # Asked in English, because the assertion below is on English words. The
    # catalogue's default is Italian (`app.i18n.DEFAULT_LANGUAGE`), so a call
    # with no language answers in Italian and this would test the catalogue's
    # default rather than the check.
    check = preflight.demo_data_check("numismatics", lang="en")
    assert check.ok is False
    assert "does not exist" in check.detail
    # The action has to be runnable as written, including the --out that puts
    # the pack where Banco reads it rather than where the config defaults to.
    assert "generate.py --settore numismatica" in check.action
    assert "--out" in check.action


def test_the_records_pseudo_path_resolves_to_this_sector_s_folder(pack):
    """`RECORDS/` is not a folder name - it means sectors[].data.records_dir."""
    build(pack, COMPLETE)
    for item in (pack / "lotti").iterdir():
        item.unlink()
    (pack / "lotti").rmdir()

    missing = preflight.demo_data("numismatics")["demos"]["m4"]["missing"]
    paths = [m["path"] for m in missing]
    assert "lotti/" in paths, paths
    assert "RECORDS/" not in paths, "the pseudo-path leaked into the report"


def test_trainer_only_material_is_still_required_and_marked(pack):
    """D4 beat 8 is a verification the room performs; it needs the answers."""
    build(pack, COMPLETE)
    (pack / "_perito" / "ground-truth.csv").unlink()

    missing = preflight.demo_data("numismatics")["demos"]["m4"]["missing"]
    entry = next(m for m in missing if m["path"] == "_perito/ground-truth.csv")
    assert entry["trainer"] is True


def test_a_missing_directory_is_caught_as_well_as_a_missing_file(pack):
    build(pack, COMPLETE)
    (pack / "regole" / "regolamento-catalogazione.md").unlink()
    (pack / "regole").rmdir()
    assert "regole/" in [m["path"] for m in
                         preflight.demo_data("numismatics")["demos"]["m3"]["missing"]]


def test_every_demo_is_reported_not_only_the_executable_ones(pack):
    """A sector pack is complete or it is not, whatever Banco can run today."""
    build(pack, COMPLETE)
    reported = set(preflight.demo_data("numismatics")["demos"])
    declared = {d["id"] for d in demos.load()["demos"]}
    assert reported == declared


def test_chain_inputs_of_later_demos_are_checked(pack):
    """D4 consumes D1's and D3's output; both are material it needs present."""
    build(pack, COMPLETE)
    (pack / "demo" / "catena" / "d1-bozze.md").unlink()
    missing = {m["path"] for m in preflight.demo_data("numismatics")["demos"]["m4"]["missing"]}
    assert "demo/catena/d1-bozze.md" in missing


def test_an_unknown_sector_is_reported_not_raised(pack):
    state = preflight.demo_data("no-such-sector")
    assert state["unknown_sector"] is True
    assert state["ok"] is False


def test_the_overview_covers_every_sector_the_database_declares(pack):
    build(pack, COMPLETE)
    overview = preflight.sectors_overview()
    assert {s["id"] for s in overview} == {s["id"] for s in demos.load()["sectors"]}
    numis = next(s for s in overview if s["id"] == "numismatics")
    assert numis["ready"] is True
    # A sector with no pack is listed and marked, never dropped from the picker.
    unready = [s for s in overview if not s["ready"]]
    assert unready and all(s["missing_demos"] for s in unready)
