"""Tests of tools/score_run.py: a good run from the (simulated) board passes, and runs that are wrong in different ways fail."""
import numpy as np
import pytest

import score_run
from sim_helpers import build_sim, last_table, run_sim


@pytest.fixture(scope="module")
def run_text(tmp_path_factory):
    return run_sim(build_sim(tmp_path_factory.mktemp("score")), "R2000\n")


def write_csv(path, t, sp, u, pv):
    path.write_text("t,sp,u,pv\n" + "\n".join(f"{a:.3f},{b:.0f},{c:.0f},{d:.0f}" for a, b, c, d in zip(t, sp, u, pv)) + "\n")


def test_a_good_run_passes(tmp_path, run_text):
    t, sp, u, pv = last_table(run_text, "t,sp,u,pv").T
    path = tmp_path / "run.csv"
    write_csv(path, t, sp, u, pv)
    assert score_run.main([str(path), "--plot", str(tmp_path / "run.png")]) == 0
    assert (tmp_path / "run.png").stat().st_size > 10000


def test_a_slow_run_fails_on_settling_time(tmp_path, run_text):
    t, sp, u, pv = last_table(run_text, "t,sp,u,pv").T
    slow = np.concatenate([np.full(100, pv[0]), pv[100] + (2000 - pv[100]) * (1 - np.exp(-(t[100:] - t[100]) / 0.15))])     # tau 150 ms instead of 10 ms
    path = tmp_path / "slow.csv"
    write_csv(path, t, sp, u, slow)
    assert score_run.main([str(path)]) == 1


def test_a_run_that_overshoots_fails(tmp_path, run_text):
    t, sp, u, pv = last_table(run_text, "t,sp,u,pv").T
    ringing = pv.copy()
    ringing[100:] = 2000 + (pv[100:] - 2000) + 400 * np.exp(-(t[100:] - t[100]) / 0.05) * np.sin((t[100:] - t[100]) * 200)
    path = tmp_path / "ring.csv"
    write_csv(path, t, sp, u, ringing)
    assert score_run.main([str(path)]) == 1


def test_a_run_that_never_reaches_the_target_fails(tmp_path, run_text):
    t, sp, u, pv = last_table(run_text, "t,sp,u,pv").T
    path = tmp_path / "stuck.csv"
    write_csv(path, t, sp, u, np.full(len(t), 203))
    assert score_run.main([str(path)]) == 1


def test_a_run_without_a_setpoint_step_is_refused():
    with pytest.raises(ValueError):
        score_run.score(np.arange(100) * 0.001, np.full(100, 500.0), np.full(100, 500.0))
