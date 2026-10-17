"""The closed-loop requirements, in one place. Each number is a limit the controller must meet on the simulated plant (tests/plant.py).

Change a limit only if you can say why; the point of a requirement is that it is written down before you see the result.
The plant: first-order lag, time constant 0.1 s, gain 3 counts per per-mille, a delay of 2 samples, a sensor that reads 300 counts at rest.
"""

# REQ-1: a setpoint step from 300 to 2000 counts on the nominal plant
STEP_FROM, STEP_TO = 300, 2000
REQ1_MAX_OVERSHOOT_PCT = 10.0        # of the step size
REQ1_MAX_SETTLE_S = 0.8              # to stay within +-2 % of the step size
REQ1_MAX_STEADY_ERROR = 3.0          # counts, averaged over the last second

# REQ-2: the same step on plants that differ from the one you tuned on: gain x0.7 to x1.3, time constant 0.05 s to 0.2 s, delay 0 to 5 samples
REQ2_MAX_OVERSHOOT_PCT = 30.0
REQ2_MAX_STEADY_ERROR = 5.0          # after 6 s: this is the "it must not oscillate or run away" limit

# REQ-3: sensor noise of 2 counts rms, holding 2000 counts
REQ3_NOISE_COUNTS = 2.0
REQ3_MAX_OUTPUT_STD = 3.0            # per-mille: the actuator must not chatter
REQ3_MAX_STEADY_ERROR = 3.0

# REQ-4: a load that pulls the process value down by 400 counts, switched on while holding 2000 counts
REQ4_LOAD = 400.0
REQ4_MAX_PEAK_DEVIATION = 300.0      # counts
REQ4_MAX_RECOVERY_S = 1.0            # back to within +-40 counts

# REQ-5: windup. The setpoint is far beyond what the plant can reach for 3 s, then returns to 2000
REQ5_MAX_RECOVERY_S = 1.0            # back within +-2 % of the step size after the setpoint returns

# REQ-6: the sensor fails (shorted: reads 0, or open: reads 4095) for 1 s, then comes back
REQ6_MAX_RESUME_S = 1.5              # after it comes back, the process value is back within +-2 % of the step size

# REQ-7: the output is always inside 0 to 1000 (every scenario above is checked for this)
