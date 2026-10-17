/* supervisor.c - watches the raw sensor reading and forces the actuator to a safe value when the sensor looks broken. See docs/SPEC.md, rules S1 to S4.
 *
 * Two counters decide everything:
 *   - bad:  bad readings in a row. Five in a row declare a fault. One good reading in between starts the count again, so a single glitch does nothing.
 *   - good: good readings in a row, counted only while there is a fault. Twenty in a row clear it. A bad reading in between starts the count again.
 * While there is a fault, the output is the safe value whatever the controller asked for.
 */
#include "supervisor.h"

void sup_init(sup_t *s)
{
    s->bad = 0;
    s->good = 0;
    s->fault = 0;
}

int32_t sup_step(sup_t *s, int32_t adc, int32_t control_out)
{
    if (adc < SUP_ADC_MIN || adc > SUP_ADC_MAX) {
        /* A bad reading. */
        s->good = 0;                             /* any recovery in progress is cancelled */
        if (s->bad < SUP_FAULT_AFTER) {          /* stop at the threshold so the counter can never grow without limit */
            s->bad++;
        }
        if (s->bad >= SUP_FAULT_AFTER) {
            s->fault = 1;
        }
    } else {
        /* A good reading. */
        s->bad = 0;                              /* it breaks the run of bad readings */
        if (s->fault) {
            s->good++;
            if (s->good >= SUP_CLEAR_AFTER) {    /* the 20th good reading in a row: the sensor is trusted again, from this very sample */
                s->fault = 0;
                s->good = 0;
            }
        }
    }
    return s->fault ? SUP_SAFE_OUTPUT : control_out;
}

int sup_fault(const sup_t *s)
{
    return s->fault != 0;
}
