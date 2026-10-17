"""Unit tests of the PID alone. Each test names the rule in docs/SPEC.md that it checks."""
import random

import pytest

from conftest import Pid, q16

LIMITS = dict(lo=-500, hi=500)


@pytest.mark.parametrize("e", [-300, -37, -1, 0, 1, 7, 100, 333])
def test_R1_proportional_output_is_kp_times_error(lib, e):
    """R1: with ki = kd = 0 the output is kp * (setpoint - measurement), to within one unit of rounding."""
    p = Pid(lib, kp=0.5, **LIMITS)
    assert abs(p.update(e, 0) - 0.5 * e) <= 1


def test_R1_proportional_acts_on_the_difference_not_on_either_value(lib):
    p = Pid(lib, kp=2.0, **LIMITS)
    assert abs(p.update(1500, 1400) - 200) <= 1
    assert abs(p.update(-1400, -1500) - 200) <= 1
    assert abs(p.update(1400, 1500) + 200) <= 1


@pytest.mark.parametrize("e", [100, -100])
def test_R2_integral_adds_ki_times_error_every_sample(lib, e):
    """R2: with kp = kd = 0 and a constant error, the output grows by ki * error per sample."""
    p = Pid(lib, ki=0.01, **LIMITS)
    out = [p.update(e, 0) for _ in range(60)]
    for n in (1, 10, 30, 60):
        assert abs(out[n - 1] - 0.01 * e * n) <= 2, f"after {n} samples"


def test_R2_integral_keeps_its_fraction_of_a_unit(lib):
    """R2: a tiny ki * error (well under one unit per sample) must still add up: nothing may be thrown away by rounding each step."""
    p = Pid(lib, ki=0.002, **LIMITS)
    out = [p.update(10, 0) for _ in range(500)]                       # 0.02 per sample, so 10 after 500 samples
    assert abs(out[-1] - 10) <= 2


def test_R2_proportional_and_integral_add(lib):
    p = Pid(lib, kp=0.5, ki=0.01, **LIMITS)
    out = [p.update(100, 0) for _ in range(40)]
    assert abs(out[0] - 51) <= 2 and abs(out[39] - 90) <= 3


def test_R3_output_stays_inside_the_limits_when_the_terms_are_huge(lib):
    """R3: the output is always within [out_min, out_max], whatever the gains and the inputs."""
    p = Pid(lib, kp=100.0, ki=5.0, kd=20.0, lo=0, hi=1000)
    for sp, pv in [(30000, 0), (0, 30000), (-30000, 30000), (30000, -30000)] * 20:
        assert 0 <= p.update(sp, pv) <= 1000


def test_R3_limits_need_not_be_centred_on_zero(lib):
    """R3 and R1 together: with limits 200 to 300 a proportional-only controller is just kp * error, held to those limits. An integral that is
    clamped to the output limits must not drag a controller with ki = 0 up to the lower limit."""
    p = Pid(lib, kp=1.0, lo=200, hi=300)
    assert p.update(0, 1000) == 200
    assert p.update(1000, 0) == 300
    assert p.update(260, 200) == 200                                   # kp * 60 = 60 is below the lower limit
    assert p.update(450, 200) == 250


@pytest.mark.parametrize("sign", [1, -1])
def test_R4_integral_does_not_wind_up_while_the_output_is_saturated(lib, sign):
    """R4: after a long time stuck at a limit, the output must leave that limit within 3 samples of the error changing sign."""
    p = Pid(lib, kp=0.5, ki=0.05, **LIMITS)
    for _ in range(5000):
        out = p.update(sign * 4000, 0)
    assert out == sign * 500
    first_three = [p.update(0, sign * 200) for _ in range(3)]          # error now has the opposite sign
    assert any(abs(o) < 500 for o in first_three), "still stuck at the limit: the integral wound up"


def test_R4_integral_still_works_after_it_has_been_clamped(lib):
    p = Pid(lib, kp=0.0, ki=0.05, **LIMITS)
    for _ in range(3000):
        p.update(4000, 0)
    out = [p.update(-10, 0) for _ in range(10)]
    assert out[0] < 500 and out[-1] < out[0] - 3, "the output must start to fall at once and keep falling at ki * error per sample"


