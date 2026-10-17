#include "control.h"
#include "gains.h"

void control_init_with(control_t *c, int32_t kp, int32_t ki, int32_t kd)
{
    pid_init(&c->pid, kp, ki, kd, CONTROL_OUT_MIN, CONTROL_OUT_MAX);
    sup_init(&c->sup);
}

void control_init(control_t *c)
{
    control_init_with(c, CONTROL_KP_Q16, CONTROL_KI_Q16, CONTROL_KD_Q16);
}

int32_t control_step(control_t *c, int32_t setpoint, int32_t adc)
{
    int32_t out = pid_update(&c->pid, setpoint, adc);
    out = sup_step(&c->sup, adc, out);
    if (sup_fault(&c->sup)) {
        pid_reset(&c->pid);
    }
    return out;
}
