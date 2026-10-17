/* gains.h - the gains, tuned with tools/identify.py (lambda = tau): see docs/TUNING.md.
 * Q16.16, per sample: see pid.h. The sample rate is CONTROL_HZ. kd is 0 on purpose: kd = 1.0 fails the noise requirement (REQ-3).
 */
#ifndef GAINS_H
#define GAINS_H

#define CONTROL_HZ        100
#define CONTROL_OUT_MIN   0         /* per-mille duty */
#define CONTROL_OUT_MAX   1000

#define CONTROL_KP_Q16    17309         /* from identify.py */
#define CONTROL_KI_Q16    1735         /* from identify.py */
#define CONTROL_KD_Q16    0         /* derivative off */

#endif