def test_R5_derivative_acts_on_the_measurement_not_on_the_error(lib):
    """R5: a setpoint step must not make the derivative term jump; only a change in the measurement does."""
    p = Pid(lib, kd=1.0, **LIMITS)
    p.update(0, 1000)
    for sp in (0, 800, -800, 0, 1200):
        assert p.update(sp, 1000) == 0, f"setpoint {sp}: the derivative reacted to the setpoint"


def test_R5_derivative_opposes_a_rising_measurement(lib):
    p = Pid(lib, kd=1.0, **LIMITS)
    p.update(0, 1000)
    assert abs(p.update(0, 1050) + 50) <= 1
    assert abs(p.update(0, 1020) - 30) <= 1
    assert abs(p.update(0, 1020)) <= 1


def test_R5_derivative_is_scaled_by_kd(lib):
    p = Pid(lib, kd=0.25, **LIMITS)
    p.update(0, 1000)
    assert abs(p.update(0, 1100) + 25) <= 1


@pytest.mark.parametrize("first_pv", [3000, -3000, 1])
def test_R6_the_first_sample_has_no_derivative_kick(lib, first_pv):
    """R6: the very first call (and the first after a reset) has no previous measurement, so the derivative term must be zero."""
    p = Pid(lib, kd=1.0, **LIMITS)
    assert p.update(first_pv, first_pv) == 0
    p.update(0, 0)
    p.reset()
    assert p.update(first_pv, first_pv) == 0


def test_R7_reset_forgets_the_integral_but_keeps_the_gains(lib):
    """R7: after pid_reset, an error of zero gives an output of zero, and the gains and limits still apply."""
    p = Pid(lib, kp=0.5, ki=0.05, kd=0.2, **LIMITS)
    for _ in range(300):
        p.update(4000, 0)
    p.reset()
    assert p.update(700, 700) == 0
    p.reset()
    assert abs(p.update(100, 0) - (50 + 5)) <= 2                       # kp*100 + ki*100, and nothing left over
    p.reset()
    assert p.update(100000 // 4, 0) == 500                             # the limits are still in force


def test_R7_a_fresh_pid_behaves_like_a_reset_one(lib):
    a, b = Pid(lib, kp=0.3, ki=0.02, kd=0.1, **LIMITS), Pid(lib, kp=0.3, ki=0.02, kd=0.1, **LIMITS)
    for _ in range(50):
        a.update(900, 100)
    a.reset()
    rng = random.Random(1)
    for _ in range(200):
        sp, pv = rng.randint(-2000, 2000), rng.randint(-2000, 2000)
        assert a.update(sp, pv) == b.update(sp, pv)


EXTREMES = [-32767, -32766, -1, 0, 1, 32766, 32767]
BIG_GAINS = [0.0, 0.0001, 1.0, 100.0, 255.0]


@pytest.mark.parametrize("kp", BIG_GAINS)
@pytest.mark.parametrize("ki", BIG_GAINS)
def test_R8_extreme_gains_and_inputs_never_overflow(lib, kp, ki):
    """R8: for inputs up to +-32767 and gains up to 255.0 no signed 32-bit overflow may happen (the sanitiser reports one as a failure),
    and the output stays inside the limits."""
    p = Pid(lib, kp=kp, ki=ki, kd=255.0, lo=-32767, hi=32767)
    for sp in EXTREMES:
        for pv in EXTREMES:
            assert -32767 <= p.update(sp, pv) <= 32767


def test_R8_random_walks_with_big_gains_stay_in_range_and_never_overflow(lib):
    rng = random.Random(7)
    p = Pid(lib, kp=200.0, ki=30.0, kd=120.0, lo=-1000, hi=1000)
    for _ in range(20000):
        out = p.update(rng.choice(EXTREMES + [rng.randint(-32767, 32767)]), rng.choice(EXTREMES + [rng.randint(-32767, 32767)]))
        assert -1000 <= out <= 1000


def test_R8_the_direction_is_right_at_the_extremes(lib):
    p = Pid(lib, kp=255.0, lo=-32767, hi=32767)
    assert p.update(32767, -32767) == 32767
    assert p.update(-32767, 32767) == -32767
