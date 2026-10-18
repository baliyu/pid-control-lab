/* Arduino.h - a stand-in for the Arduino library, used only by the tests, so that the real sketch can be compiled and run on the PC.
 *
 * It models the circuit the sketch controls: the DAC on A0 drives a 100 kOhm resistor into a node with a 100 nF capacitor to ground, and the ADC
 * on A1 reads that node. Time is virtual: it advances only when the sketch calls micros(), delay() or analogRead(), so a run is exact and fast.
 * Only the parts of the Arduino API that the sketch uses are here.
 */
#ifndef ARDUINO_STUB_H
#define ARDUINO_STUB_H

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>

#define A0 14
#define A1 15

struct SimBoard {
    double now_us = 0.0;           /* virtual time */
    double v_node = 0.0;           /* volts at the RC node */
    double v_dac = 0.0;            /* volts the DAC drives */
    double r_ohm = 100e3, c_farad = 100e-9, vref = 3.3;
    int adc_bits = 12, dac_bits = 10;
    double noise_counts = 1.0;     /* ADC noise, +-counts (uniform) */
    double load_volts = 0.0;       /* a disturbance: volts the node is pulled down by in steady state */
    int stuck_adc = -1;            /* if >= 0 the ADC reports this value (a broken sensor) */
    uint32_t rng = 12345u;
    std::string input;             /* what the "PC" types */
    size_t in_pos = 0;

    void advance(double dt_us) {
        const double tau_us = r_ohm * c_farad * 1e6;
        v_node += (v_dac - load_volts - v_node) * (1.0 - exp(-dt_us / tau_us));
        if (v_node < 0.0) v_node = 0.0;
        now_us += dt_us;
    }
    double noise() {
        rng = rng * 1664525u + 1013904223u;
        return ((rng >> 8) / 16777216.0 - 0.5) * 2.0 * noise_counts;
    }
};

inline SimBoard &board() { static SimBoard b; return b; }

inline void analogWriteResolution(int bits) { board().dac_bits = bits; }
inline void analogReadResolution(int bits) { board().adc_bits = bits; }
inline void analogWrite(int, int code) {
    const double full = (double)((1 << board().dac_bits) - 1);
    board().v_dac = (double)code / full * board().vref;
}
inline int analogRead(int) {
    board().advance(60.0);                                   /* a conversion takes a little time */
    if (board().stuck_adc >= 0) return board().stuck_adc;
    const double full = (double)((1 << board().adc_bits) - 1);
    double counts = board().v_node / board().vref * full + board().noise();
    if (counts < 0) counts = 0;
    if (counts > full) counts = full;
    return (int)floor(counts + 0.5);
}
inline uint32_t micros() {
    board().advance(5.0);                                    /* every call costs a few microseconds, so a busy-wait loop ends */
    return (uint32_t)board().now_us;
}
inline uint32_t millis() { return (uint32_t)(board().now_us / 1000.0); }
inline void delay(uint32_t ms) { board().advance(ms * 1000.0); }

struct SerialStub {
    explicit operator bool() const { return true; }
    void begin(long) {}
    int available() { return (int)(board().input.size() - board().in_pos); }
    int read() { return board().input[board().in_pos++]; }
    void print(const char *s) { fputs(s, stdout); }
    void print(char c) { fputc(c, stdout); }
    void print(int v) { printf("%d", v); }
    void print(unsigned v) { printf("%u", v); }
    void print(long v) { printf("%ld", v); }
    void print(unsigned long v) { printf("%lu", v); }
    void println(const char *s) { fputs(s, stdout); fputc('\n', stdout); }
    void println(int v) { printf("%d\n", v); }
    void println(long v) { printf("%ld\n", v); }
};
static SerialStub Serial;

#endif
