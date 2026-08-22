"""`towerwatch_query_metrics` — raw, paginated time-series access.

Contract: `docs/design/01-query_metrics.md`. Returns numbers for the model to reason
over; performs no interpretation. Def-token target: 220.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup
from towerwatch_ops_agent.domain.protocol import DataClient, UnknownMetricError
from towerwatch_ops_agent.domain.windows import resolve_window
from towerwatch_ops_agent.telemetry.spans import tool_span

logger = logging.getLogger(__name__)

TOOL_NAME = "towerwatch_query_metrics"

TOOL_DESCRIPTION = """\
Raw time-series data points from TowerWatch network monitoring.

Pick this when you need the actual numbers — specific values, series, timestamps — and \
you will do your own reasoning over them. If you want a judgment about a window \
(is it degraded, and against what reference), use analyze_window instead.

Returns downsampled [timestamp, value] pairs per metric, plus data_status. Read \
data_status before the numbers: 'empty_window' means collected here with nothing in \
range (a true negative), while 'not_collected' means this site never collects it — no \
evidence, so do not infer that anything is healthy."""


class SeriesPointOut(BaseModel):
    ts: datetime = Field(description="Sample timestamp, ISO-8601 with offset.")
    value: float = Field(description="Value in the metric's native unit. Example: 47.3")


class QueryMetricsResponse(BaseModel):
    """The response envelope. `data_status` is mandatory on every tool response."""

    data_status: DataStatus = Field(
        description=(
            "ok=data present; empty_window=collected here, none in range (true "
            "negative); not_collected=site never collects this (NO evidence — do not "
            "infer health); partial=some groups missing; error=see message."
        )
    )
    series: dict[str, list[SeriesPointOut]] = Field(
        default_factory=dict,
        description="Metric name to its downsampled points. Empty unless data_status is ok.",
    )
    coverage_notes: list[str] = Field(
        default_factory=list,
        description="Why data is missing or partial, in plain language.",
    )
    truncated: bool = Field(
        default=False, description="True when more points exist beyond this page."
    )
    next_page_token: str | None = Field(
        default=None, description="Pass back as page_token to continue. Null when complete."
    )
    error: ToolError | None = Field(
        default=None, description="Present only when data_status is 'error'."
    )


class ToolError(BaseModel):
    """Actionable by contract: what went wrong, what to do next, whether to retry."""

    error_type: str = Field(description="Machine class. Example: 'unknown_metric'")
    message: str = Field(description="What went wrong and why.")
    suggested_next_call: str | None = Field(
        default=None, description="The concrete call that would work."
    )
    retryable: bool = Field(description="True when a corrected retry can succeed.")


QueryMetricsResponse.model_rebuild()


def build_request_model(site_enum: type[Enum]) -> type[BaseModel]:
    """Build the request model against the startup-derived site enum (ADR-0007).

    The site list cannot be a literal in this module: it comes from configured sites at
    startup, so a new site appears in the schema on next boot with no code change.
    """

    class QueryMetricsRequest(BaseModel):
        site: site_enum = Field(  # type: ignore[valid-type]
            description="Monitoring site to query. Example: 'standstill'"
        )
        metric_group: MetricGroup = Field(
            description=(
                "Metric family to query. One group per call. "
                "Example: 'latency' (rtt, jitter, packet loss)"
            )
        )
        metrics: list[str] | None = Field(
            default=None,
            description=(
                "Narrow to specific metric names in the group. Omit for all of them; "
                "a wrong name returns the group's valid list. Example: ['rtt_avg_google']"
            ),
        )
        start: datetime = Field(
            description="Window start, ISO-8601 with offset. Example: '2026-07-14T00:00:00-07:00'"
        )
        end: datetime = Field(
            description="Window end, ISO-8601 with offset. Example: '2026-07-14T06:00:00-07:00'"
        )
        step: str | None = Field(
            default=None,
            pattern=r"^\d+[smhd]$",
            description="Downsample interval; omit to scale with range. Example: '15m'",
        )
        page_size: int = Field(
            default=500,
            ge=1,
            le=5000,
            description="Max points per metric per page. Example: 500",
        )
        page_token: str | None = Field(
            default=None,
            description=(
                "Continuation token from a truncated response; omit on a first call. "
                "Example: the next_page_token value returned by the previous call"
            ),
        )

        @model_validator(mode="after")
        def _end_after_start(self) -> QueryMetricsRequest:
            if self.end <= self.start:
                raise ValueError("end must be after start")
            return self

    return QueryMetricsRequest


def query_metrics(request: Any, *, client: DataClient, mode: str) -> QueryMetricsResponse:
    """Execute one query against whichever `DataClient` is wired in.

    `client` is typed as the Protocol, never a concrete class — the tool cannot tell
    whether it is reading live data or the fixture, which is the property ADR-0002
    exists to preserve.
    """
    site_value = request.site.value if isinstance(request.site, Enum) else str(request.site)

    with tool_span(tool_name=TOOL_NAME, mode=mode, site=site_value) as metrics:
        metrics["input_bytes"] = len(request.model_dump_json())
        if request.page_token:
            metrics["page_index"] = 1

        try:
            # Both modes resolve "now" through the same seam and the same helper, so
            # fixture mode exercises the default path rather than bypassing it.
            start, end = resolve_window(request.start, request.end, now=client.now())
            result = client.get_metric_series(
                site=site_value,
                metric_group=request.metric_group,
                metrics=request.metrics,
                start=start,
                end=end,
                step=request.step,
                page_size=request.page_size,
                page_token=request.page_token,
            )
        # Deliberately broad: the error contract says a tool returns an actionable
        # error envelope, so no failure may escape as an exception and take the
        # session down. `_error_response` maps known classes and labels the rest
        # `internal_error, retryable: false`.
        except Exception as exc:  # noqa: BLE001
            response = _error_response(exc)
        else:
            # Response construction is inside the guard, not in an `else:`. Validating
            # the client's points is itself a failure point — `SeriesPoint` is a plain
            # dataclass with no validation, so a `DataClient` may hand back a sample
            # Pydantic rejects. `FixtureClient` coerces with float() at load and cannot
            # trip this; ADR-0002's `GrafanaCloudClient` reads a live API, which is
            # exactly where a malformed sample comes from. Left in an `else:` that
            # failure escaped as a bare ValidationError with no envelope at all.
            try:
                response = QueryMetricsResponse(
                    data_status=result.data_status,
                    series={
                        name: [SeriesPointOut(ts=p.ts, value=p.value) for p in points]
                        for name, points in result.metrics.items()
                    },
                    coverage_notes=result.coverage_notes,
                    truncated=result.truncated,
                    next_page_token=result.next_page_token,
                )
            except ValidationError as exc:
                response = _malformed_series_response(exc)

        metrics["data_status"] = response.data_status.value
        metrics["output_bytes"] = len(response.model_dump_json())
        if response.error is not None:
            metrics["error_type"] = response.error.error_type
        return response


def _malformed_series_response(exc: ValidationError) -> QueryMetricsResponse:
    """The data client returned a sample this tool cannot represent.

    Server-side data quality, not a caller mistake — so `internal_error` and not
    retryable, and the validation detail goes to the operator's log rather than to the
    model, which can do nothing with it.
    """
    logger.error("DataClient returned a sample that failed validation: %s", exc)
    return QueryMetricsResponse(
        data_status=DataStatus.error,
        error=ToolError(
            error_type="internal_error",
            message=(
                "The data source returned a sample this tool could not read. "
                "This is not a problem with your request and retrying will not help."
            ),
            retryable=False,
        ),
    )


def _error_response(exc: Exception) -> QueryMetricsResponse:
    """Map an exception to the actionable error contract."""
    if isinstance(exc, UnknownMetricError):
        error = ToolError(
            error_type="unknown_metric",
            message=str(exc),
            suggested_next_call=(
                f"Retry with metrics from: {exc.valid}, or omit `metrics` for all of them."
            ),
            retryable=True,
        )
    elif isinstance(exc, ValueError):
        # The advice has to match the failure. A stale page_token is fixed by
        # dropping the token, not by "correcting the window or step" — a generic line
        # there actively contradicts the message beside it, and the error contract
        # exists so a miss is self-correcting in one turn.
        message = str(exc)
        if "page_token" in message:
            next_call = "Re-issue the same request with no page_token to start over."
        elif "step" in message:
            next_call = "Retry with a step like '60s', '15m', '1h', or omit it entirely."
        else:
            next_call = (
                "Correct the window (start must be before end, and not in the future) and retry."
            )
        error = ToolError(
            error_type="invalid_request",
            message=message,
            suggested_next_call=next_call,
            retryable=True,
        )
    else:
        # The exception class, never its message. `str(exc)` on an arbitrary failure
        # carries whatever the raising code put there — a FileNotFoundError names the
        # server's filesystem path, and the binding invariant is that internals never
        # appear in a tool result. The class is enough for a model to know retrying
        # will not help; the details belong in the operator's logs and on the span's
        # `tool.error_type`.
        logger.exception("Unhandled error in %s", TOOL_NAME)
        error = ToolError(
            error_type="internal_error",
            message=(
                f"The server failed while handling this request ({type(exc).__name__}). "
                "This is not a problem with your request and retrying will not help."
            ),
            retryable=False,
        )
    return QueryMetricsResponse(data_status=DataStatus.error, error=error)
