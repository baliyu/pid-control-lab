"""Checks on the C code itself rather than on its behaviour."""
import re
from pathlib import Path

from conftest import CORE


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def test_the_code_builds_with_no_compiler_warnings(build_result):
    """-Wall -Wextra -Wshadow: warnings in fixed-point code are very often real bugs (a sign mix, a truncation)."""
    _, result = build_result
    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == "", "the compiler reported warnings:\n" + result.stderr


def test_the_controller_and_supervisor_use_no_floating_point():
    """The target (STM32L0, Cortex-M0+) has no floating-point unit: float and double there are slow software routines and pull in a library."""
    for name in ("pid.c", "pid.h", "supervisor.c", "supervisor.h"):
        code = strip_comments((CORE / name).read_text())
        assert not re.search(r"\b(float|double)\b|math\.h|\bsqrt|\bpow\b", code), f"{name} uses floating point"
        assert not re.search(r"\d\.\d|\d\.f\b|\d[eE][+-]?\d", code.replace("0x", "")), f"{name} contains a floating-point constant"


def test_the_gains_are_inside_the_range_the_controller_is_specified_for():
    """docs/SPEC.md: gains are 0.0 to 255.0 in Q16.16 (0 to 16711680)."""
    text = (CORE / "gains.h").read_text()
    for name in ("CONTROL_KP_Q16", "CONTROL_KI_Q16", "CONTROL_KD_Q16"):
        m = re.search(rf"#define\s+{name}\s+(\d+)", text)
        assert m, f"{name} is not a plain integer in gains.h"
        assert 0 <= int(m.group(1)) <= 255 * 65536, f"{name} is out of range"
    ki = int(re.search(r"#define\s+CONTROL_KI_Q16\s+(\d+)", text).group(1))
    assert ki == 0 or ki >= 100, "a ki this small is below the resolution you can tune with in Q16.16 (check the units)"
