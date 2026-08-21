"""Tool-layer behaviour: request validation, the error contract, and mode-blindness."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from towerwatch_ops_agent.domain.fixture_client import FixtureClient, _encode_page_token
from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup, build_site_enum
from towerwatch_ops_agent.tools import query_metrics as query_metrics_module
from towerwatch_ops_agent.tools.query_metrics import (
    _error_response,
    build_request_model,
    query_metrics,
)

SRC = Path(query_metrics_module.__file__)


@pytest.fixture
def request_model(fixture_client: FixtureClient):
    return build_request_model(build_site_enum(fixture_client.sites))


def _call(request_model, fixture_client: FixtureClient, **overrides):
    params = {
        "site": "standstill",
        "metric_group": MetricGroup.latency,
        "start": "2026-07-14T00:00:00-07:00",
        "end": "2026-07-14T01:00:00-07:00",
    }
    params.update(overrides)
    return query_metrics(request_model(**params), client=fixture_client, mode="fixture")


def test_ok_response_carries_series(request_model, fixture_client: FixtureClient) -> None:
    response = _call(request_model, fixture_client)
    assert response.data_status is DataStatus.ok
    assert set(response.series) == {"rtt_avg_google", "pkt_loss_google"}
    assert response.error is None


def test_not_collected_surfaces_through_the_tool(
    request_model, fixture_client: FixtureClient
) -> None:
    response = _call(request_model, fixture_client, site="home", metric_group=MetricGroup.signal)
    assert response.data_status is DataStatus.not_collected
    assert response.series == {}


def test_empty_window_surfaces_through_the_tool(
    request_model, fixture_client: FixtureClient
) -> None:
    response = _call(
        request_model,
        fixture_client,
        start="2026-07-14T02:00:00-07:00",
        end="2026-07-14T03:00:00-07:00",
    )
    assert response.data_status is DataStatus.empty_window
    assert response.series == {}


def test_request_rejects_end_before_start(request_model) -> None:
    with pytest.raises(ValidationError):
        request_model(
            site="standstill",
            metric_group=MetricGroup.latency,
            start="2026-07-14T02:00:00-07:00",
            end="2026-07-14T01:00:00-07:00",
        )


def test_request_rejects_unknown_site(request_model) -> None:
    """The site enum is derived from configured sites; anything else fails at the schema."""
    with pytest.raises(ValidationError):
        request_model(
            site="atlantis",
            metric_group=MetricGroup.latency,
            start="2026-07-14T00:00:00-07:00",
            end="2026-07-14T01:00:00-07:00",
        )


def test_request_rejects_malformed_step(request_model) -> None:
    with pytest.raises(ValidationError):
        request_model(
            site="standstill",
            metric_group=MetricGroup.latency,
            start="2026-07-14T00:00:00-07:00",
            end="2026-07-14T01:00:00-07:00",
            step="fifteen minutes",
        )


def test_unknown_metric_returns_actionable_retryable_error(
    request_model, fixture_client: FixtureClient
) -> None:
    response = _call(request_model, fixture_client, metrics=["rtt_avg_bogus"])
    assert response.data_status is DataStatus.error
    assert response.error is not None
    assert response.error.error_type == "unknown_metric"
    assert response.error.retryable is True
    assert "rtt_avg_google" in (response.error.suggested_next_call or "")


def test_future_window_is_an_invalid_request(request_model, fixture_client: FixtureClient) -> None:
    """fixture_now is 2026-07-14T08:00; a window past it cannot be satisfied."""
    response = _call(
        request_model,
        fixture_client,
        start="2026-07-20T00:00:00-07:00",
        end="2026-07-20T01:00:00-07:00",
    )
    assert response.data_status is DataStatus.error
    assert response.error is not None
    assert response.error.error_type == "invalid_request"


def test_tool_module_imports_no_concrete_client() -> None:
    """Structural proof that no tool learns which mode it is in (ADR-0002).

    Parses the module's imports rather than trusting convention. A tool that imported
    FixtureClient could branch on mode, and the dual-mode guarantee would be a comment
    instead of a property.
    """
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)

    forbidden = ("fixture_client", "grafana_cloud_client", "fixture_manifest")
    offenders = [name for name in imported if any(bad in name for bad in forbidden)]
    assert offenders == [], f"query_metrics imports a concrete data client: {offenders}"


def test_tool_def_description_teaches_the_absence_distinction() -> None:
    """The def is a prompt. If it doesn't teach not_collected, the model will misread it."""
    description = query_metrics_module.TOOL_DESCRIPTION
    assert "not_collected" in description
    assert "empty_window" in description
    assert "analyze_window" in description


