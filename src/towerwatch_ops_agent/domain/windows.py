"""Window resolution and downsampling — the deterministic arithmetic layer.

Per `00-contract-conventions.md`, the server interprets only against enumerable
context. Bucketing and aggregation live here; nothing in this module makes a judgment
about what the numbers mean.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from towerwatch_ops_agent.domain.protocol import SeriesPoint

_STEP_PATTERN = re.compile(r"^(\d+)([smhd])$")
_STEP_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def parse_step(step: str) -> timedelta:
    """Parse a `step` value (`60s`, `15m`, `1h`, `1d`) into a timedelta."""
    match = _STEP_PATTERN.match(step)
    if not match:
        raise ValueError(f"Invalid step {step!r} — expected a form like '60s', '15m', '1h', '1d'.")
    amount, unit = int(match.group(1)), match.group(2)
    if amount <= 0:
        raise ValueError(f"Invalid step {step!r} — must be positive.")
    return timedelta(**{_STEP_UNITS[unit]: amount})


def resolve_window(start: datetime, end: datetime, *, now: datetime) -> tuple[datetime, datetime]:
    """Resolve a requested window against the injected clock.

    `now` comes from `DataClient.now()` — the system clock live, frozen `fixture_now`
    in fixture mode. Both modes call this same function, which is the point: a fixture
    that bypassed the default resolution path would leave the most-used production
    behavior untested (`00-contract-conventions.md`, the clock seam).

    Absolute ISO-8601 windows pass through unchanged, which is every window today.

    TODO(relative-window-grammar): `00-contract-conventions.md` refers to "any input
    that resolves against now", but no contract doc defines a relative syntax
    (`now-1h` or otherwise). Rather than invent one, this accepts absolute timestamps
    only and still routes them through the seam so the call site is real and tested.
    Define the grammar in the conventions doc before implementing it here.
    """
    if end <= start:
        raise ValueError("end must be after start")
    if start > now:
        raise ValueError(
            f"Window starts in the future: start={start.isoformat()} > now={now.isoformat()}"
        )
    return start, end


def default_step(start: datetime, end: datetime) -> str:
    """Pick a `step` when the caller omits one.

    A 2-week window at 60 s resolution is ~20k points per metric; never ship that
    (`01-query_metrics.md`). Targets a few hundred points per metric across the range.
    """
    span_s = (end - start).total_seconds()
    if span_s <= 3 * 3600:
        return "60s"
    if span_s <= 24 * 3600:
        return "5m"
    if span_s <= 7 * 24 * 3600:
        return "1h"
    return "1d"


def downsample(
    points: list[SeriesPoint], *, step: timedelta, origin: datetime
) -> list[SeriesPoint]:
    """Bucket points into fixed-width intervals and take the mean of each.

    Mean, not last-point-in-bucket: a bucket's last sample discards everything else in
    it, which silently erases exactly the spikes that matter on network data. Buckets
    are anchored to `origin` (the window start) so the same request always produces the
    same boundaries — eval stability depends on it.

    Each bucket is timestamped at its left edge.
    """
    if not points:
        return []
    buckets: dict[int, list[float]] = {}
    for point in points:
        index = int((point.ts - origin) // step)
        buckets.setdefault(index, []).append(point.value)
    return [
        SeriesPoint(ts=origin + index * step, value=sum(values) / len(values))
        for index, values in sorted(buckets.items())
    ]
