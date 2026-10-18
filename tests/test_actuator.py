"""Tests of core/actuator.c, the live-zero mapping from controller output to a converter code. It is compiled on its own, with the
undefined-behaviour sanitiser, so it does not depend on the PID or the supervisor."""
import ctypes
import subprocess

import pytest

from conftest import CORE


@pytest.fixture(scope="module")
def scale(tmp_path_factory):
    so = tmp_path_factory.mktemp("act") / "libact.so"
    cmd = ["gcc", "-shared", "-fPIC", "-O1", "-g", "-Wall", "-Wextra", "-Wshadow", "-fsanitize=undefined", "-I", str(CORE), str(CORE / "actuator.c"), "-o", str(so)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0 and result.stderr == "", result.stderr
    f = ctypes.CDLL(str(so)).actuator_scale
    f.restype, f.argtypes = ctypes.c_int32, [ctypes.c_int32, ctypes.c_int32]
    return f


def test_the_ends_of_the_range_are_5_and_90_percent_of_full_scale(scale):
    assert scale(0, 1023) == 51 and scale(1000, 1023) == 921
    assert scale(0, 4095) == 205 and scale(1000, 4095) == 3686
    assert scale(0, 1599) == 80 and scale(1000, 1599) == 1439


def test_the_output_never_reaches_zero_or_full_scale(scale):
    """The reason for the mapping: the lowest and the highest signal must stay clear of the supervisor's shorted and open limits (50 and 4045 of 4095)."""
    full = 4095
    assert scale(0, full) > 50 and scale(1000, full) < 4045


def test_it_rises_with_the_output_and_never_falls(scale):
    codes = [scale(u, 1023) for u in range(0, 1001)]
    assert all(b >= a for a, b in zip(codes, codes[1:]))
    assert codes[-1] - codes[0] == 870                    # 921 - 51: about 0.87 of a code per output unit


def test_it_is_within_half_a_code_of_the_exact_value(scale):
    for u in range(0, 1001, 7):
        exact = 1023 * (0.05 + 0.85 * u / 1000.0)
        assert abs(scale(u, 1023) - exact) <= 0.5 + 1e-9


@pytest.mark.parametrize("u,expected", [(-1, 51), (-100000, 51), (1001, 921), (2 ** 31 - 1, 921), (-2 ** 31, 51)])
def test_out_of_range_outputs_are_clamped(scale, u, expected):
    assert scale(u, 1023) == expected


def test_large_full_scales_do_not_overflow(scale):
    assert scale(1000, 2 ** 20) == round(2 ** 20 * 0.9) and scale(0, 65535) == round(65535 * 0.05)
