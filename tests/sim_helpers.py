"""Builds and runs the real Feather sketch on the PC against the stand-in Arduino library (tests/arduino_stub/), for the tests and the tools."""
import subprocess
from pathlib import Path

import numpy as np

from conftest import CORE, ROOT

STUB = ROOT / "tests" / "arduino_stub"
SKETCH = ROOT / "firmware" / "feather_m0"


def build_sim(out_dir, core=CORE, sketch=None, main=None):
    """Compile the C core with gcc and the sketch (as C++) with g++, with the undefined-behaviour sanitiser on. Returns the path of the program."""
    out_dir = Path(out_dir)
    objects = []
    for name in ("pid", "supervisor", "control", "actuator"):
        obj = out_dir / f"{name}.o"
        r = subprocess.run(["gcc", "-c", "-Wall", "-Wextra", "-Wshadow", "-fsanitize=undefined", "-I", str(core), str(Path(core) / f"{name}.c"), "-o", str(obj)],
                           capture_output=True, text=True)
        assert r.returncode == 0 and r.stderr == "", r.stderr
        objects.append(str(obj))
    exe = out_dir / "sim"
    cmd = ["g++", "-std=gnu++11", "-Wall", "-Wextra", "-fsanitize=undefined", "-I", str(core), "-I", str(STUB), str(main or STUB / "sim_main.cpp"), *objects, "-o", str(exe)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0 and r.stderr == "", "the sketch does not build:\n" + r.stderr
    return exe


def run_sim(exe, commands, *args):
    """Type `commands` into the simulated Serial Monitor. Returns the text the sketch printed. Fails if the sanitiser reports anything."""
    r = subprocess.run([str(exe), *map(str, args)], input=commands, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stderr == "", "undefined behaviour in the code:\n" + r.stderr[:600]
    return r.stdout


def last_table(text, header):
    """The rows of the last CSV block that starts with `header`, as an array (the block ends at a line starting with #)."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(header)]
    assert starts, f"no capture with the header {header!r} in the output"
    rows = []
    for line in lines[starts[-1] + 1:]:
        if line.startswith("#"):
            break
        rows.append([float(x) for x in line.split(",")])
    return np.array(rows)
