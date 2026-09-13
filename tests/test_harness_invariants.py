"""What the projected surface must never render.

PROJECT.md invariant 1 and AGENTS.md rule 2: no API key, no client name, no
ground-truth file, no trainer note reaches the harness. These are checked
against every demo and every sector, because the repository serves several
clients from one demo database and the one that matters is always the sector
nobody is currently looking at.
"""

from __future__ import annotations

import json

import pytest

from app.server import demos


def _sector_ids() -> list[str]:
    return [s["id"] for s in demos.load().get("sectors", [])]


def _demo_ids() -> list[str]:
    return [d["id"] for d in demos.load().get("demos", [])]


def test_no_resolved_demo_contains_any_sector_client_name():
    """A client name must not appear for its own sector or for any other."""
    names = [
        (s["id"], (s.get("client", {}).get("name") or "").strip())
        for s in demos.load().get("sectors", [])
    ]
    named = [(sid, n) for sid, n in names if n]
    if not named:
        pytest.skip("no sector declares a client name")

    for demo_id in _demo_ids():
        for sector in _sector_ids():
            blob = json.dumps(demos.resolve_demo(demo_id, sector), ensure_ascii=False)
            for owner, name in named:
                assert name not in blob, (
                    f"{demo_id}/{sector} renders the client name of {owner}: {name!r}"
                )


# A name no client has. The guards below must be exercised whatever the database
# happens to declare, so they are tested against this rather than against a real
# sector's `client.name`.
FAKE_CLIENT = {"name": "Acme Fittizia S.r.l.", "sector": "test sector"}


def test_no_sector_declares_a_client_name():
    """The demo database is client-agnostic. Names live in `engagements/`.

    The `client` block IS the substitution map, so a name written here reaches
    the projected surface and is inlined into the deck's published
    `index.html`. One sat there from the first delivery until 2026-09-12. See
    `theory-deck/PROMPTS.md`.
    """
    named = [
        s["id"] for s in demos.load().get("sectors", [])
        if (s.get("client", {}).get("name") or "").strip()
    ]
    assert not named, f"sectors declaring a client name: {named}"


def test_client_name_is_not_substitutable():
    """`{{name}}` must not expand, so a future prompt cannot leak it."""
    assert "name" in demos.CONFIDENTIAL_CLIENT_FIELDS
    substituted = demos._substitute(
        "{{name}} and {{sector}}",
        {k: v for k, v in FAKE_CLIENT.items()
         if k not in demos.CONFIDENTIAL_CLIENT_FIELDS},
    )
    assert "{{name}}" in substituted, "the client name was substituted in"
    assert "{{sector}}" not in substituted, "ordinary placeholders must still work"


def test_resolution_refuses_content_carrying_the_client_name():
    """The guard must fire on a name written straight into a prompt.

    Against a synthetic client, not against whatever the database declares.
    The previous version of this test skipped itself once every sector shipped
    `name: ""` — which left the guard untested at exactly the moment the
    database stopped protecting itself.
    """
    name = FAKE_CLIENT["name"]
    with pytest.raises(ValueError, match="invariant 1"):
        demos._assert_no_client_name({"text": f"a draft for {name}"}, FAKE_CLIENT)


def test_an_empty_client_name_does_not_match_everything():
    """`name: ""` must be a no-op, not a substring that refuses every demo."""
    demos._assert_no_client_name({"text": "anything at all"}, {"name": ""})
    demos._assert_no_client_name({"text": "anything at all"}, {"name": "   "})
    demos._assert_no_client_name({"text": "anything at all"}, {})


def test_no_resolved_demo_contains_a_trainer_field():
    for demo_id in _demo_ids():
        for sector in _sector_ids():
            blob = json.dumps(demos.resolve_demo(demo_id, sector), ensure_ascii=False)
            for field in demos.TRAINER_FIELDS:
                assert f'"{field}"' not in blob, f"{demo_id}/{sector} leaks {field}"


def test_no_resolved_demo_offers_a_trainer_only_file():
    """Files flagged `trainer: true` stay off the projected download rail."""
    for demo_id in _demo_ids():
        for sector in _sector_ids():
            resolved = demos.resolve_demo(demo_id, sector)
            for entry in resolved.get("files", []):
                assert not (isinstance(entry, dict) and entry.get("trainer"))


def test_ground_truth_and_trainer_readmes_never_reach_the_harness():
    forbidden = ("ground-truth", "LEGGIMI")
    for demo_id in _demo_ids():
        for sector in _sector_ids():
            blob = json.dumps(demos.resolve_demo(demo_id, sector), ensure_ascii=False)
            for token in forbidden:
                assert token not in blob, f"{demo_id}/{sector} references {token}"
