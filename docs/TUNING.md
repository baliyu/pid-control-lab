# Choosing the gains

The loop controls a process that behaves like a **first-order lag with a delay**: you change the output, and after a short dead time the process value
moves towards a new level along an exponential. A heater with a sensor behaves like this, and so does a PWM output through an RC filter into an ADC.
Three numbers describe it:

* **K**, the gain: how many counts the process value moves per unit of output, in steady state;
* **tau**, the time constant: how long it takes to cover 63 % of the way;
* **delay**: the dead time before anything starts to happen.

## 1. Measure the plant (the same method works on a real one)

Apply one step to the output with the loop open, log `t,u,pv` to a CSV and let it settle. `tools/identify.py` finds K, tau and the delay with the classic
two-point method and prints a first set of gains:

    python3 tools/identify.py step.csv            # lambda = tau
    python3 tools/identify.py step.csv --lam 0.15 # a gentler loop

Log a step from the simulated plant with `python3 tools/log_step.py step.csv` (options: `--output`, `--noise`, `--tau`, `--gain`, `--delay`); the real board will produce the same file format later.

## 2. Where the suggestion comes from

Lambda tuning (also called IMC): `kp = tau / (K * (lambda + delay))` and `ki = kp * Ts / tau`, where Ts is the sample period.
**lambda is the closed-loop time constant you ask for.** Small lambda: fast response, aggressive controller, little margin. Large lambda: slow and gentle.

## 3. Units, and why Q16.16

`kp` is in output units per count; `ki` is per sample. With the nominal plant `ki` comes out around 0.026, which in Q16.16 is about 1700. In
Q8.8 it would be 6.8, and rounding that to 7 would change your integral gain by about 4 %: that is the reason the gains are Q16.16. The tool prints the integers
for `core/gains.h`.

## 4. Experiments worth doing, and writing down in your own words

* Run with lambda = 0.5 tau, tau, 1.5 tau and 2 tau. For each, which requirement is the first to fail, and why? (With the nominal plant the aggressive end fails REQ-2, because it is too
  lively for plants that differ from the one you tuned on, and the sluggish end fails REQ-1, because it misses the settling-time limit. Check that this is what you see.)
* Set `kd` to 1.0. What does REQ-3 say, and why does derivative action make noise worse?
* Turn the integral off (`ki = 0`). Which requirement notices first?
* Look at `tools/step_plot.py` before and after each change. A number such as "overshoot 12 %" means more once you have seen the curve.
