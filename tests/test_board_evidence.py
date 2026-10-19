"""The captures recorded on the real board (results/board/) against the requirement, the predictions and the guide.

These are not simulations: step_S500.csv and run_R2000.csv are what the Feather M0 printed with the 100 kOhm and 100 nF circuit wired up. If they are ever replaced by
captures from a different circuit, these tests say whether the claims in the README and the guide still hold."""
import numpy as np
import pytest

import board_report
import identify
import score_run
from conftest import ROOT

STEP = ROOT / "results" / "board" / "step_S500.csv"
RUN = ROOT / "results" / "board" / "run_R2000.csv"


def test_the_recorded_closed_loop_run_meets_the_scaled_step_requirement(capfd):
    assert score_run.main([str(RUN)]) == 0, capfd.readouterr().out


def test_the_recorded_step_gives_a_plant_close_to_the_prediction():
    t, u, pv = board_report.load(STEP, ("t", "u", "pv"))
    m = identify.identify(t, u, pv)
    assert abs(m["gain"] - 3.48) / 3.48 < 0.10, m
    assert abs(m["tau"] - 0.010) / 0.010 < 0.25, m
    assert m["delay"] < 0.003, m


def test_the_integral_holds_the_target_with_no_average_offset():
    m = board_report.measure()
    assert abs(m["bias"]) <= 3.0, m
    assert abs(m["u_hold"] - 516) <= 25, m


def test_the_guide_table_is_generated_from_these_captures(capfd):
    assert board_report.main(["--check"]) == 0, capfd.readouterr().err
