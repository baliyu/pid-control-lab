#!/usr/bin/env python3
"""Scores a closed-loop run from the board (a CSV with the columns t,sp,u,pv) against the step requirement REQ-1 of tests/requirements.py.

REQ-1 was written for the simulated plant, whose time constant is 100 ms. The circuit on the Feather has a time constant of 10 ms (100 kOhm x 100 nF)
and runs ten times faster, so every time in the requirement is multiplied by 0.1 (TIME_SCALE); overshoot and steady-state error are unchanged.

    python3 tools/score_run.py run.csv
    python3 tools/score_run.py run.csv --plot results/figures/feather_run.png
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import numpy as np

import requirements as R

TIME_SCALE = 0.1


def score(t, sp, pv):
    """Overshoot (% of the step), settling time to +-2 % of the step, and steady-state error over the last 0.3 s, for the setpoint step in the run."""
    start = int(np.argmax(sp != sp[0]))
    if start == 0:
        raise ValueError("the setpoint never changes in this run: there is no step to score")
    target = sp[-1]
    size = target - sp[0]
    sign = 1.0 if size > 0 else -1.0
    ts = float(np.median(np.diff(t)))
    outside = np.nonzero(np.abs(pv[start:] - target) > 0.02 * abs(size))[0]
    settle = 0.0 if len(outside) == 0 else (float("inf") if outside[-1] == len(pv[start:]) - 1 else (outside[-1] + 1) * ts)
    n_last = max(1, int(round(0.3 / ts)))
    return {"overshoot_pct": max(0.0, float(np.max(sign * (pv[start:] - target)))) / abs(size) * 100.0, "settle_s": settle,
            "steady_error": float(np.mean(np.abs(pv[-n_last:] - target)))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--plot", help="also write a picture of the run to this file")
    a = ap.parse_args(argv)
    try:
        with open(a.csv, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        print(f"score_run: {a.csv} does not exist. tools/from_monitor.py has to succeed first (it prints 'wrote {a.csv}').", file=sys.stderr)
        return 1
    if not rows or not {"t", "sp", "u", "pv"} <= set(rows[0]):
        print(f"score_run: {a.csv} needs the columns t,sp,u,pv, which a closed-loop run (R2000) prints; a step capture (S500) has t,u,pv.", file=sys.stderr)
        return 1
    t, sp, u, pv = (np.array([float(r[k]) for r in rows]) for k in ("t", "sp", "u", "pv"))
    try:
        m = score(t, sp, pv)
    except ValueError as e:
        print(f"score_run: {e}", file=sys.stderr)
        return 1
    limits = {"overshoot_pct": R.REQ1_MAX_OVERSHOOT_PCT, "settle_s": R.REQ1_MAX_SETTLE_S * TIME_SCALE, "steady_error": R.REQ1_MAX_STEADY_ERROR}
    ok = True
    for key, label, unit in (("overshoot_pct", "overshoot", "%"), ("settle_s", "settling time", "s"), ("steady_error", "steady-state error", "counts")):
        good = m[key] <= limits[key]
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}  {label}: {m[key]:.3f} {unit} (limit {limits[key]:.3f})")
    print(f"output range {u.min():.0f} to {u.max():.0f} per-mille; setpoint {sp[0]:.0f} -> {sp[-1]:.0f} counts")
    if a.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(t, pv, label="process value (ADC counts)")
        ax.plot(t, sp, "k--", label="setpoint")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("counts")
        ax2 = ax.twinx()
        ax2.plot(t, u, color="tab:orange", alpha=0.6, label="output (per-mille)")
        ax2.set_ylabel("output (per-mille)")
        ax.set_title(f"overshoot {m['overshoot_pct']:.1f} %, settle {m['settle_s'] * 1000:.0f} ms, steady error {m['steady_error']:.2f} counts")
        ax.legend(loc="lower right")
        fig.tight_layout()
        Path(a.plot).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(a.plot, dpi=130)
        print(f"wrote {a.plot}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
