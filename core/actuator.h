/* actuator.h - turns the controller's output (0 to 1000 per-mille) into the number to write to a DAC or a PWM compare register.
 *
 * "Live zero": the output is never driven all the way to 0 V or to the supply. Per-mille 0 maps to 5 % of full scale and per-mille 1000 to 90 %.
 * The reason is the sensor supervisor: it treats a reading below 50 counts as a shorted sensor and one above 4045 as an open one, so a real
 * signal must stay clear of both ends, exactly as the 4 to 20 mA signal in industry never uses 0 mA for a valid value. On a 3.3 V board the
 * circuit then rests at about 0.165 V and tops out at about 2.97 V.
 *
 * Pure integer arithmetic, no floating point, no hardware: it is tested on the PC (tests/test_actuator.py).
 */
#ifndef ACTUATOR_H
#define ACTUATOR_H

#include <stdint.h>

#define ACT_MIN_PERMILLE   50      /* per-mille of full scale that output 0 maps to */
#define ACT_MAX_PERMILLE   900     /* per-mille of full scale that output 1000 maps to */

/* out_permille is clamped to 0..1000. full_scale is the largest code the converter takes (1023 for a 10-bit DAC, 1599 for a PWM
 * with a period of 1600 counts). The result is rounded to the nearest code. */
int32_t actuator_scale(int32_t out_permille, int32_t full_scale);

#endif
