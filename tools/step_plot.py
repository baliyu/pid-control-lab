#!/usr/bin/env python3
"""Plot how the controller in core/ behaves on the simulated plant, with the gains in core/gains.h (or the ones you give).

Four panels: the setpoint step on the nominal plant (with the +-2 % band and the output), the same step on 27 different plants (the robustness
requirement), a load disturbance, and the recovery from a long saturation. The requirement limits are drawn where they apply.

    python3 tools/step_plot.py                       # uses core/gains.h
    python3 tools/step_plot.py --gains 0.25 0.025 0  # try other gains (kp ki kd, real numbers) without editing anything
"""
import argparse
import itertools
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import requirements as R
from conftest import Ctrl, build, load_library
from plant import TS, Plant, simulate, step_metrics


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gains", nargs=3, type=float, metavar=("KP", "KI", "KD"), help="real-number gains instead of the ones in gains.h")
    ap.add_argument("--out", default=str(ROOT / "results" / "figures" / "step_response.png"))
    a = ap.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        so, result = build(tmp)
        if result.returncode != 0:
            print(result.stderr)
            return 1
        lib = load_library(so)
        make = (lambda: Ctrl(lib)) if a.gains is None else (lambda: Ctrl(lib, tuple(a.gains)))

        n, start = 700, 20
        sp = np.full(n, float(R.STEP_FROM))
        sp[start:] = R.STEP_TO
        band = 0.02 * (R.STEP_TO - R.STEP_FROM)

        fig, ax = plt.subplots(2, 2, figsize=(12, 8))
        nominal = simulate(make().step, sp, Plant())
        m = step_metrics(nominal, start, R.STEP_TO)
        a0 = ax[0, 0]
        a0.plot(nominal["t"], nominal["pv"], label="process value")
        a0.plot(nominal["t"], nominal["sp"], "k--", label="setpoint")
        a0.axhspan(R.STEP_TO - band, R.STEP_TO + band, color="g", alpha=0.15, label="+-2 %")
        a0.set_title(f"REQ-1 nominal: overshoot {m['overshoot_pct']:.1f} %, settle {m['settle_s']:.2f} s, steady error {m['steady_error']:.2f}")
        a1 = a0.twinx()
        a1.plot(nominal["t"], nominal["out"], color="tab:orange", alpha=0.6)
        a1.set_ylabel("output (per-mille)")
        a0.set_ylabel("counts")
        a0.legend(loc="lower right")

        worst = 0.0
        for g, tau, d in itertools.product([0.7, 1.0, 1.3], [0.05, 0.1, 0.2], [0, 2, 5]):
            lg = simulate(make().step, sp, Plant(gain=3.0 * g, tau=tau, delay=d))
            ax[0, 1].plot(lg["t"], lg["pv"], alpha=0.5, lw=0.8)
            worst = max(worst, step_metrics(lg, start, R.STEP_TO)["overshoot_pct"])
        ax[0, 1].axhline(R.STEP_TO, color="k", ls="--")
        ax[0, 1].set_title(f"REQ-2 27 different plants: worst overshoot {worst:.1f} % (limit {R.REQ2_MAX_OVERSHOOT_PCT:.0f} %)")

        nl, t_load = 900, 400
        load = np.zeros(nl)
        load[t_load:] = R.REQ4_LOAD
        s4 = np.full(nl, float(R.STEP_FROM))
        s4[start:] = R.STEP_TO
        lg = simulate(make().step, s4, Plant(), load=load)
        ax[1, 0].plot(lg["t"], lg["pv"])
        ax[1, 0].axhline(R.STEP_TO, color="k", ls="--")
        ax[1, 0].axvline(t_load * TS, color="r", ls=":", label=f"{R.REQ4_LOAD:.0f} count load switched on")
        ax[1, 0].set_title(f"REQ-4 disturbance: peak deviation {np.max(np.abs(lg['pv'][t_load:] - R.STEP_TO)):.0f} counts (limit {R.REQ4_MAX_PEAK_DEVIATION:.0f})")
        ax[1, 0].legend()

        back = 320
        s5 = np.full(nl, float(R.STEP_FROM))
        s5[start:back] = 20000
        s5[back:] = R.STEP_TO
        lg = simulate(make().step, s5, Plant())
        ax[1, 1].plot(lg["t"], lg["pv"], label="process value")
        ax[1, 1].plot(lg["t"], np.minimum(lg["sp"], 4095), "k--", label="setpoint (clipped for the plot)")
        ax[1, 1].set_title("REQ-5 windup: unreachable setpoint for 3 s, then back to 2000")
        ax[1, 1].legend()
        for axis in ax.flat:
            axis.set_xlabel("time (s)")
            axis.title.set_fontsize(9.5)
        fig.tight_layout()
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=130)
        print(f"nominal step: overshoot {m['overshoot_pct']:.1f} %, settle {m['settle_s']:.2f} s, steady error {m['steady_error']:.2f} counts")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
