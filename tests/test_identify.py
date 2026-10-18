"""Tests of tools/identify.py on data from the simulated plant, where the right answer is known. Needs none of your code."""
import csv
from pathlib import Path

import numpy as np
import pytest

import identify
from plant import TS, Plant, simulate


def open_loop_step(plant, n=500, at=20, out=500, seed=2):
    u = np.zeros(n)
    u[at:] = out
    it = iter(u)
    return simulate(lambda sp, adc: next(it), np.zeros(n), plant, seed=seed), u


@pytest.mark.parametrize("gain,tau,delay", [(3.0, 0.1, 2), (3.0, 0.2, 2), (2.0, 0.05, 4), (4.0, 0.3, 0), (1.5, 0.1, 6)])
def test_the_plant_is_recovered_from_a_noisy_step(gain, tau, delay):
    log, u = open_loop_step(Plant(gain=gain, tau=tau, delay=delay, noise=1.0))
    m = identify.identify(log["t"], u, log["adc"])
    assert abs(m["gain"] - gain) / gain < 0.05
    assert abs(m["tau"] - tau) / tau < 0.20
    assert abs(m["delay"] - (delay * TS)) < 0.035                    # within about three samples


def test_the_suggested_gains_follow_the_lambda_formula():
    m = {"gain": 3.0, "tau": 0.1, "delay": 0.02, "ts": 0.01}
    g = identify.suggest(m)                                          # lambda = tau
    assert g["kp"] == pytest.approx(0.1 / (3.0 * (0.1 + 0.02 + 0.005)))
    assert g["ki"] == pytest.approx(g["kp"] * 0.01 / 0.1)
    slower = identify.suggest(m, lam=0.3)
    assert slower["kp"] < g["kp"] and slower["ki"] < g["ki"]


def test_a_log_without_a_step_is_refused():
    with pytest.raises(ValueError):
        identify.identify(np.arange(100) * 0.01, np.zeros(100), np.full(100, 300.0))


def test_the_command_line_reads_a_csv(tmp_path, capfd):
    log, u = open_loop_step(Plant(noise=1.0))
    path = tmp_path / "step.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "u", "pv"])
        w.writerows(zip(log["t"], u, log["adc"]))
    assert identify.main([str(path)]) == 0
    printed = capfd.readouterr().out
    assert "plant:" in printed and "#define CONTROL_KP_Q16" in printed


def test_a_reading_that_does_not_respond_to_the_step_is_refused_with_a_wiring_hint():
    """An analogue input that is not connected reads noise (often mains hum) whatever the output does. That must be reported, not turned into a plant."""
    n = 300
    u = np.zeros(n)
    u[100:] = 500
    pv = 1700 + np.random.RandomState(1).normal(0, 100, n)
    with pytest.raises(ValueError, match="did not respond"):
        identify.identify(np.arange(n) * 0.001, u, pv)


def test_the_real_capture_from_a_floating_input_is_refused(capfd):
    """tests/data/board_step_floating_input.csv is a real capture from the Feather with the ADC input left unconnected: the reading sat near 1680 counts with 50 Hz
    mains hum, before and after the step. It once crashed this tool with a division by zero."""
    path = Path(__file__).parent / "data" / "board_step_floating_input.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    with pytest.raises(ValueError, match="did not respond"):
        identify.identify([r["t"] for r in rows], [r["u"] for r in rows], [r["pv"] for r in rows])
    assert identify.main([str(path)]) == 1
    assert "did not respond" in capfd.readouterr().err


def test_a_plant_that_responds_the_wrong_way_is_refused(tmp_path, capfd):
    log, u = open_loop_step(Plant(noise=1.0))
    path = tmp_path / "step.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "u", "pv"])
        w.writerows(zip(log["t"], u, 4000.0 - log["adc"]))
    assert identify.main([str(path)]) == 1
    assert "more output raises the reading" in capfd.readouterr().err


def test_a_noise_free_step_still_works():
    log, u = open_loop_step(Plant(noise=0.0))
    m = identify.identify(log["t"], u, log["adc"])
    assert abs(m["gain"] - 3.0) / 3.0 < 0.05
