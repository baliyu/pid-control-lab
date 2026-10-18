# Running the controller on the Feather M0

The same C controller that passed every test against the simulated plant now drives a real circuit: the Feather's DAC feeds an RC filter, the ADC reads the
filter's output, and the PID holds that voltage at a target, exactly as it would hold a temperature.

```
A0 (DAC) ---[ 100 kOhm ]---+--- A1 (ADC)
                           |
                      [ 100 nF, marked 104 ]
                           |
GND -----------------------+
```

The node between the resistor and the capacitor is the "process value". It follows the DAC with a time constant of 100 kOhm x 100 nF = 10 ms, ten times
faster than the simulated plant (100 ms). So the loop runs at 1 kHz, not 100 Hz: measured in samples the plant is the same, and the tuned gains carry over.

## What the PC model predicts

The sketch was run on the PC against a model of this circuit (`tests/test_feather_sketch.py`). These numbers are predictions; the point of the session is to find out
where the real circuit differs.

| Quantity | Predicted | Measured on the board |
|---|---|---|
| Resting reading (output 0, DAC at 5 %) | about 204 counts (0.165 V) | |
| Reading after a step to output 500 | about 1945 counts | |
| Plant gain from `identify.py` | 3.48 counts per per-mille | |
| Time constant from `identify.py` | 10 ms | |
| Delay from `identify.py` | under 1 ms | |
| Closed loop to 2000 counts: overshoot | under 1 % | |
| Closed loop to 2000 counts: settling time (+-2 %) | about 43 ms | |
| Closed loop to 2000 counts: steady-state error | under 1 count | |
| Output needed to hold 2000 counts | about 516 per-mille | |

Real parts differ from the model: a 100 nF ceramic capacitor can be 10 to 20 % off its marking (more with voltage and temperature), the resistor is usually 5 %, and the
converters have offsets. A gain or time constant within about 20 % of the prediction is normal. A big difference is worth understanding.

## Steps

1. **Wire it** as above (the diagram in the chat, or the table here): A0 to the resistor, the resistor to the node, A1 to the node, the capacitor from the node to GND.
2. **Copy the C core next to the sketch** (WSL). The Arduino IDE only compiles what is in the sketch folder:

       cd /mnt/c/stm32-pid-control-lab
       sh firmware/feather_m0/sync_core.sh

3. **Upload** (Windows, Arduino IDE): open `C:\stm32-pid-control-lab\firmware\feather_m0\feather_m0.ino`, choose the board *Adafruit Feather M0* and the port, press Upload.
4. **Talk to it.** Open the Serial Monitor, set the line ending to *Newline*, and send:
   * `I` prints the settings and the gains.
   * `Z` puts the output at rest. The green LED does not follow it (the DAC pin has no LED).
   * `S500` records an open-loop step: 0.1 s at rest, then the output steps to 500 and 0.5 s more is recorded.
   * `R2000` records a closed-loop run: the PID takes the reading from its resting value to 2000 counts.
5. **Save a capture.** After the line `# done`, select everything in the Serial Monitor, copy, and paste into a text file in the repository folder (for example `raw_step.txt`).
6. **Clean it and analyse it** (WSL):

       python tools/from_monitor.py raw_step.txt step_board.csv
       python tools/identify.py step_board.csv
       python tools/from_monitor.py raw_run.txt run_board.csv
       python tools/score_run.py run_board.csv --plot results/figures/feather_run.png

   `identify.py` prints the plant it found and a set of gains. `score_run.py` scores the run against REQ-1 with the times scaled by 0.1 and writes a picture.
7. **Fill in the last column of the table** with what you measured, and write down what surprised you.

## If something is off

* **Resting reading near 0:** A1 is shorted to ground, or the capacitor is shorted, or something holds the node low. **Near 4095:** A1 touches 3.3 V.
* **A reading around 1500 to 1900 that wobbles by a hundred counts or more, with a 50 Hz ripple, and does not change when the output steps:** A1 is *floating*: it is not
  connected to the node, or to anything. An unconnected analogue input picks up mains hum and reads a meaningless middle value. `tools/identify.py` refuses such a capture and
  says so (the first real capture from this board looked exactly like this: `tests/data/board_step_floating_input.csv`).
* **Three quick tests to find the fault** (unplug USB while moving wires, then plug in and send `S500` as before):
  1. Join the A0 wire *straight* to the A1 wire, with no resistor and no capacitor. The reading should jump from about 204 to about 1945 within a millisecond or two.
  2. If that works, put the resistor between them and the capacitor from the node to GND, and repeat.
  3. If test 1 still reads about 1700 and ignores the output, the fault is in the A0 or A1 connection itself or in the board: check that the header pins are soldered, that
     each wire is in the right row of the breadboard, and that the wire ends really touch the pins.
* **Resting reading below 50 counts:** the supervisor treats that as a shorted sensor and holds the output at 0 (the tests include this case). The live zero leaves only
  about 155 counts of margin, so a leaky capacitor or a load on the node can trip it. Check the capacitor and the wiring before anything else.
* **Resting reading below 50 counts:** the supervisor treats that as a shorted sensor and holds the output at 0 (the tests include this case). The live zero leaves only
  about 155 counts of margin, so a leaky capacitor or a load on the node can trip it. Check the capacitor and the wiring before anything else.
* **The output never leaves 0 in a closed-loop run:** the same cause. Look at the first lines of the capture.
* **Gain or time constant far from the prediction:** run `identify.py` on your own capture. It prints gains for the plant you actually have; put them in `core/gains.h`, run
  `python -m pytest -q`, run `sync_core.sh` again and upload.
* **Noisy readings (a few counts):** normal for a 12-bit ADC at 1 kHz; the requirement allows for it.

## What a good result lets you claim

That the controller from the simulated tests ran on real hardware, how the measured plant compared with the prediction, and how the closed loop scored against the requirement.
It does not show a thermal process, long-term drift, or the STM32 port: the loop ran on a Feather M0 (SAMD21, Cortex-M0+).
