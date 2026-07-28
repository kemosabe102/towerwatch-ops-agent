"""The data-access seam (ADR-0002).

`GrafanaCloudClient` (live) and `FixtureClient` (curated) satisfy this Protocol.
No tool may import either concrete class — tools depend on `DataClient` only, which
is what keeps a tool from learning which mode it is running in. A test in
`tests/tools/test_query_metrics.py` asserts this structurally rather than by convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup


class UnknownMetricError(ValueError):
    """A requested metric name is not in the group.

    Lives beside the Protocol, not in one implementation: every `DataClient` raises it,
    and the tool layer must be able to catch it without importing a concrete client.
    Carries the group's valid names so a miss is self-correcting in one turn rather
    than a dead end (`00-contract-conventions.md`, error contract).
    """

    def __init__(self, *, metric_group: MetricGroup, unknown: list[str], valid: list[str]) -> None:
        self.metric_group = metric_group
        self.unknown = unknown
        self.valid = valid
        super().__init__(
            f"Unknown metric(s) {unknown} in group {metric_group.value!r}. Valid names: {valid}"
        )


@dataclass(frozen=True)
class SeriesPoint:
    """One sample. `value` is in the metric's native unit — units live in metric names."""

    ts: datetime
    value: float


@dataclass(frozen=True)
class MetricSeriesResult:
    """One `metric_group`'s answer for one query — mode-agnostic by construction.

    Carries `data_status` rather than letting the caller infer it from an empty
    `metrics` dict: empty-because-not-collected and empty-because-nothing-in-range
    are different answers, and only the client can tell them apart.
    """

    metrics: dict[str, list[SeriesPoint]]
    data_status: DataStatus
    coverage_notes: list[str] = field(default_factory=list)
    truncated: bool = False
    next_page_token: str | None = None


@runtime_checkable
class DataClient(Protocol):
    """Read access to metric series, plus the clock.

    The Protocol grows one method per tool as tools are built, rather than being
    speculatively drafted for all seven now — the group-to-layer mapping the later
    tools need does not exist yet.
    """

    def get_metric_series(
        self,
        *,
        site: str,
        metric_group: MetricGroup,
        metrics: list[str] | None,
        start: datetime,
        end: datetime,
        step: str | None,
        page_size: int,
        page_token: str | None,
    ) -> MetricSeriesResult:
        """Return one group's series for a window, already downsampled and paged."""
        ...

    def now(self) -> datetime:
        """Resolve "now" — system clock live, frozen `fixture_now` in fixture mode.

        On the DataClient rather than a separate injected Clock so there is exactly
        one seam per mode instead of two. `00-contract-conventions.md` requires that
        this never be a tool parameter and that both modes run the same resolution
        path, so fixture mode cannot skip the most-used production behavior.
        """
        ...
