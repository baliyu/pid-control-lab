"""Tests of the sensor supervisor alone. Each test names the rule in docs/SPEC.md that it checks."""
import pytest

from conftest import Sup

MIN, MAX, FAULT_AFTER, CLEAR_AFTER, SAFE = 50, 4045, 5, 20, 0       # the constants in core/supervisor.h


def test_S1_a_healthy_sensor_passes_the_output_straight_through(lib):
    """S1: while every sample is inside [50, 4045] the output is returned unchanged and there is no fault."""
    s = Sup(lib)
    assert not s.fault
    for adc in (50, 51, 300, 2000, 4044, 4045, 1234):
        for out in (0, 1, 500, 1000, -7):
            assert s.step(adc, out) == out and not s.fault


@pytest.mark.parametrize("bad", [0, 49, 4046, 4095, -5, 100000])
def test_S2_a_fault_is_declared_on_the_fifth_bad_sample_in_a_row(lib, bad):
    """S2: the first four bad samples pass the output through (it could be a glitch); the fifth declares the fault and the output becomes safe."""
    s = Sup(lib)
    for n in range(1, FAULT_AFTER):
        assert s.step(bad, 800) == 800 and not s.fault, f"bad sample number {n}"
    assert s.step(bad, 800) == SAFE and s.fault
    assert s.step(bad, 800) == SAFE and s.fault


def test_S2_the_limits_are_exact(lib):
    for good in (MIN, MAX):
        s = Sup(lib)
        for _ in range(50):
            assert s.step(good, 600) == 600 and not s.fault, f"{good} is a good reading"
    for bad in (MIN - 1, MAX + 1):
        s = Sup(lib)
        for _ in range(FAULT_AFTER):
            s.step(bad, 600)
        assert s.fault, f"{bad} is a bad reading"


def test_S3_a_good_sample_restarts_the_count_of_bad_ones(lib):
    """S3: bad samples must be consecutive: a good one in between starts the count again, so scattered glitches never declare a fault."""
    s = Sup(lib)
    for _ in range(10):
        for _ in range(FAULT_AFTER - 1):
            s.step(0, 500)
        s.step(2000, 500)
    assert not s.fault
    assert s.step(0, 500) == 500


def test_S3_mixed_bad_values_count_together(lib):
    s = Sup(lib)
    for adc in (0, 4095, 10, 4090):
        s.step(adc, 500)
    assert not s.fault
    assert s.step(0, 500) == SAFE and s.fault


def test_S4_a_fault_clears_on_the_twentieth_good_sample_in_a_row(lib):
    """S4: while there is a fault the output stays safe until 20 good samples in a row; the 20th passes the output through again."""
    s = Sup(lib)
    for _ in range(FAULT_AFTER):
        s.step(0, 500)
    assert s.fault
    for n in range(1, CLEAR_AFTER):
        assert s.step(2000, 700) == SAFE and s.fault, f"good sample number {n}"
    assert s.step(2000, 700) == 700 and not s.fault
    assert s.step(2000, 650) == 650


def test_S4_a_bad_sample_during_recovery_restarts_the_count_of_good_ones(lib):
    s = Sup(lib)
    for _ in range(FAULT_AFTER):
        s.step(4095, 500)
    for _ in range(CLEAR_AFTER - 1):
        s.step(2000, 700)
    assert s.fault
    s.step(4095, 700)
    for n in range(1, CLEAR_AFTER):
        assert s.step(2000, 700) == SAFE and s.fault, f"after the interruption, good sample number {n}"
    assert s.step(2000, 700) == 700 and not s.fault


def test_S4_after_a_fault_has_cleared_a_new_one_needs_five_bad_samples_again(lib):
    s = Sup(lib)
    for _ in range(FAULT_AFTER):
        s.step(0, 500)
    for _ in range(CLEAR_AFTER):
        s.step(2000, 500)
    assert not s.fault
    for n in range(1, FAULT_AFTER):
        assert s.step(0, 500) == 500 and not s.fault
    assert s.step(0, 500) == SAFE and s.fault


def test_S4_two_supervisors_do_not_share_state(lib):
    a, b = Sup(lib), Sup(lib)
    for _ in range(FAULT_AFTER):
        a.step(0, 500)
    assert a.fault and not b.fault and b.step(0, 500) == 500
