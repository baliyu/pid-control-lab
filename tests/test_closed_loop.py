"""The controller (PID plus supervisor, with the gains in core/gains.h) against the simulated plant. The limits are in tests/requirements.py.
These fail until you have written the PID and the supervisor and tuned the gains."""
import itertools

import numpy as np
import pytest

import requirements as R
from conftest import Ctrl
from plant import ADC_MAX, TS, Plant, simulate, step_metrics

N = 700                                     # 7 s
START = 20


def step_setpoint(n=N, to=R.STEP_TO):
    sp = np.full(n, float(R.STEP_FROM))
    sp[START:] = to
    return sp


def in_limits(log):
    return bool(np.all((log["out"] >= 0) & (log["out"] <= 1000)))


def back_within(log, after, target, band):
    """Seconds after sample `after` until the process value stays within +-band of target (0.0 if it never left, inf if it never stays)."""
    outside = np.nonzero(np.abs(log["pv"][after:] - target) > band)[0]
    if len(outside) == 0:
        return 0.0
    return float("inf") if outside[-1] == len(log["pv"][after:]) - 1 else (outside[-1] + 1) * TS


def test_REQ1_step_response_on_the_nominal_plant(lib):
    log = simulate(Ctrl(lib).step, step_setpoint(), Plant())
    m = step_metrics(log, START, R.STEP_TO)
    assert in_limits(log)
    assert m["steady_error"] <= R.REQ1_MAX_STEADY_ERROR, m
    assert m["overshoot_pct"] <= R.REQ1_MAX_OVERSHOOT_PCT, m
    assert m["settle_s"] <= R.REQ1_MAX_SETTLE_S, m


@pytest.mark.parametrize("gain_factor,tau,delay", list(itertools.product([0.7, 1.0, 1.3], [0.05, 0.1, 0.2], [0, 2, 5])))
def test_REQ2_the_same_gains_work_on_plants_that_differ(lib, gain_factor, tau, delay):
    log = simulate(Ctrl(lib).step, step_setpoint(), Plant(gain=3.0 * gain_factor, tau=tau, delay=delay))
    m = step_metrics(log, START, R.STEP_TO)
    assert in_limits(log)
    assert m["steady_error"] <= R.REQ2_MAX_STEADY_ERROR, m
    assert m["overshoot_pct"] <= R.REQ2_MAX_OVERSHOOT_PCT, m


def test_REQ3_sensor_noise_does_not_make_the_actuator_chatter(lib):
    log = simulate(Ctrl(lib).step, step_setpoint(), Plant(noise=R.REQ3_NOISE_COUNTS), seed=3)
    assert in_limits(log)
    assert np.std(log["out"][-200:]) <= R.REQ3_MAX_OUTPUT_STD
    assert abs(np.mean(log["pv"][-200:]) - R.STEP_TO) <= R.REQ3_MAX_STEADY_ERROR


def test_REQ4_a_load_disturbance_is_rejected(lib):
    n, t_load = 900, 400
    load = np.zeros(n)
    load[t_load:] = R.REQ4_LOAD
    log = simulate(Ctrl(lib).step, step_setpoint(n), Plant(), load=load)
    assert in_limits(log)
    assert np.max(np.abs(log["pv"][t_load:] - R.STEP_TO)) <= R.REQ4_MAX_PEAK_DEVIATION
    assert back_within(log, t_load, R.STEP_TO, 40.0) <= R.REQ4_MAX_RECOVERY_S


def test_REQ5_the_controller_recovers_quickly_from_a_long_saturation(lib):
    """The setpoint is unreachable for 3 s, so the output sits at its limit; an integral that kept growing would delay the recovery."""
    n, back = 900, 320
    sp = step_setpoint(n, to=20000)
    sp[back:] = R.STEP_TO
    log = simulate(Ctrl(lib).step, sp, Plant())
    assert in_limits(log) and log["out"][back - 10] == 1000
    band = 0.02 * (R.STEP_TO - R.STEP_FROM)
    assert back_within(log, back, R.STEP_TO, band) <= R.REQ5_MAX_RECOVERY_S


@pytest.mark.parametrize("forced,name", [(0, "shorted"), (4095, "open")])
def test_REQ6_a_broken_sensor_makes_the_output_safe_and_the_loop_resumes(lib, forced, name):
    n, a, b = 900, 300, 400
    override = [None] * n
    for k in range(a, b):
        override[k] = forced
    ctrl = Ctrl(lib)
    log = simulate(ctrl.step, step_setpoint(n), Plant(), adc_override=override)
    assert in_limits(log)
    assert np.all(log["out"][a + 4:b + 19] == 0), f"{name}: the output must be 0 from the 5th bad sample until 20 good samples after the sensor is back"
    band = 0.02 * (R.STEP_TO - R.STEP_FROM)
    assert back_within(log, b, R.STEP_TO, band) <= R.REQ6_MAX_RESUME_S
    assert not ctrl.fault


def test_REQ6_the_pid_does_not_wind_up_during_a_sensor_fault(lib):
    """The sensor reads 0 (shorted) for 3 s. Resuming must not throw the process value far above the setpoint."""
    n, a, b = 900, 300, 600
    override = [None] * n
    for k in range(a, b):
        override[k] = 0
    log = simulate(Ctrl(lib).step, step_setpoint(n), Plant(), adc_override=override)
    assert np.max(log["pv"][b:]) <= R.STEP_TO * 1.15


def test_REQ7_even_the_sanitiser_stays_quiet_over_a_long_noisy_run(lib):
    log = simulate(Ctrl(lib).step, step_setpoint(3000), Plant(noise=15.0), seed=11)
    assert in_limits(log) and np.max(log["adc"]) <= ADC_MAX
