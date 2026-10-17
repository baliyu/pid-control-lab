# What you are asked to write

Three files are yours: `core/pid.c` (with the state in `core/pid.h`), `core/supervisor.c` (with its state in `core/supervisor.h`), and the three
numbers in `core/gains.h`. Everything else is provided: the glue that calls them (`core/control.c`), the simulated plant, the tests and the tools.

Every test names the rule it checks. Run `pytest -q tests/test_pid_unit.py` to work on the PID, `tests/test_supervisor.py` for the supervisor,
and `tests/test_closed_loop.py` once both work and you have chosen gains.

## Numbers

* The target has no floating-point unit. **No `float`, `double` or `math.h`** (a test looks for them).
* **Gains are Q16.16**: real value = raw / 65536, so 1.0 is `PID_ONE` (65536). Valid range 0.0 to 255.0 (raw 0 to 16 711 680).
* **Gains are per sample.** `ki` already contains the sample period and `kd` is divided by it, so `pid_update` takes no time argument.
* Setpoint and measurement are integers in the same units (ADC counts), valid range **-32767 to +32767**. The output is an integer in output units.
* **No signed 32-bit overflow is allowed for any valid input and gain.** The tests are built with the undefined-behaviour sanitiser, so an overflow fails
  the test that caused it. (Think about how big `kp * error` can get, and what size the sum of the three terms needs.)

## The PID (`core/pid.c`)

The textbook form, for one sample: `output = kp * e  +  I  +  kd * (previous_measurement - measurement)`, where `e = setpoint - measurement`
and `I` accumulates `ki * e`. The rules below say what has to be true; how you arrange it is up to you.

| Rule | Statement |
|---|---|
| **R1** | With `ki = kd = 0` the output is `kp * e`, to within one unit of rounding, held inside the limits. It depends on the difference only. |
| **R2** | With `kp = kd = 0` and a constant error, the output grows by `ki * e` per sample. A very small `ki * e` (well under one output unit per sample) must still add up over many samples: do not round away the fraction every step. |
| **R3** | The output is **always** inside `[out_min, out_max]`, whatever the gains and inputs, and the limits need not include zero or be symmetric. A controller with `ki = 0` and limits 200 to 300 is just `kp * e` held to 200..300. |
| **R4** | Anti-windup: after a long time stuck at a limit, the output must leave that limit within 3 samples of the error changing sign. (Two common ways: clamp the integral, or stop integrating while saturated in the direction that makes it worse. Choose one and be able to say why.) |
| **R5** | The derivative acts on the **measurement**, not on the error, so a setpoint step does not make it jump ("derivative kick"). It opposes a rising measurement. |
| **R6** | The first call after `pid_init` or `pid_reset` has no previous measurement, so its derivative term must be zero. |
| **R7** | `pid_reset` forgets the integral and the history and keeps the gains and limits. A fresh controller and a reset one behave identically. |
| **R8** | No overflow, and the output stays in range, for any inputs in the valid range and any gains from 0.0 to 255.0. |

## The supervisor (`core/supervisor.c`)

It watches the raw ADC reading. A shorted sensor reads near 0 and an open one near full scale; a controller that believes a shorted thermistor
can drive a heater flat out. Constants are in `core/supervisor.h`.

| Rule | Statement |
|---|---|
| **S1** | A reading from `SUP_ADC_MIN` (50) to `SUP_ADC_MAX` (4045) inclusive is good. While all readings are good the output is passed through unchanged and there is no fault. |
| **S2** | A fault is declared on the 5th bad reading **in a row** (`SUP_FAULT_AFTER`). The first four pass the output through (it may be a glitch); from the 5th on, the output is `SUP_SAFE_OUTPUT` (0). |
| **S3** | Bad readings must be consecutive: one good reading in between starts the count again. |
| **S4** | During a fault the output stays safe until 20 good readings **in a row** (`SUP_CLEAR_AFTER`); the 20th passes the output through again. A bad reading during recovery restarts the count of good ones. A new fault needs five bad readings again. |

`core/control.c` (provided) runs the PID, then the supervisor, and resets the PID on every sample during a fault so that it cannot wind up on a reading that
means nothing.

## The closed-loop requirements

They are in `tests/requirements.py`, each one a number written down before you see the result:

| | |
|---|---|
| **REQ-1** | Step from 300 to 2000 counts on the nominal plant: overshoot, settling time and steady-state error within the limits. |
| **REQ-2** | The same gains work when the plant differs: gain x0.7 to x1.3, time constant 0.05 to 0.2 s, delay 0 to 5 samples (27 plants). |
| **REQ-3** | Sensor noise of 2 counts does not make the actuator chatter. |
| **REQ-4** | A 400 count load disturbance is rejected within the limits. |
| **REQ-5** | Recovery from a long saturation (the windup trap). |
| **REQ-6** | A shorted or open sensor makes the output exactly 0 from the 5th bad sample until recovery, and the loop then resumes. |
| **REQ-7** | The output stays inside 0 to 1000 in every scenario. |

## Order of work that tends to go well

1. `pid.c` with only `kp` (R1, R3), then add the integral (R2, R4), then the derivative (R5, R6), then reset (R7), then look at overflow (R8).
2. `supervisor.c` (S1 to S4).
3. Characterise the plant and choose the gains (`docs/TUNING.md`), then run the closed-loop tests and `tools/step_plot.py`.
