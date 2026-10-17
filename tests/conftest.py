"""Builds the C controller into a shared library and gives the tests small Python wrappers around it.

The library is compiled with the undefined-behaviour sanitiser, so a signed integer overflow anywhere in your code fails the test that caused it.
Set CORE_DIR to test a different copy of the core/ folder (the default is core/ in this repository).
"""
import ctypes
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get("CORE_DIR", ROOT / "core")).resolve()
WRAPPER = ROOT / "tests" / "wrapper" / "ctrl_wrapper.c"
C_FILES = [CORE / "pid.c", CORE / "supervisor.c", CORE / "control.c"]
Q = 65536                                   # PID_ONE: 1.0 in Q16.16


def q16(x):
    """A real gain as a Q16.16 integer."""
    return int(round(x * Q))


def build(out_dir):
    out = Path(out_dir) / "libcontrol.so"
    cmd = ["gcc", "-shared", "-fPIC", "-O1", "-g", "-Wall", "-Wextra", "-Wshadow", "-fsanitize=undefined",
           "-I", str(CORE), *map(str, C_FILES), str(WRAPPER), "-o", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return out, result


@pytest.fixture(scope="session")
def build_result(tmp_path_factory):
    out, result = build(tmp_path_factory.mktemp("build"))
    return out, result


def load_library(path):
    """Open the compiled library and declare the argument and result types of every function in it."""
    L = ctypes.CDLL(str(path))
    i32, vp = ctypes.c_int32, ctypes.c_void_p
    sigs = {
        "w_pid_new": (vp, [i32] * 5), "w_pid_free": (None, [vp]), "w_pid_reset": (None, [vp]), "w_pid_update": (i32, [vp, i32, i32]),
        "w_sup_new": (vp, []), "w_sup_free": (None, [vp]), "w_sup_step": (i32, [vp, i32, i32]), "w_sup_fault": (ctypes.c_int, [vp]),
        "w_ctrl_new": (vp, [ctypes.c_int, i32, i32, i32]), "w_ctrl_free": (None, [vp]), "w_ctrl_step": (i32, [vp, i32, i32]),
        "w_ctrl_fault": (ctypes.c_int, [vp]),
        "w_default_kp": (i32, []), "w_default_ki": (i32, []), "w_default_kd": (i32, []), "w_out_min": (i32, []), "w_out_max": (i32, []),
    }
    for name, (res, args) in sigs.items():
        f = getattr(L, name)
        f.restype, f.argtypes = res, args
    return L


@pytest.fixture(scope="session")
def lib(build_result):
    out, result = build_result
    assert result.returncode == 0, "the C code does not build:\n" + result.stderr
    return load_library(out)


class Pid:
    """The PID alone. Gains are real numbers here (converted to Q16.16)."""

    def __init__(self, lib, kp=0.0, ki=0.0, kd=0.0, lo=-500, hi=500, raw=False):
        conv = (lambda g: int(g)) if raw else q16
        self.lib, self.h = lib, lib.w_pid_new(conv(kp), conv(ki), conv(kd), lo, hi)

    def update(self, sp, pv):
        return self.lib.w_pid_update(self.h, sp, pv)

    def reset(self):
        self.lib.w_pid_reset(self.h)

    def __del__(self):
        self.lib.w_pid_free(self.h)


class Sup:
    def __init__(self, lib):
        self.lib, self.h = lib, lib.w_sup_new()

    def step(self, adc, out=500):
        return self.lib.w_sup_step(self.h, adc, out)

    @property
    def fault(self):
        return bool(self.lib.w_sup_fault(self.h))

    def __del__(self):
        self.lib.w_sup_free(self.h)


class Ctrl:
    """PID plus supervisor, with the gains from core/gains.h unless others are given (real numbers)."""

    def __init__(self, lib, gains=None):
        self.lib = lib
        self.h = lib.w_ctrl_new(1, 0, 0, 0) if gains is None else lib.w_ctrl_new(0, q16(gains[0]), q16(gains[1]), q16(gains[2]))

    def step(self, sp, adc):
        return self.lib.w_ctrl_step(self.h, sp, adc)

    @property
    def fault(self):
        return bool(self.lib.w_ctrl_fault(self.h))

    def __del__(self):
        self.lib.w_ctrl_free(self.h)


@pytest.fixture(autouse=True)
def no_undefined_behaviour(capfd):
    """Fail any test during which the sanitiser reports undefined behaviour (for example a signed overflow) in the C code."""
    yield
    err = capfd.readouterr().err
    assert "runtime error" not in err, "undefined behaviour in the C code:\n" + err[:800]
