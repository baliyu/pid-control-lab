"""A simulated plant for the closed-loop tests: a first-order lag with a transport delay, a load disturbance, ADC noise and 12-bit quantisation.

It stands in for a real process such as a heater and a thermistor, or a PWM output through an RC filter into an ADC. Units:
the control output is per-mille (0 to 1000), the process value is ADC counts (0 to 4095), one step is one sample of TS seconds.
"""
import math
from dataclasses import dataclass

import numpy as np

TS = 0.01                  # sample period in seconds (100 Hz, the same as CONTROL_HZ in core/gains.h)
ADC_MAX = 4095
OUT_MIN, OUT_MAX = 0, 1000


@dataclass(frozen=True)
class Plant:
    gain: float = 3.0       # counts per per-mille of output, in steady state (so full output reaches offset + 3000 counts)
    tau: float = 0.1        # time constant in seconds
    offset: float = 300.0   # what the sensor reads with no output at all: ambient temperature, never zero
    delay: int = 2          # transport delay in samples (the output takes this many samples to start to act)
    noise: float = 0.0      # ADC noise, counts rms


def simulate(step, setpoint, plant=Plant(), load=None, adc_override=None, seed=1):
    """Run the closed loop. `step(setpoint, adc)` is the controller (one call per sample) and returns the actuator output.

    setpoint:     one value per sample (counts)
    load:         optional, one value per sample: counts the process value is pulled down by, in steady state
    adc_override: optional list with one entry per sample, None or a count that the ADC reports instead of the real value (a broken sensor)
    Returns a dict of numpy arrays: t, sp, pv (the true process value, before noise), adc (what the controller saw), out (what the plant received).
    """
    n = len(setpoint)
    rng = np.random.RandomState(seed)
    alpha = 1.0 - math.exp(-TS / plant.tau)
    pipe = [0] * plant.delay                      # outputs that have been sent but have not started to act yet
    x = 0.0                                       # how far the process value is above its offset
    log = {k: np.zeros(n) for k in ("t", "sp", "pv", "adc", "out")}
    for k in range(n):
        pv = max(0.0, min(float(ADC_MAX), plant.offset + x))
        adc = int(round(pv + (rng.normal(0.0, plant.noise) if plant.noise else 0.0)))
        adc = max(0, min(ADC_MAX, adc))
        if adc_override is not None and adc_override[k] is not None:
            adc = adc_override[k]
        out = int(step(int(setpoint[k]), adc))
        pipe.append(out)
        acting = pipe.pop(0)
        target = plant.gain * max(OUT_MIN, min(OUT_MAX, acting)) - (load[k] if load is not None else 0.0)
        x += alpha * (target - x)
        log["t"][k], log["sp"][k], log["pv"][k], log["adc"][k], log["out"][k] = k * TS, setpoint[k], pv, adc, out
    return log


def step_metrics(log, start, final, band=0.02):
    """Numbers for a setpoint step from the first value to `final` that happened at sample `start`.

    overshoot_pct:  how far the process value went past the final value, as a percentage of the step size
    settle_s:       how long after the step until the process value stays within +-band (a fraction of the step size) of the final value
    steady_error:   the average distance from the final value over the last second
    """
    pv, t = log["pv"], log["t"]
    size = abs(final - log["sp"][start - 1]) if start > 0 else abs(final)
    sign = 1.0 if final >= (log["sp"][start - 1] if start > 0 else 0) else -1.0
    over = max(0.0, float(np.max(sign * (pv[start:] - final))))
    outside = np.nonzero(np.abs(pv[start:] - final) > band * size)[0]
    settle = 0.0 if len(outside) == 0 else (outside[-1] + 1) * TS
    if len(outside) and outside[-1] == len(pv[start:]) - 1:
        settle = float("inf")
    return {"overshoot_pct": 100.0 * over / size, "settle_s": settle,
            "steady_error": float(np.mean(np.abs(pv[-int(1 / TS):] - final)))}
