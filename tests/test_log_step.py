"""Tests of tools/log_step.py: what it writes must be readable by tools/identify.py and give back the plant that was simulated."""
import csv

import pytest

import identify
import log_step


def read(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return [float(r["t"]) for r in rows], [float(r["u"]) for r in rows], [float(r["pv"]) for r in rows]


def test_the_file_has_the_right_columns_and_one_step(tmp_path):
    path = tmp_path / "step.csv"
    assert log_step.main([str(path)]) == 0
    t, u, pv = read(path)
    assert len(t) == 500 and u[0] == 0 and u[-1] == 500 and sorted(set(u)) == [0.0, 500.0]
    assert abs(t[1] - t[0] - 0.01) < 1e-9


def test_the_default_step_is_recognised_as_the_nominal_plant(tmp_path):
    path = tmp_path / "step.csv"
    log_step.main([str(path)])
    m = identify.identify(*read(path))
    assert abs(m["gain"] - 3.0) / 3.0 < 0.05 and abs(m["tau"] - 0.1) / 0.1 < 0.2 and abs(m["delay"] - 0.02) < 0.035


@pytest.mark.parametrize("tau,gain", [(0.2, 3.0), (0.05, 2.0)])
def test_other_plants_can_be_logged_and_recovered(tmp_path, tau, gain):
    path = tmp_path / "step.csv"
    log_step.main([str(path), "--tau", str(tau), "--gain", str(gain), "--seconds", "6"])
    m = identify.identify(*read(path))
    assert abs(m["gain"] - gain) / gain < 0.05 and abs(m["tau"] - tau) / tau < 0.2
