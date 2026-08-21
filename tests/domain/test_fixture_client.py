"""FixtureClient behaviour against the stub corpus.

The absence tests carry the most weight: `not_collected` and `empty_window` are the
distinction the whole contract is built on, so both are asserted by exact status value
rather than by "the result was empty".
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from towerwatch_ops_agent.domain.fixture_client import FixtureClient
from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup
from towerwatch_ops_agent.domain.protocol import UnknownMetricError


def _query(client: FixtureClient, **overrides):
    params = {
        "site": "standstill",
        "metric_group": MetricGroup.latency,
        "metrics": None,
        "start": datetime.fromisoformat("2026-07-14T00:00:00-07:00"),
        "end": datetime.fromisoformat("2026-07-14T01:00:00-07:00"),
        "step": None,
        "page_size": 500,
        "page_token": None,
    }
    params.update(overrides)
    return client.get_metric_series(**params)


def test_ok_returns_series_for_present_group(fixture_client: FixtureClient) -> None:
    result = _query(fixture_client)
    assert result.data_status is DataStatus.ok
    assert set(result.metrics) == {"rtt_avg_google", "pkt_loss_google"}
    assert len(result.metrics["rtt_avg_google"]) == 6
    assert not result.truncated


def test_not_collected_for_absent_group(fixture_client: FixtureClient) -> None:
    """home has no cellular modem — signal is absent for a physical reason."""
    result = _query(fixture_client, site="home", metric_group=MetricGroup.signal)
    assert result.data_status is DataStatus.not_collected
    assert result.metrics == {}
    note = " ".join(result.coverage_notes).lower()
    assert "signal" in note
    assert "no evidence" in note


def test_empty_window_for_out_of_range_query(fixture_client: FixtureClient) -> None:
    """Collected group, no samples in range — a true negative, not missing coverage."""
    result = _query(
        fixture_client,
        start=datetime.fromisoformat("2026-07-14T02:00:00-07:00"),
        end=datetime.fromisoformat("2026-07-14T03:00:00-07:00"),
    )
    assert result.data_status is DataStatus.empty_window
    assert result.metrics == {}


def test_not_collected_and_empty_window_are_distinct(fixture_client: FixtureClient) -> None:
    """The load-bearing distinction, asserted directly.

    Both return no data. Conflating them is the grounding failure the envelope exists
    to prevent, so this pins them as different values in one place.
    """
    absent = _query(fixture_client, site="home", metric_group=MetricGroup.signal)
    empty = _query(
        fixture_client,
        start=datetime.fromisoformat("2026-07-14T02:00:00-07:00"),
        end=datetime.fromisoformat("2026-07-14T03:00:00-07:00"),
    )
    assert absent.metrics == empty.metrics == {}
    assert absent.data_status is DataStatus.not_collected
    assert empty.data_status is DataStatus.empty_window
    assert absent.data_status is not empty.data_status


def test_downsample_aggregates_rather_than_taking_last_point(
    fixture_client: FixtureClient,
) -> None:
    """A 30m step over 6 points must average, not sample.

    The second bucket holds 47, 44, 131. Last-point-in-bucket yields 131 and hides the
    two low samples; the mean is ~74. Asserting the mean catches an implementer who
    silently drops data.
    """
    result = _query(fixture_client, step="30m")
    rtt = result.metrics["rtt_avg_google"]
    assert len(rtt) == 2
    assert rtt[0].value == pytest.approx((101 + 99 + 80) / 3)
    assert rtt[1].value == pytest.approx((47 + 44 + 131) / 3)
    assert rtt[1].value != 131.0


def test_downsample_buckets_anchor_to_window_start(fixture_client: FixtureClient) -> None:
    """Stable bucket boundaries — eval stability depends on identical requests agreeing."""
    result = _query(fixture_client, step="30m")
    rtt = result.metrics["rtt_avg_google"]
    assert rtt[0].ts == datetime.fromisoformat("2026-07-14T00:00:00-07:00")
    assert rtt[1].ts == datetime.fromisoformat("2026-07-14T00:30:00-07:00")


def test_pagination_returns_token_and_resumes(fixture_client: FixtureClient) -> None:
    first = _query(fixture_client, step="10m", page_size=4)
    assert first.truncated
    assert first.next_page_token is not None
    assert len(first.metrics["rtt_avg_google"]) == 4

    second = _query(fixture_client, step="10m", page_size=4, page_token=first.next_page_token)
    assert not second.truncated
    assert second.next_page_token is None
    assert len(second.metrics["rtt_avg_google"]) == 2
    assert second.metrics["rtt_avg_google"][0].ts > first.metrics["rtt_avg_google"][-1].ts


def test_pagination_keeps_metrics_time_aligned(fixture_client: FixtureClient) -> None:
    """Both metrics advance together, so a page compares the same interval."""
    page = _query(fixture_client, step="10m", page_size=3)
    rtt = page.metrics["rtt_avg_google"]
    loss = page.metrics["pkt_loss_google"]
    assert [p.ts for p in rtt] == [p.ts for p in loss]


def test_metrics_narrowing(fixture_client: FixtureClient) -> None:
    result = _query(fixture_client, metrics=["rtt_avg_google"])
    assert set(result.metrics) == {"rtt_avg_google"}


def test_unknown_metric_names_carry_the_valid_list(fixture_client: FixtureClient) -> None:
    """A miss must be self-correcting in one turn, not a dead end."""
    with pytest.raises(UnknownMetricError) as excinfo:
        _query(fixture_client, metrics=["rtt_avg_bogus"])
    assert excinfo.value.unknown == ["rtt_avg_bogus"]
    assert "rtt_avg_google" in excinfo.value.valid


def test_unknown_site_is_not_collected(fixture_client: FixtureClient) -> None:
    result = _query(fixture_client, site="nowhere")
    assert result.data_status is DataStatus.not_collected


def test_now_returns_frozen_fixture_now(fixture_client: FixtureClient) -> None:
    """The clock seam reads the manifest, never the system clock."""
    assert fixture_client.now() == datetime.fromisoformat("2026-07-14T08:00:00-07:00")
    assert fixture_client.now() == fixture_client.manifest.fixture_now


def test_now_is_stable_across_calls(fixture_client: FixtureClient) -> None:
    """A clock that drifted mid-session would make two identical eval runs disagree."""
    first = fixture_client.now()
    second = fixture_client.now()
    assert first == second
    assert abs(first - datetime.now(tz=first.tzinfo)) > timedelta(days=1)


def test_sites_are_derived_from_the_corpus(fixture_client: FixtureClient) -> None:
    assert set(fixture_client.sites) == {"standstill", "home"}
