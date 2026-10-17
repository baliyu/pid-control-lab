/* ctrl_wrapper.c - gives the Python tests a plain-C handle to each module. The tests never look inside your structs,
 * so you are free to design the state however you like. */
#include <stdlib.h>
#include "pid.h"
#include "supervisor.h"
#include "control.h"
#include "gains.h"

void *w_pid_new(int32_t kp, int32_t ki, int32_t kd, int32_t out_min, int32_t out_max)
{
    pid_ctrl_t *p = malloc(sizeof *p);
    pid_init(p, kp, ki, kd, out_min, out_max);
    return p;
}
void w_pid_free(void *p) { free(p); }
void w_pid_reset(void *p) { pid_reset(p); }
int32_t w_pid_update(void *p, int32_t sp, int32_t pv) { return pid_update(p, sp, pv); }

void *w_sup_new(void)
{
    sup_t *s = malloc(sizeof *s);
    sup_init(s);
    return s;
}
void w_sup_free(void *s) { free(s); }
int32_t w_sup_step(void *s, int32_t adc, int32_t out) { return sup_step(s, adc, out); }
int w_sup_fault(void *s) { return sup_fault(s); }

void *w_ctrl_new(int use_defaults, int32_t kp, int32_t ki, int32_t kd)
{
    control_t *c = malloc(sizeof *c);
    if (use_defaults) {
        control_init(c);
    } else {
        control_init_with(c, kp, ki, kd);
    }
    return c;
}
void w_ctrl_free(void *c) { free(c); }
int32_t w_ctrl_step(void *c, int32_t sp, int32_t adc) { return control_step(c, sp, adc); }
int w_ctrl_fault(void *c) { return sup_fault(&((control_t *)c)->sup); }

int32_t w_default_kp(void) { return CONTROL_KP_Q16; }
int32_t w_default_ki(void) { return CONTROL_KI_Q16; }
int32_t w_default_kd(void) { return CONTROL_KD_Q16; }
int32_t w_out_min(void) { return CONTROL_OUT_MIN; }
int32_t w_out_max(void) { return CONTROL_OUT_MAX; }
