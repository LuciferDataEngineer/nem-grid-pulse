from nem_grid_pulse.status import (
    headroom_status,
    negative_price_status,
    relative_stress,
    renewable_share_status,
)


def test_relative_stress_bands():
    assert relative_stress(100, 100, amber=0.10, red=0.30) == "green"
    assert relative_stress(115, 100, amber=0.10, red=0.30) == "amber"
    assert relative_stress(140, 100, amber=0.10, red=0.30) == "red"
    assert relative_stress(90, 100, amber=0.10, red=0.30) == "green"


def test_absolute_status_bands():
    assert negative_price_status(0.01) == "green"
    assert negative_price_status(0.05) == "amber"
    assert negative_price_status(0.10) == "red"
    assert renewable_share_status(0.50) == "green"
    assert renewable_share_status(0.35) == "amber"
    assert renewable_share_status(0.20) == "red"
    assert headroom_status(0.10) == "green"
    assert headroom_status(0.30) == "amber"
    assert headroom_status(0.80) == "red"
