/* supervisor.h - a safety layer between the controller and the actuator: if the sensor looks broken, drive the actuator to a safe value.
 * The rules it follows (S1 to S4) are in docs/SPEC.md.
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
    int32_t bad;                 /* how many bad samples in a row (it stops counting at SUP_FAULT_AFTER) */
    int32_t good;                /* how many good samples in a row while there is a fault: counts towards clearing it */
    int32_t fault;               /* 1 while a fault is declared */
} sup_t;

void sup_init(sup_t *s);

/* Call once per sample with the raw ADC reading and the controller's output. Returns the output to send to the actuator. */
int32_t sup_step(sup_t *s, int32_t adc, int32_t control_out);

/* Non-zero while a fault is declared. */
int sup_fault(const sup_t *s);

#endif
