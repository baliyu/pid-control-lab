"""Tests of the test equipment itself: the simulated plant and the metrics. These need none of your code and pass from the start,
so that a failing closed-loop test means the controller is at fault, not the simulator."""
import math

import numpy as np
import pytest

from plant import ADC_MAX, TS, Plant, simulate, step_metrics


def hold(out):
    return lambda sp, adc: out


def test_open_loop_step_follows_the_exponential():
    n = 300
    log = simulate(hold(500), np.zeros(n), Plant(gain=3.0, tau=0.1, delay=0, offset=300.0))
    expected = 300.0 + 1500.0 * (1.0 - np.exp(-(log["t"] + TS) / 0.1))
    assert np.max(np.abs(log["pv"][1:] - expected[:-1])) < 1.0 + 1e-9


def test_the_delay_postpones_the_response_by_that_many_samples():
    base = simulate(hold(500), np.zeros(100), Plant(delay=0))
    late = simulate(hold(500), np.zeros(100), Plant(delay=5))
    assert np.allclose(late["pv"][5:], base["pv"][:-5])
    assert np.all(late["pv"][:6] == 300.0)


def test_output_is_limited_to_the_actuator_range_and_pv_to_the_adc_range():
    log = simulate(hold(100000), np.zeros(400), Plant(gain=30.0))
    assert log["pv"].max() <= ADC_MAX and log["adc"].max() <= ADC_MAX


def test_a_load_lowers_the_steady_state_by_that_many_counts():
    log = simulate(hold(500), np.zeros(600), Plant(delay=0), load=np.full(600, 200.0))
    assert abs(log["pv"][-1] - (300.0 + 1500.0 - 200.0)) < 1.0


def test_noise_is_added_to_what_the_controller_sees_but_not_to_the_true_value():
    log = simulate(hold(500), np.zeros(2000), Plant(noise=3.0), seed=5)
    spread = np.std(log["adc"][1000:] - log["pv"][1000:])
    assert 2.0 < spread < 4.0
    assert np.std(log["pv"][1000:]) < 0.5


def test_a_broken_sensor_reports_the_forced_value_while_the_real_value_carries_on():
    override = [None] * 50 + [0] * 20 + [None] * 30
    log = simulate(hold(300), np.zeros(100), Plant(delay=0), adc_override=override)
    assert np.all(log["adc"][50:70] == 0) and log["pv"][60] > 300.0


def test_the_same_seed_gives_the_same_run():
    a = simulate(hold(400), np.zeros(200), Plant(noise=2.0), seed=9)
    b = simulate(hold(400), np.zeros(200), Plant(noise=2.0), seed=9)
    assert np.array_equal(a["adc"], b["adc"])


def test_metrics_on_a_made_up_response():
    n, start = 400, 20
    sp = np.full(n, 300.0)
    sp[start:] = 2000.0
    pv = np.full(n, 300.0)
    t = np.arange(n - start) * TS
    pv[start:] = 2000.0 - 1700.0 * np.exp(-t / 0.2) * np.cos(8 * t)         # rings a little, settles
    log = {"t": np.arange(n) * TS, "sp": sp, "pv": pv}
    m = step_metrics(log, start, 2000.0)
    assert m["steady_error"] < 1.0 and m["overshoot_pct"] > 0.0 and 0.3 < m["settle_s"] < 1.5


def test_metrics_report_a_response_that_never_settles_as_infinite():
    n = 200
    sp = np.full(n, 300.0)
    sp[20:] = 2000.0
    log = {"t": np.arange(n) * TS, "sp": sp, "pv": np.full(n, 300.0)}
    assert math.isinf(step_metrics(log, 20, 2000.0)["settle_s"])


@pytest.mark.parametrize("tau", [0.05, 0.1, 0.2])
def test_time_constant_is_respected(tau):
    log = simulate(hold(500), np.zeros(int(6 * tau / TS) + 5), Plant(tau=tau, delay=0))
    k = int(round(tau / TS)) - 1
    assert abs((log["pv"][k + 1] - 300.0) / 1500.0 - (1 - math.exp(-1))) < 0.01
