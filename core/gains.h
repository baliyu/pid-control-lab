/* gains.h - YOU TUNE THESE (docs/TUNING.md). They start at zero, so the closed-loop tests fail until you choose them.
 * Q16.16, per sample: see pid.h. The sample rate is CONTROL_HZ.
 */
#ifndef GAINS_H
#define GAINS_H

#define CONTROL_HZ        100
#define CONTROL_OUT_MIN   0         /* per-mille duty */
#define CONTROL_OUT_MAX   1000

#define CONTROL_KP_Q16    0         /* TODO(you) */
#define CONTROL_KI_Q16    0         /* TODO(you) */
#define CONTROL_KD_Q16    0         /* TODO(you), 0 is a fine answer */

#endif
