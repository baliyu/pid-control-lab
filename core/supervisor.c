/* supervisor.c - YOU WRITE THIS (stubs for now). See docs/SPEC.md, rules S1 to S4. */
#include "supervisor.h"

void sup_init(sup_t *s)
{
    (void)s;
    /* TODO(you) */
}

int32_t sup_step(sup_t *s, int32_t adc, int32_t control_out)
{
    (void)s;
    (void)adc;
    /* TODO(you): for now every output is passed through, which is exactly the unsafe behaviour the tests look for */
    return control_out;
}

int sup_fault(const sup_t *s)
{
    (void)s;
    /* TODO(you) */
    return 0;
}
