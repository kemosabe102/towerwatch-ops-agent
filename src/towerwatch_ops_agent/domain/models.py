"""Shared domain vocabulary: metric groups, data status, and the site enum.

Two enums here are built differently on purpose. See `MetricGroup` below.
"""

from __future__ import annotations

from enum import Enum, StrEnum


# The vocabulary surface for `query_metrics` — 11 groups standing in for 74 metrics.
#
# Deliberately hardcoded, unlike `Site` (built at startup) and the runbook `section`
# enum (parsed from headings). ADR-0007 names `section`, `site`, and `event_types` as
# the derived enums; `metric_group` is not one of them, and the reason is structural:
# TowerWatch's `docs/metrics-inventory.md` has ten section headings that do not map
# one-to-one onto these eleven values — `signal`, `cell_identity`, and `hardware` are
# all carved out of its single "Cellular radio" section. The split is an editorial
# judgment about what an agent should be able to ask for, so there is no source to
# derive it from. Do not "fix" this into symmetry with `Site`.
#
# Deliberately a comment, not a docstring: Pydantic copies a class docstring verbatim
# into the JSON Schema, so a docstring here would ship this maintainer note to the
# model on every call — 29% of the request schema spent telling a future *code author*
# not to refactor. `test_enum_docstrings_stay_out_of_the_schema` pins that.
class MetricGroup(StrEnum):
    latency = "latency"
    throughput = "throughput"
    dns = "dns"
    tcp = "tcp"
    gateway = "gateway"
    speedtest = "speedtest"
    bufferbloat = "bufferbloat"
    signal = "signal"
    cell_identity = "cell_identity"
    hardware = "hardware"
    meta = "meta"


# The response envelope's absence-discriminator (`00-contract-conventions.md`).
#
# `not_collected` vs `empty_window` is the load-bearing distinction in the whole
# contract: one is a true negative, the other is no evidence at all. A model that
# reads `not_collected` as health has made the grounding failure this enum exists
# to prevent.
#
# A comment rather than a docstring for the same reason as `MetricGroup` above: the
# model is taught these semantics by the `data_status` field description in
# `query_metrics.py`, which is written for it. This note is for maintainers.
class DataStatus(StrEnum):
    ok = "ok"
    empty_window = "empty_window"
    not_collected = "not_collected"
    partial = "partial"
    error = "error"


def build_site_enum(names: list[str]) -> type[Enum]:
    """Build the `site` enum at startup from configured sites (ADR-0007).

    Derived rather than hardcoded so a new site appears in the tool schema on next
    server start, with no code change. The failure mode of the hardcoded version is
    silence: the def keeps advertising the stale list and the model never learns the
    new site exists.

    Raises on an empty list — a zero-value enum would present as "no sites exist"
    rather than "the config failed to parse". This is the same concern ADR-0007 raises
    for the runbook (log derived enum sizes so a silent zero-section parse is visible),
    applied to sites with a louder mechanism: refusing to boot rather than logging,
    because an empty site enum makes every subsequent tool call unanswerable.
    """
    if not names:
        raise ValueError(
            "No sites configured — refusing to build an empty site enum. "
            "An empty enum is indistinguishable from a broken config at the tool surface."
        )
    return StrEnum("Site", {name: name for name in names})  # type: ignore[return-value]
