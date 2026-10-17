/* pid.h - a fixed-point PID controller.
 *
 * Numbers are plain integers, with no floating point (the STM32L0 has no floating-point unit).
 *   - Gains are Q16.16 fixed point: real value = raw / 65536, so 1.0 is PID_ONE (65536) and 0.0208 is about 1365.
 *   - Gains are "per sample": ki already includes the sample period and kd is divided by it, so the controller needs no time input.
 *   - setpoint and measurement are in the same units (ADC counts); the output is in output units (for example per-mille duty).
 * pid_update() is called once per sample, at a fixed rate.
 */
#ifndef PID_H
#define PID_H

#include <stdint.h>

#define PID_Q   16
#define PID_ONE (1 << PID_Q)

typedef struct {
    int32_t kp;                 /* Q16.16, per sample */
    int32_t ki;
    int32_t kd;
    int32_t out_min;            /* the output is always kept inside [out_min, out_max] */
    int32_t out_max;

    int32_t integral;           /* the running total of ki * error, in Q16.16 output units, kept inside the output limits */
    int32_t prev_pv;            /* the previous measurement, for the derivative term */
    int32_t primed;             /* 0 until the first measurement has been seen (there is no "previous" one before that) */
} pid_ctrl_t;

/* Set the gains and limits and clear all state. */
void pid_init(pid_ctrl_t *p, int32_t kp, int32_t ki, int32_t kd, int32_t out_min, int32_t out_max);

/* Forget the integral and the history. Keep the gains and limits. */
void pid_reset(pid_ctrl_t *p);

/* One control step. Returns the new output. */
int32_t pid_update(pid_ctrl_t *p, int32_t setpoint, int32_t measurement);

#endif
