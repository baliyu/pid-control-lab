/* pid.c - YOU WRITE THIS. The three functions below are stubs that compile but do nothing useful, so the tests fail until you implement them.
 * Read docs/SPEC.md first: it lists the rules (R1 to R8) and each test names the rule it checks.
 */
#include "pid.h"

void pid_init(pid_ctrl_t *p, int32_t kp, int32_t ki, int32_t kd, int32_t out_min, int32_t out_max)
{
    p->kp = kp;
    p->ki = ki;
    p->kd = kd;
    p->out_min = out_min;
    p->out_max = out_max;
    /* TODO(you): clear your state here too */
}

void pid_reset(pid_ctrl_t *p)
{
    (void)p;
    /* TODO(you) */
}

int32_t pid_update(pid_ctrl_t *p, int32_t setpoint, int32_t measurement)
{
    (void)p;
    (void)setpoint;
    (void)measurement;
    /* TODO(you) */
    return 0;
}
