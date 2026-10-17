/* supervisor.h - a safety layer between the controller and the actuator: if the sensor looks broken, drive the actuator to a safe value.
 * THIS IS PART OF WHAT YOU WRITE: see docs/SPEC.md (rules S1 to S4).
 *
 * A thermistor or a divider that is shorted reads near 0, and one that is open reads near full scale; neither is a real measurement,
 * and a controller that trusts it can drive a heater flat out. The supervisor watches the raw ADC counts.
 */
#ifndef SUPERVISOR_H
#define SUPERVISOR_H

#include <stdint.h>

#define SUP_ADC_MIN      50      /* a sample below this is bad */
#define SUP_ADC_MAX      4045    /* a sample above this is bad */
#define SUP_FAULT_AFTER  5       /* a fault is declared on the 5th bad sample in a row */
#define SUP_CLEAR_AFTER  20      /* and cleared on the 20th good sample in a row */
#define SUP_SAFE_OUTPUT  0       /* what the actuator gets while there is a fault */

typedef struct {
    /* TODO(you): add the counters and flags you need (and delete this placeholder) */
    int32_t todo;
} sup_t;

void sup_init(sup_t *s);

/* Call once per sample with the raw ADC reading and the controller's output. Returns the output to send to the actuator. */
int32_t sup_step(sup_t *s, int32_t adc, int32_t control_out);

/* Non-zero while a fault is declared. */
int sup_fault(const sup_t *s);

#endif
