#!/usr/bin/env python3
"""Fit a first-order lag with a delay to a logged open-loop step response, and suggest starting gains.

Input: a CSV with the columns  t,u,pv  (seconds, actuator output, process value in counts) in which the output makes ONE step
(for example 0 to 500 per-mille) and the process value then settles. The same tool serves the simulated plant and, later, a real one.

Method (the classic two-point method): smooth the response, find the times at which it has covered 28.3 % and 63.2 % of its way,
then  tau = 1.5 * (t63 - t28)  and  delay = t63 - tau. The gain is the final change in pv divided by the change in the output.

Suggested gains (lambda tuning, also called IMC): kp = tau / (K * (lambda + delay)),  ki = kp * Ts / tau,  kd = 0, with lambda = tau by default;
a larger lambda gives a slower, gentler loop. They are printed as real numbers and as Q16.16 integers ready for core/gains.h.
"""
import argparse
import csv
import sys

import numpy as np


def identify(t, u, pv, smooth=5):
    t, u, pv = (np.asarray(a, dtype=float) for a in (t, u, pv))
    if len(t) < 30:
        raise ValueError("need at least 30 samples")
    jump = np.abs(np.diff(u))
    k0 = int(np.argmax(jump)) + 1                                   # first sample with the new output
    if jump.max() == 0:
        raise ValueError("the output never changes: there is no step to analyse")
    ts = float(np.median(np.diff(t)))
    du = float(np.mean(u[k0:]) - np.mean(u[:k0]))
    base = float(np.mean(pv[max(0, k0 - 10):k0]))
    final = float(np.mean(pv[-max(5, len(pv) // 20):]))
    dpv = final - base
    noise = max(float(np.std(pv[max(0, k0 - 50):k0])), 0.5)          # how much the reading wobbles by itself before the step
    if abs(dpv) < 6.0 * noise:
        raise ValueError(f"the process value did not respond to the step: it changed by {dpv:+.0f} counts while it wobbles by about {noise:.0f} counts on its own. "
                         "Check that the sensor input is really connected to the plant, and that the output drives the plant.")
    k = dpv / du
    sm = np.convolve(pv, np.ones(smooth) / smooth, mode="same")
    sm[:smooth], sm[-smooth:] = pv[:smooth], pv[-smooth:]

    def crossing(frac):
        level = base + frac * dpv
        above = (sm[k0:] - level) * np.sign(dpv) >= 0
        i = int(np.argmax(above))
        if not above[i]:
            raise ValueError("the response never reaches that level: record a longer step")
        if i == 0:
            return t[k0] - t[k0]
        y0, y1 = sm[k0 + i - 1], sm[k0 + i]
        return (t[k0 + i - 1] - t[k0]) + (level - y0) / (y1 - y0) * ts

    t28, t63 = crossing(0.283), crossing(0.632)
    tau = 1.5 * (t63 - t28)
    if not np.isfinite(tau) or tau <= 0.0:
        raise ValueError("could not fit a time constant: the response is too fast for the sample period, or too noisy. Record a step with a slower plant or a faster sample rate.")
    delay = max(0.0, t63 - tau)
    return {"gain": k, "tau": tau, "delay": delay, "ts": ts}


def suggest(model, lam=None):
    k, tau, delay, ts = model["gain"], model["tau"], model["delay"], model["ts"]
    if k <= 0.0 or tau <= 0.0:
        raise ValueError(f"cannot suggest gains for a plant with gain {k:.3f} and time constant {tau:.4f} s: the controller expects a plant where more output raises the reading.")
    lam = tau if lam is None else lam
    kp = tau / (k * (lam + delay + ts / 2))
    ki = kp * ts / tau
    return {"kp": kp, "ki": ki, "kd": 0.0, "lambda": lam}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="file with columns t,u,pv")
    ap.add_argument("--lam", type=float, help="lambda in seconds (default: tau)")
    a = ap.parse_args(argv)
    with open(a.csv, newline="") as f:
        rows = list(csv.DictReader(f))
    try:
        model = identify([r["t"] for r in rows], [r["u"] for r in rows], [r["pv"] for r in rows])
        g = suggest(model, a.lam)
    except ValueError as e:
        print(f"identify: {e}", file=sys.stderr)
        return 1
    print(f"plant:   gain {model['gain']:.3f} counts per output unit, time constant {model['tau']:.3f} s, delay {model['delay']:.3f} s "
          f"(sample period {model['ts']:.3f} s)")
    print(f"gains:   kp {g['kp']:.4f}  ki {g['ki']:.5f}  kd {g['kd']:.1f}   (lambda {g['lambda']:.3f} s)")
    print(f"gains.h: #define CONTROL_KP_Q16 {round(g['kp'] * 65536)}   #define CONTROL_KI_Q16 {round(g['ki'] * 65536)}   #define CONTROL_KD_Q16 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
