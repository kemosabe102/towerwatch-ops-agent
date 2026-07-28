"""`FixtureClient` — the curated-corpus half of the dual-mode seam (ADR-0002).

Authoritative for tests and evals, because determinism is what makes an eval result
mean anything. Reads a committed manifest; never touches the network.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

from towerwatch_ops_agent.domain.fixture_manifest import (
    FixtureManifest,
    FixtureWindow,
    load_series,
)
from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup
from towerwatch_ops_agent.domain.protocol import (
    MetricSeriesResult,
    SeriesPoint,
    UnknownMetricError,
)
from towerwatch_ops_agent.domain.windows import (
    default_step,
    downsample,
    parse_step,
)


def _encode_page_token(offset: int) -> str:
    """Opaque to the caller by construction, so paging internals stay changeable."""
    return base64.urlsafe_b64encode(json.dumps({"offset": offset}).encode()).decode()


def _decode_page_token(token: str) -> int:
    try:
        payload = json.loads(base64.urlsafe_b64decode(token.encode()).decode())
        offset = int(payload["offset"])
    except Exception as exc:
        raise ValueError(f"Malformed page_token: {token!r}") from exc
    if offset < 0:
        raise ValueError(f"Malformed page_token: negative offset {offset}")
    return offset


class FixtureClient:
    """Satisfies `DataClient` against a committed fixture corpus."""

    def __init__(self, manifest_path: Path) -> None:
        self._manifest_path = Path(manifest_path)
        self._manifest = FixtureManifest.load(self._manifest_path)
        # Frozen for the process lifetime. A clock that drifts mid-session would make
        # two identical eval runs disagree, which is the whole thing the fixture exists
        # to prevent.
        self._now = self._manifest.fixture_now
        self._series_cache: dict[str, dict[str, list[SeriesPoint]]] = {}

    @property
    def manifest(self) -> FixtureManifest:
        return self._manifest

    @property
    def sites(self) -> list[str]:
        return self._manifest.sites

    def now(self) -> datetime:
        """The frozen `fixture_now` from the manifest — never the system clock."""
        return self._now

    def _windows_for_site(self, site: str) -> list[FixtureWindow]:
        return [window for window in self._manifest.windows if window.site == site]

    def _load_window_series(self, window: FixtureWindow) -> dict[str, list[SeriesPoint]]:
        if window.payload is None:
            return {}
        if window.id not in self._series_cache:
            payload_path = self._manifest_path.parent / window.payload
            self._series_cache[window.id] = load_series(payload_path)
        return self._series_cache[window.id]

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
        windows = self._windows_for_site(site)
        if not windows:
            return MetricSeriesResult(
                metrics={},
                data_status=DataStatus.not_collected,
                coverage_notes=[f"No fixture windows exist for site {site!r}."],
            )

        # Absence is checked before any payload read — the reason is documented data,
        # not an inference from an empty result. This is the load-bearing branch:
        # `not_collected` means no evidence, and must never look like `empty_window`.
        for window in windows:
            reason = window.absent_reason(metric_group)
            if reason is not None:
                return MetricSeriesResult(
                    metrics={},
                    data_status=DataStatus.not_collected,
                    coverage_notes=[
                        (
                            f"Site {site!r} does not collect metric group "
                            f"{metric_group.value!r} ({reason}). No evidence — "
                            f"absence here is not a healthy reading."
                        )
                    ],
                )

        collecting = [w for w in windows if metric_group in w.groups_present]
        if not collecting:
            return MetricSeriesResult(
                metrics={},
                data_status=DataStatus.not_collected,
                coverage_notes=[
                    (
                        f"Metric group {metric_group.value!r} is not present in the fixture "
                        f"for site {site!r}, and no reason is recorded for its absence."
                    )
                ],
            )

        # Collected here — so an empty result from this point on is a true negative.
        collected: dict[str, list[SeriesPoint]] = {}
        for window in collecting:
            for name, points in self._load_window_series(window).items():
                collected.setdefault(name, []).extend(
                    point for point in points if start <= point.ts < end
                )

        coverage_notes: list[str] = []
        if metrics is not None:
            known = set(collected)
            unknown = [name for name in metrics if name not in known]
            if unknown:
                raise UnknownMetricError(metric_group=metric_group, unknown=unknown, valid=sorted(known))
            collected = {name: collected[name] for name in metrics}

        step_value = step or default_step(start, end)
        step_delta = parse_step(step_value)
        downsampled = {
            name: downsample(points, step=step_delta, origin=start)
            for name, points in collected.items()
        }

        if not any(downsampled.values()):
            return MetricSeriesResult(
                metrics={},
                data_status=DataStatus.empty_window,
                coverage_notes=[
                    (
                        f"Site {site!r} collects {metric_group.value!r}, but no samples fall "
                        f"in {start.isoformat()}..{end.isoformat()}. This is a true negative."
                    )
                ],
            )

        offset = _decode_page_token(page_token) if page_token else 0
        paged, truncated, next_token = _paginate(downsampled, offset=offset, page_size=page_size)
        if truncated:
            coverage_notes.append(
                f"Truncated at {page_size} points per metric; pass next_page_token to continue."
            )

        return MetricSeriesResult(
            metrics=paged,
            data_status=DataStatus.ok,
            coverage_notes=coverage_notes,
            truncated=truncated,
            next_page_token=next_token,
        )


def _paginate(
    series: dict[str, list[SeriesPoint]], *, offset: int, page_size: int
) -> tuple[dict[str, list[SeriesPoint]], bool, str | None]:
    """Page uniformly across metrics: each metric yields the same index range.

    Keeps metrics time-aligned within a page, so a caller comparing two series in one
    response is comparing the same interval rather than two different offsets.
    """
    longest = max((len(points) for points in series.values()), default=0)
    paged = {name: points[offset : offset + page_size] for name, points in series.items()}
    truncated = offset + page_size < longest
    next_token = _encode_page_token(offset + page_size) if truncated else None
    return paged, truncated, next_token
