/* control.h - one control step: the PID, then the supervisor. Provided; you do not edit this. It is what the firmware will call every sample. */
#ifndef CONTROL_H
#define CONTROL_H

#include <stdint.h>
#include "pid.h"
#include "supervisor.h"

typedef struct {
    pid_ctrl_t pid;
    sup_t      sup;
} control_t;

/* The gains and limits from gains.h. */
void control_init(control_t *c);

/* The same, with other gains (used by the tests and the tuning tools). */
void control_init_with(control_t *c, int32_t kp, int32_t ki, int32_t kd);

/* One step with the raw ADC reading. Returns the actuator output: the PID output, or SUP_SAFE_OUTPUT while the supervisor reports a fault.
 * While there is a fault the PID is reset every step, so it does not wind up on a reading that means nothing. */
int32_t control_step(control_t *c, int32_t setpoint, int32_t adc);

#endif
