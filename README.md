<!-- pid-lab -->
# stm32-pid-control-lab

A fixed-point PID controller and a sensor-fault supervisor in C, written for an STM32 (Cortex-M0+, no floating-point unit) and tested from Python against a
simulated plant. The emphasis is on method: the requirements are written down as numbers first, the tests are built to catch bugs (including overflow, with the
undefined-behaviour sanitiser), and the gains are chosen by measuring the plant and then tuning, not by guessing.

## Status

- [ ] PID controller written (`core/pid.c`): rules R1 to R8 in [docs/SPEC.md](docs/SPEC.md)
- [ ] Sensor supervisor written (`core/supervisor.c`): rules S1 to S4
- [ ] Gains chosen from a measured plant (`core/gains.h`, [docs/TUNING.md](docs/TUNING.md))
- [ ] Closed-loop requirements REQ-1 to REQ-7 met on the simulated plant
- [ ] On-board loop: the controller running on the STM32 against a real RC-filter plant, with a hardware-in-the-loop test runner (not started)

## Run it

    bash tools/setup_ubuntu.sh                       # once: a C compiler and a Python environment
    source ~/.venvs/stm32-pid-control-lab/bin/activate
    python -m pytest -q                              # everything
    python tools/step_plot.py                        # the four-panel picture of the closed loop
    python tools/identify.py step.csv                # fit a plant model to a logged step and suggest gains

## What is tested

| File | What it checks |
|---|---|
| `tests/test_pid_unit.py` | each PID rule on its own: proportional, integral (including tiny steps), limits, anti-windup, derivative on measurement, first sample, reset, and no overflow at the extremes |
| `tests/test_supervisor.py` | the fault logic to the sample: exactly 5 bad readings to declare, exactly 20 good to clear, exact limits, restarts |
| `tests/test_closed_loop.py` | the loop against the simulated plant: step response, 27 different plants, noise, a load disturbance, windup, a failed sensor |
| `tests/test_hygiene.py` | no compiler warnings, no floating point, gains in range |
| `tests/test_plant.py`, `test_identify.py`, `test_step_plot.py` | the test equipment itself (the simulator, the plant-fitting tool, the plotting tool), so a failing loop test means the controller is at fault |

The simulated plant (`tests/plant.py`) is a first-order lag with a transport delay, a load input, ADC noise and 12-bit quantisation. The limits are in
`tests/requirements.py`, in one place.

## Layout

    core/    pid.[ch]  supervisor.[ch]  gains.h   control.[ch] (calls the PID and then the supervisor; this is what the firmware will call each sample)
    tests/   the pytest suite, the simulated plant and a small C wrapper that lets Python call the C code
    tools/   identify.py (plant model and gains from a logged step)  step_plot.py  setup_ubuntu.sh
    docs/    SPEC.md (the rules)  TUNING.md (how the gains are chosen)

## Honest limits

- Everything above runs against a **simulated** plant. Nothing here has run on a board yet, and no claim is made about a real heater or a real RC filter until the last item in the status list is ticked.
- The plant is first-order with a delay. Real processes can have a second pole, a nonlinear gain or a sensor with its own lag.
- The tests run on a PC (x86-64): they find logic and overflow bugs, but not timing, stack use or compiler differences on the Cortex-M0+.
- The sample rate is fixed at 100 Hz; jitter in the real sample period is not modelled.
