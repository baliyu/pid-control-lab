/* pid.c - the fixed-point PID controller. The rules it follows (R1 to R8) are in docs/SPEC.md, and each test names the rule it checks.
 *
 * The idea: every sample the controller looks at how far the measurement is from the target (the error) and decides the output as the sum of three parts:
 *   P  reacts to the error now:            kp * error
 *   I  reacts to the error built up so far: it adds ki * error every sample, so a small steady error is pushed out over time
 *   D  reacts to how fast the measurement is moving: it opposes a quick rise, which calms the loop
 */
#include "pid.h"

/* Keep x between lo and hi. */
static int64_t clamp64(int64_t x, int64_t lo, int64_t hi)
{
    if (x < lo) {
        return lo;
    }
    if (x > hi) {
        return hi;
    }
    return x;
}

void pid_reset(pid_ctrl_t *p)
{
    p->integral = 0;            /* no built-up error */
    p->prev_pv = 0;
    p->primed = 0;              /* the next measurement is the first one: there is nothing to compare it with yet */
}

void pid_init(pid_ctrl_t *p, int32_t kp, int32_t ki, int32_t kd, int32_t out_min, int32_t out_max)
{
    p->kp = kp;
    p->ki = ki;
    p->kd = kd;
    p->out_min = out_min;
    p->out_max = out_max;
    pid_reset(p);
}

int32_t pid_update(pid_ctrl_t *p, int32_t setpoint, int32_t measurement)
{
    /* The output limits, scaled up to Q16.16 so that they can be compared with the terms below, which are Q16.16 too. */
    const int64_t lo = (int64_t)p->out_min * PID_ONE;
    const int64_t hi = (int64_t)p->out_max * PID_ONE;

    /* All of the arithmetic is done in 64 bits: a gain of 255.0 times an error of 65534 is about 1.1e12, far more than a 32-bit number can hold. */
    const int64_t error = (int64_t)setpoint - measurement;

    /* P: kp * error (still Q16.16). */
    const int64_t p_term = (int64_t)p->kp * error;

    /* D: acts on the measurement, not on the error, so that changing the setpoint does not make it jump. A rising measurement gives a negative term.
     * On the very first sample there is no previous measurement, so the term is zero. */
    const int64_t d_term = p->primed ? (int64_t)p->kd * ((int64_t)p->prev_pv - measurement) : 0;
    p->prev_pv = measurement;
    p->primed = 1;

    /* I: add ki * error to the running total. The total is kept inside the output limits (and always allowed to include zero), so that
     * after a long time stuck at a limit it cannot have grown huge: this is the anti-windup. */
    const int64_t i_term = clamp64((int64_t)p->integral + (int64_t)p->ki * error, lo < 0 ? lo : 0, hi > 0 ? hi : 0);
    p->integral = (int32_t)i_term;

    /* Add the three parts, keep the result inside the output limits, then drop the 16 fraction bits to get a plain output value. */
    return (int32_t)(clamp64(p_term + i_term + d_term, lo, hi) >> PID_Q);
}
