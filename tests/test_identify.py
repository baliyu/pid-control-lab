"""Tests of tools/identify.py on data from the simulated plant, where the right answer is known. Needs none of your code."""
import csv

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
