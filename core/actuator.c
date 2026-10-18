#include "actuator.h"

int32_t actuator_scale(int32_t out_permille, int32_t full_scale)
{
    if (out_permille < 0) {
        out_permille = 0;
    }
    if (out_permille > 1000) {
        out_permille = 1000;
    }
    /* Fraction of full scale, in millionths: 50 000 at output 0 rising by 850 per output unit to 900 000 at output 1000. */
    const int64_t millionths = (int64_t)ACT_MIN_PERMILLE * 1000 + (int64_t)(ACT_MAX_PERMILLE - ACT_MIN_PERMILLE) * out_permille;
    return (int32_t)(((int64_t)full_scale * millionths + 500000) / 1000000);
}
