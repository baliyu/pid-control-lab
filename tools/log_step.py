#!/usr/bin/env python3
"""Log an open-loop step of the simulated plant to a CSV that tools/identify.py can read (columns t,u,pv: seconds, output, sensor reading in counts).

Open loop means no controller: the output is held at 0 for the first 0.2 s, then stepped to --output (default 500 per-mille), and the plant is recorded
for --seconds. The real board will produce the same file format later, so the same tool will fit a real plant.

    python3 tools/log_step.py step.csv
    python3 tools/log_step.py step.csv --output 400 --noise 2 --tau 0.2
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import numpy as np

from plant import TS, Plant, simulate


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="file to write")
    ap.add_argument("--output", type=float, default=500.0, help="the output the step goes to, in per-mille (default 500)")
    ap.add_argument("--seconds", type=float, default=5.0, help="how long to record (default 5)")
    ap.add_argument("--noise", type=float, default=1.0, help="sensor noise in counts rms (default 1)")
    ap.add_argument("--gain", type=float, default=3.0, help="plant gain, counts per per-mille (default 3)")
    ap.add_argument("--tau", type=float, default=0.1, help="plant time constant in seconds (default 0.1)")
    ap.add_argument("--delay", type=int, default=2, help="plant delay in samples (default 2)")
    ap.add_argument("--seed", type=int, default=2, help="noise seed (default 2)")
    a = ap.parse_args(argv)

    n, at = int(round(a.seconds / TS)), int(round(0.2 / TS))
    u = np.zeros(n)
    u[at:] = a.output
    it = iter(u)
    log = simulate(lambda sp, adc: next(it), np.zeros(n), Plant(gain=a.gain, tau=a.tau, delay=a.delay, noise=a.noise), seed=a.seed)
    with open(a.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "u", "pv"])
        for t, out, adc in zip(log["t"], u, log["adc"]):
            w.writerow([f"{t:.2f}", f"{out:.0f}", f"{adc:.0f}"])
    print(f"wrote {a.csv}: {n} samples, the output steps from 0 to {a.output:.0f} at {at * TS:.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
