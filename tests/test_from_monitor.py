"""Tests of tools/from_monitor.py, and of the whole chain from a capture on the (simulated) board to the plant model that tools/identify.py finds."""
import pytest

import from_monitor
import identify
from sim_helpers import build_sim, run_sim

RAW = """# feather_m0 pid: 1 kHz loop
12:00:01.001 -> # gains (Q16.16): kp 17309 ki 1735 kd 0
12:00:05.000 -> t,u,pv\r
12:00:05.001 -> 0.000,0,203\r
12:00:05.002 -> 0.001,0,204\r
12:00:05.003 -> # done
12:00:09.000 -> t,u,pv
12:00:09.001 -> 0.000,0,201
12:00:09.002 -> 0.001,500,202
12:00:09.003 -> 0.002,500,230
12:00:09.004 -> # done
"""


def test_the_last_capture_is_taken_by_default_and_time_stamps_are_dropped(tmp_path):
    raw, out = tmp_path / "raw.txt", tmp_path / "out.csv"
    raw.write_text(RAW)
    assert from_monitor.main([str(raw), str(out)]) == 0
    assert out.read_text().splitlines() == ["t,u,pv", "0.000,0,201", "0.001,500,202", "0.002,500,230"]


def test_an_earlier_capture_can_be_chosen(tmp_path):
    raw, out = tmp_path / "raw.txt", tmp_path / "out.csv"
    raw.write_text(RAW)
    assert from_monitor.main([str(raw), str(out), "--block", "0"]) == 0
    assert out.read_text().splitlines() == ["t,u,pv", "0.000,0,203", "0.001,0,204"]
    assert from_monitor.main([str(raw), str(out), "--block", "5"]) == 1


def test_text_without_a_capture_is_refused(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("# nothing here\nhello\n")
    assert from_monitor.main([str(raw), str(tmp_path / "out.csv")]) == 1


def test_closed_loop_captures_with_four_columns_are_kept_whole(tmp_path):
    raw, out = tmp_path / "raw.txt", tmp_path / "out.csv"
    raw.write_text("t,sp,u,pv\n0.000,203,0,203\n0.001,203,0,204\n# done\n")
    assert from_monitor.main([str(raw), str(out)]) == 0
    assert out.read_text().splitlines()[0] == "t,sp,u,pv"


def test_a_capture_from_the_sketch_goes_through_the_tools_and_gives_the_documented_plant(tmp_path_factory):
    """Sketch (on the PC) -> text as the Serial Monitor shows it -> from_monitor -> identify: the chain the real session will use."""
    tmp = tmp_path_factory.mktemp("chain")
    text = run_sim(build_sim(tmp), "I\nS500\n")
    stamped = "\n".join(f"10:00:{i % 60:02d}.000 -> {line}" for i, line in enumerate(text.splitlines())) + "\n"
    raw, out = tmp / "raw.txt", tmp / "step.csv"
    raw.write_text(stamped)
    assert from_monitor.main([str(raw), str(out)]) == 0
    assert identify.main([str(out)]) == 0
