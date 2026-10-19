#!/usr/bin/env python3
"""Builds the "predicted against measured" table in docs/ON_BOARD.md from the two captures kept in results/board/:
step_S500.csv (an open-loop step, columns t,u,pv) and run_R2000.csv (a closed-loop run, columns t,sp,u,pv). The numbers in the guide are never typed by hand.

    python3 tools/board_report.py            write the table into docs/ON_BOARD.md (between the markers <!-- board:start --> and <!-- board:end -->)
    python3 tools/board_report.py --check    only check that the table in the guide is current (the tests do this)
    python3 tools/board_report.py --print    print the table
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import numpy as np

import identify
import score_run

START, END = "<!-- board:start -->", "<!-- board:end -->"
STEP_CSV = ROOT / "results" / "board" / "step_S500.csv"
RUN_CSV = ROOT / "results" / "board" / "run_R2000.csv"
GUIDE = ROOT / "docs" / "ON_BOARD.md"


def load(path, columns):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return [np.array([float(r[c]) for r in rows]) for c in columns]


def measure(step_csv=STEP_CSV, run_csv=RUN_CSV):
    t, u, pv = load(step_csv, ("t", "u", "pv"))
    k0 = int(np.argmax(np.abs(np.diff(u)))) + 1
    model = identify.identify(t, u, pv)
    t2, sp, u2, pv2 = load(run_csv, ("t", "sp", "u", "pv"))
    m = score_run.score(t2, sp, pv2)
    hold = slice(-300, None)
    return {"rest": float(np.mean(pv[:k0])), "final": float(np.mean(pv[-100:])), "gain": model["gain"], "tau": model["tau"], "delay": model["delay"],
            "overshoot": m["overshoot_pct"], "settle": m["settle_s"], "steady": m["steady_error"],
            "bias": float(np.mean(pv2[hold]) - sp2_target(sp)), "noise": float(np.std(pv2[hold])), "u_hold": float(np.mean(u2[hold]))}


def sp2_target(sp):
    return float(sp[-1])


def table(m):
    rows = [
        ("Resting reading (output 0, DAC at 5 %)", "about 204 counts (0.165 V)", f"{m['rest']:.0f} counts"),
        ("Reading after a step to output 500", "about 1945 counts", f"{m['final']:.0f} counts"),
        ("Plant gain from `identify.py`", "3.48 counts per per-mille", f"{m['gain']:.2f} counts per per-mille"),
        ("Time constant from `identify.py`", "10 ms", f"{m['tau'] * 1000:.1f} ms"),
        ("Delay from `identify.py`", "under 1 ms", f"{m['delay'] * 1000:.1f} ms"),
        ("Closed loop to 2000 counts: highest reading above the target", "under 1 %", f"{m['overshoot']:.1f} %"),
        ("Closed loop to 2000 counts: settling time (+-2 %)", "about 43 ms", f"{m['settle'] * 1000:.0f} ms"),
        ("Closed loop to 2000 counts: average distance from the target over the last 0.3 s (this includes the reading's own noise)", "under 1 count", f"{m['steady']:.2f} counts"),
        ("Closed loop to 2000 counts: average reading minus the target over the last 0.3 s (the bias the integral removes)", "0", f"{m['bias']:+.2f} counts"),
        ("Noise of the reading while holding (standard deviation)", "about 0.6 counts in the model", f"{m['noise']:.1f} counts"),
        ("Output needed to hold 2000 counts", "about 516 per-mille", f"{m['u_hold']:.0f} per-mille"),
    ]
    lines = ["| Quantity | Predicted by the PC model | Measured on the board |", "|---|---|---|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    return "\n".join(lines)


def block(m):
    return f"{START}\n{table(m)}\n{END}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="only check that the guide is current")
    mode.add_argument("--print", action="store_true", dest="show", help="print the table")
    ap.add_argument("--step", default=str(STEP_CSV))
    ap.add_argument("--run", default=str(RUN_CSV))
    ap.add_argument("--guide", default=str(GUIDE))
    a = ap.parse_args(argv)
    try:
        m = measure(a.step, a.run)
    except (OSError, ValueError, KeyError) as e:
        print(f"board_report: cannot use the captures: {e}", file=sys.stderr)
        return 1
    if a.show:
        print(table(m))
        return 0
    guide = Path(a.guide)
    text = guide.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(f"board_report: {guide} has no {START} ... {END} markers to fill.", file=sys.stderr)
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + block(m) + tail
    if a.check:
        if new != text:
            print("board_report: the table in docs/ON_BOARD.md does not match the captures in results/board/. Run  python3 tools/board_report.py", file=sys.stderr)
            return 1
        print("docs/ON_BOARD.md is up to date")
        return 0
    guide.write_text(new, encoding="utf-8")
    print(f"updated {guide.name} from {Path(a.step).name} and {Path(a.run).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
