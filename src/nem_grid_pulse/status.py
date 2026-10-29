"""Auditable red / amber / green rules for the dashboard KPI cards."""

from __future__ import annotations


def relative_stress(latest: float, baseline: float, *, amber: float, red: float) -> str:
    """Higher than the baseline is worse. Gaps are fractions, so 0.10 means 10%."""
    if baseline == 0:
        return "amber"
    gap = (latest - baseline) / abs(baseline)
    if gap > red:
        return "red"
    if gap > amber:
        return "amber"
    return "green"


def negative_price_status(hour_share: float) -> str:
    if hour_share < 0.02:
        return "green"
    if hour_share < 0.08:
        return "amber"
    return "red"


def renewable_share_status(share: float) -> str:
    if share >= 0.45:
        return "green"
    if share >= 0.30:
        return "amber"
    return "red"


def headroom_status(fraction_of_peak: float) -> str:
    """How large a flat +1 GW is relative to the region's own peak."""
    if fraction_of_peak >= 0.50:
        return "red"
    if fraction_of_peak >= 0.25:
        return "amber"
    return "green"


STATUS_LABEL = {"green": "Within band", "amber": "Watch", "red": "High stress"}
