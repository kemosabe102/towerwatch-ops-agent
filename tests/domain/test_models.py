"""The shared vocabulary, and the schema-cleanliness guard.

The docstring/def-token test here is the structural half of a decision: maintainer
rationale for `MetricGroup` and `DataStatus` lives in comments rather than docstrings
so Pydantic cannot copy it into the tool schema. Without this test that is a convention
someone breaks by writing the obvious thing; with it, breaking it fails the build.
"""

from __future__ import annotations

import json

import pytest

from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup, build_site_enum


def test_enum_values_serialize_as_plain_strings() -> None:
    """StrEnum, not `str, Enum`: f-string interpolation must not leak the class name.

    Under `class X(str, Enum)` on Python 3.11+, `f"{X.member}"` renders
    'X.member' while `json.dumps` renders 'member' — so a span attribute built with an
    f-string and a JSON body built from the same value would disagree. StrEnum makes
    both render the bare value, which removes the trap instead of documenting it.
    """
    assert f"{MetricGroup.latency}" == "latency"
    assert str(DataStatus.not_collected) == "not_collected"
    assert json.dumps({"g": MetricGroup.latency}) == '{"g": "latency"}'
    assert MetricGroup.latency == "latency"


def test_enum_docstrings_stay_out_of_the_schema() -> None:
    """Maintainer notes must not reach the model — they are def-token spend.

    Asserted at the source rather than through a rendered tool schema: Pydantic copies
    `__doc__` verbatim into the JSON Schema, so an absent docstring is the property
    that matters, and checking it here keeps this test runnable in the layer that owns
    the decision. `MetricGroup`'s rationale runs ~750 characters — as a docstring it
    was 29% of the rendered request schema, spent telling a future code author not to
    refactor.
    """
    for enum_cls in (MetricGroup, DataStatus):
        doc = enum_cls.__doc__ or ""
        # Enum supplies a stock docstring when the class defines none; anything longer
        # is prose someone wrote, and prose here is prose the model pays for.
        assert len(doc) < 120, (
            f"{enum_cls.__name__} has a docstring ({len(doc)} chars). Pydantic will "
            "copy it into the tool schema — put maintainer rationale in a comment."
        )
        assert "ADR-" not in doc
        assert "Do not" not in doc


def test_enum_values_are_the_whole_schema_contribution() -> None:
    """What the model *does* receive is the value list, and nothing else."""
    assert json.dumps([m.value for m in MetricGroup]) == json.dumps(
        [
            "latency",
            "throughput",
            "dns",
            "tcp",
            "gateway",
            "speedtest",
            "bufferbloat",
            "signal",
            "cell_identity",
            "hardware",
            "meta",
        ]
    )


def test_data_status_values_match_the_contract() -> None:
    """Pinned against `00-contract-conventions.md`; a rename is a contract change."""
    assert {s.value for s in DataStatus} == {
        "ok",
        "empty_window",
        "not_collected",
        "partial",
        "error",
    }


def test_site_enum_is_built_from_the_given_names() -> None:
    site = build_site_enum(["standstill", "home"])
    assert [m.value for m in site] == ["standstill", "home"]


def test_site_enum_accepts_names_that_are_not_python_identifiers() -> None:
    """Site names come from committed fixture data, not from code.

    A hyphen or a space is a plausible real-world site label, and nothing looks these
    up attribute-style — Pydantic validates by value. Pinned so nobody "hardens" this
    into an identifier-only check and rejects valid config.
    """
    site = build_site_enum(["3rd-floor", "my site"])
    assert [m.value for m in site] == ["3rd-floor", "my site"]


def test_empty_site_list_refuses_to_build() -> None:
    """Louder than logging: an empty site enum makes every tool call unanswerable."""
    with pytest.raises(ValueError, match="No sites configured"):
        build_site_enum([])
