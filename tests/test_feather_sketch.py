"""The real Feather sketch (firmware/feather_m0/feather_m0.ino) with the real C core, run on the PC against a model of the circuit it will control:
the DAC on A0 into a 100 kOhm resistor, a 100 nF capacitor to ground, and the ADC on A1 reading the node (time constant 10 ms).

This catches mistakes in the sketch (a missing include, a wrong pin, a capture that is off by one sample, a command that does not work) before the board is involved.
It does NOT show that the real circuit behaves like the model: that is what the measurements on the board are for (docs/ON_BOARD.md)."""
import shutil
import subprocess

import numpy as np
import pytest

import identify
import requirements as R
from conftest import ROOT
from sim_helpers import SKETCH, STUB, build_sim, last_table, run_sim

TIME_SCALE = 0.1              # the board's plant (10 ms) over the simulated plant (100 ms): every time in tests/requirements.py shrinks by this factor


@pytest.fixture(scope="module")
def sim(tmp_path_factory):
    return build_sim(tmp_path_factory.mktemp("sim"))


def closed_loop(sim, target, *args):
    t, sp, u, pv = last_table(run_sim(sim, f"R{target}\n", *args), "t,sp,u,pv").T
    return t, sp, u, pv


def metrics(sp, pv, target):
    start = int(np.argmax(sp != sp[0]))
    size = target - sp[0]
    outside = np.nonzero(np.abs(pv[start:] - target) > 0.02 * size)[0]
    return {"overshoot_pct": max(0.0, (pv[start:].max() - target) / size * 100.0),
            "settle_s": 0.0 if len(outside) == 0 else (outside[-1] + 1) * 0.001,
            "steady_error": float(np.mean(np.abs(pv[-300:] - target)))}


def test_the_sketch_builds_and_says_what_it_is(sim):
    out = run_sim(sim, "I\n")
    assert "feather_m0 pid" in out and "gains (Q16.16)" in out


def test_unknown_commands_and_rest_are_handled(sim):
    out = run_sim(sim, "Q7\nZ\n")
    assert "# unknown command" in out and "# output at rest" in out


def test_an_open_loop_step_shows_the_circuit_the_documentation_predicts(sim):
    """The resting reading is about 204 counts, a step to output 500 settles near 1945 counts, and tools/identify.py finds a gain of 3.48 counts per
    per-mille and a time constant of 10 ms from the capture: the numbers in docs/ON_BOARD.md."""
    t, u, pv = last_table(run_sim(sim, "S500\n"), "t,u,pv").T
    assert len(t) == 600 and u[99] == 0 and u[100] == 500
    assert abs(np.mean(pv[50:100]) - 204.0) < 3.0
    assert abs(np.mean(pv[-50:]) - 1945.0) < 5.0
    m = identify.identify(t, u, pv)
    assert abs(m["gain"] - 3.48) / 3.48 < 0.03 and abs(m["tau"] - 0.010) / 0.010 < 0.10 and m["delay"] < 0.003


@pytest.mark.parametrize("target", [1000, 2000, 3000])
def test_the_closed_loop_meets_the_step_requirement_scaled_to_this_plant(sim, target):
    """REQ-1 of tests/requirements.py with every time scaled by 0.1: the same tuned gains must give the same behaviour, ten times faster."""
    t, sp, u, pv = closed_loop(sim, target)
    m = metrics(sp, pv, target)
    assert m["steady_error"] <= R.REQ1_MAX_STEADY_ERROR, m
    assert m["overshoot_pct"] <= R.REQ1_MAX_OVERSHOOT_PCT, m
    assert m["settle_s"] <= R.REQ1_MAX_SETTLE_S * TIME_SCALE, m


def test_the_output_stays_in_range_and_starts_at_rest(sim):
    t, sp, u, pv = closed_loop(sim, 2000)
    assert u.min() >= 0 and u.max() <= 1000
    assert u[:100].max() <= 10, "the output should stay near rest while the setpoint equals the resting reading"
    assert abs(u[-1] - 516) <= 6, "holding 2000 counts needs about (2000 - 204) / 3.48 = 516"


def test_a_load_pulling_the_node_down_is_rejected(sim):
    """0.1 V (about 124 counts) pulled off the node all the time: the loop still holds the setpoint, with a higher output."""
    t, sp, u, pv = closed_loop(sim, 2000, "--load", 0.1)
    assert np.mean(np.abs(pv[-300:] - 2000)) <= R.REQ1_MAX_STEADY_ERROR
    assert u[-1] > 516 + 25


def test_a_load_that_drags_the_resting_reading_below_50_counts_is_treated_as_a_shorted_sensor(sim):
    """The live zero leaves only about 155 counts above the supervisor's shorted limit (resting reading 204, limit 50). A load of 0.3 V takes the resting reading
    to 0, and the supervisor, correctly, holds the output off. This is a limit of the circuit, not a bug: docs/ON_BOARD.md says what to check on the board."""
    t, sp, u, pv = closed_loop(sim, 2000, "--load", 0.3)
    assert np.all(u == 0) and pv[-1] < 50


@pytest.mark.parametrize("stuck", [0, 4095])
def test_a_broken_sensor_never_drives_the_output(sim, stuck):
    """The supervisor at work in the real sketch: with the ADC stuck at 0 (shorted) or 4095 (open) the output stays at 0, whatever the setpoint."""
    t, sp, u, pv = closed_loop(sim, 2000, "--stuck", stuck)
    assert np.all(u == 0)


def test_the_same_input_gives_the_same_output_twice(sim):
    assert run_sim(sim, "S300\nR1500\n") == run_sim(sim, "S300\nR1500\n")


def test_the_sketch_folder_is_self_contained_after_sync_core(tmp_path):
    """The Arduino IDE compiles every .c file in the sketch folder and nothing else. Copy firmware/feather_m0 and core/ somewhere new, run the sync script,
    then build from the sketch folder alone with no other include path, as the IDE does."""
    shutil.copytree(ROOT / "core", tmp_path / "core")
    folder = tmp_path / "firmware" / "feather_m0"
    folder.mkdir(parents=True)
    for f in ("feather_m0.ino", "sync_core.sh"):
        shutil.copy(SKETCH / f, folder / f)
    assert subprocess.run(["sh", str(folder / "sync_core.sh")], capture_output=True, text=True).returncode == 0
    main = tmp_path / "sim_main.cpp"
    main.write_text((STUB / "sim_main.cpp").read_text().replace('"../../firmware/feather_m0/feather_m0.ino"', f'"{folder / "feather_m0.ino"}"'))
    exe = tmp_path / "sim"
    objects = []
    for c in sorted(folder.glob("*.c")):                         # what the IDE would compile
        obj = tmp_path / (c.stem + ".o")
        r = subprocess.run(["gcc", "-c", "-Wall", "-Wextra", "-I", str(folder), str(c), "-o", str(obj)], capture_output=True, text=True)
        assert r.returncode == 0 and r.stderr == "", r.stderr
        objects.append(str(obj))
    assert len(objects) == 4
    r = subprocess.run(["g++", "-std=gnu++11", "-Wall", "-Wextra", "-I", str(folder), "-I", str(STUB), str(main), *objects, "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0 and r.stderr == "", r.stderr
    assert "t,u,pv" in run_sim(exe, "S200\n")