def test_pagination_round_trips_through_the_tool(
    request_model, fixture_client: FixtureClient
) -> None:
    first = _call(request_model, fixture_client, step="10m", page_size=4)
    assert first.truncated
    assert first.next_page_token is not None

    second = _call(
        request_model,
        fixture_client,
        step="10m",
        page_size=4,
        page_token=first.next_page_token,
    )
    assert not second.truncated
    assert len(second.series["rtt_avg_google"]) == 2


def test_malformed_page_token_is_actionable(request_model, fixture_client: FixtureClient) -> None:
    response = _call(request_model, fixture_client, page_token="not-a-real-token")
    assert response.data_status is DataStatus.error
    assert response.error is not None
    assert response.error.retryable is True


def test_response_timestamps_keep_their_offset(
    request_model, fixture_client: FixtureClient
) -> None:
    """ISO-8601 with explicit offset, per conventions — never naive datetimes."""
    response = _call(request_model, fixture_client)
    first = response.series["rtt_avg_google"][0]
    assert first.ts.tzinfo is not None
    assert first.ts == datetime.fromisoformat("2026-07-14T00:00:00-07:00")


def test_internal_errors_do_not_leak_server_internals_to_the_model(
    fixture_client: FixtureClient,
) -> None:
    """Regression: the envelope interpolated the raw exception into `message`.

    `str(exc)` on an arbitrary failure carries whatever the raising code put there — a
    FileNotFoundError names the server's filesystem path. That message goes into the
    tool result the model reads, so it violated the binding invariant directly. The
    class survives (a model needs to know retrying will not help); the details do not.
    """
    leaky = FileNotFoundError(
        2, "No such file or directory", "/nonexistent/secret-internal-dir/creds.json"
    )
    response = _error_response(leaky)

    assert "secret-internal-dir" in str(leaky)  # the message really did carry the path
    assert response.error is not None
    assert response.error.error_type == "internal_error"
    assert response.error.retryable is False
    assert "secret-internal-dir" not in response.error.message
    assert "creds.json" not in response.error.message
    assert "FileNotFoundError" in response.error.message


def test_a_stale_page_token_is_told_to_drop_the_token(
    request_model, fixture_client: FixtureClient
) -> None:
    """Regression: it was told to "correct the window or step", which would not help.

    The error contract exists so a miss is self-correcting in one turn. Advice that
    contradicts the message beside it costs the model a turn and may cost it several.
    """
    response = _call(
        request_model,
        fixture_client,
        step="10m",
        page_size=4,
        page_token=_encode_page_token(9999),
    )

    assert response.data_status is DataStatus.error
    assert response.error is not None
    assert response.error.retryable is True
    next_call = response.error.suggested_next_call or ""
    assert "page_token" in next_call
    assert "window" not in next_call


def test_every_request_field_documents_an_example(fixture_client: FixtureClient) -> None:
    """A Phase 1 acceptance criterion: constraints and an example in every input field.

    Asserted rather than eyeballed, because a new field added without one is exactly
    the kind of omission a reviewer skims past.
    """
    model = build_request_model(build_site_enum(fixture_client.sites))
    missing = [
        name
        for name, field in model.model_fields.items()
        if "example" not in (field.description or "").lower()
    ]
    assert not missing, f"Request fields with no example: {missing}"
