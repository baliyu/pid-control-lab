/* feather_m0.ino - runs the PID from core/ against a real RC filter on an Adafruit Feather M0 (SAMD21, Cortex-M0+, no floating-point unit).
 *
 * The circuit (see docs/ON_BOARD.md): A0 (the 10-bit DAC) -> 100 k resistor -> node -> A1 (the ADC), with a 100 nF capacitor from the node to ground.
 * The node is the "process value": it follows the DAC with a time constant of 100 k x 100 nF = 10 ms. That is ten times faster than the plant the
 * gains were tuned on (100 ms at 100 Hz), so the loop runs ten times faster too (1 kHz): measured in samples the plant is the same.
 *
 * Commands over USB serial (send them with a newline; the Arduino Serial Monitor at any baud rate works):
 *   I         print the settings
 *   Z         put the output at rest (output 0, which is 5 % of full scale: see core/actuator.h)
 *   S<level>  open-loop step: rest for 0.3 s, then record 0.6 s at 1 kHz while the output steps from 0 to <level> (0..1000) after 0.1 s
 *   R<target> closed-loop run: rest for 0.3 s, then record 0.6 s at 1 kHz while the PID takes the process value from its resting reading to <target> counts
 * Each capture prints a CSV (t,u,pv for S
; t,sp,u,pv for R) and then "# done". Lines starting with # are comments.
 *
 * The sketch only reads and writes pins and keeps time: all the control logic is the tested C in core/ (copied here by sync_core.sh).
 */
#include <stdlib.h>

extern "C" {
#include "control.h"
#include "actuator.h"
#include "gains.h"
}

static const uint32_t TS_US     = 1000;      /* control period: 1 kHz */
static const int32_t  DAC_FULL  = 1023;      /* 10-bit DAC on A0 */
static const int      N_OPEN    = 600;       /* open-loop capture: 0.6 s */
static const int      N_CLOSED  = 600;       /* closed-loop capture: 0.6 s, the same number of rows as the open-loop one, so it fits in the Serial Monitor */
static const int      STEP_AT   = 100;       /* the step happens 0.1 s into a capture */

static control_t ctrl;
static uint16_t  log_sp[N_CLOSED];
static uint16_t  log_u[N_CLOSED];
static uint16_t  log_pv[N_CLOSED];

static char    line[24];
static uint8_t line_len = 0;

static void write_output(int32_t out_permille)
{
    analogWrite(A0, (int)actuator_scale(out_permille, DAC_FULL));
}

static int32_t read_process_value(void)
{
    return (int32_t)analogRead(A1);
}

/* Wait until the next 1 ms tick. Times are compared as differences, so the 32-bit microsecond counter wrapping round is harmless. */
static void wait_next_tick(uint32_t *next)
{
    *next += TS_US;
    while ((int32_t)(micros() - *next) < 0) {
    }
}

static void settle_at_rest(void)
{
    write_output(0);
    delay(300);                              /* 30 time constants: the capacitor has fully settled */
}

static void print_seconds(uint32_t ms)
{
    Serial.print(ms / 1000);
    Serial.print('.');
    const uint32_t rest = ms % 1000;
    if (rest < 100) {
        Serial.print('0');
    }
    if (rest < 10) {
        Serial.print('0');
    }
    Serial.print(rest);
}

static void run_open_loop(int32_t level)
{
    if (level < 0) {
        level = 0;
    }
    if (level > 1000) {
        level = 1000;
    }
    settle_at_rest();
    uint32_t next = micros();
    for (int i = 0; i < N_OPEN; i++) {
        const int32_t u = (i < STEP_AT) ? 0 : level;
        log_pv[i] = (uint16_t)read_process_value();      /* read first, then act: the reading is the state before this sample's output */
        write_output(u);
        log_u[i] = (uint16_t)u;
        wait_next_tick(&next);
    }
    write_output(0);
    Serial.println("t,u,pv");
    for (int i = 0; i < N_OPEN; i++) {
        print_seconds((uint32_t)i);
        Serial.print(',');
        Serial.print((int)log_u[i]);
        Serial.print(',');
        Serial.println((int)log_pv[i]);
    }
    Serial.println("# done");
}

static void run_closed_loop(int32_t target)
{
    if (target < 0) {
        target = 0;
    }
    if (target > 4095) {
        target = 4095;
    }
    settle_at_rest();
    control_init(&ctrl);
    const int32_t rest = read_process_value();           /* the setpoint starts at the resting reading, so the output starts at rest too */
    uint32_t next = micros();
    for (int i = 0; i < N_CLOSED; i++) {
        const int32_t sp = (i < STEP_AT) ? rest : target;
        const int32_t pv = read_process_value();
        const int32_t u = control_step(&ctrl, sp, pv);
        write_output(u);
        log_sp[i] = (uint16_t)sp;
        log_u[i] = (uint16_t)u;
        log_pv[i] = (uint16_t)pv;
        wait_next_tick(&next);
    }
    write_output(0);
    Serial.println("t,sp,u,pv");
    for (int i = 0; i < N_CLOSED; i++) {
        print_seconds((uint32_t)i);
        Serial.print(',');
        Serial.print((int)log_sp[i]);
        Serial.print(',');
        Serial.print((int)log_u[i]);
        Serial.print(',');
        Serial.println((int)log_pv[i]);
    }
    Serial.println("# done");
}

static void print_info(void)
{
    Serial.println("# feather_m0 pid: 1 kHz loop, 10-bit DAC on A0, 12-bit ADC on A1");
    Serial.print("# gains (Q16.16): kp ");
    Serial.print((long)CONTROL_KP_Q16);
    Serial.print(" ki ");
    Serial.print((long)CONTROL_KI_Q16);
    Serial.print(" kd ");
    Serial.println((long)CONTROL_KD_Q16);
    Serial.println("# commands: I info, Z rest, S<level> open-loop step, R<target> closed-loop run");
}

static void handle_command(const char *cmd)
{
    const long arg = atol(cmd + 1);
    switch (cmd[0]) {
    case 'I':
        print_info();
        break;
    case 'Z':
        write_output(0);
        Serial.println("# output at rest");
        break;
    case 'S':
        run_open_loop((int32_t)arg);
        break;
    case 'R':
        run_closed_loop((int32_t)arg);
        break;
    default:
        Serial.println("# unknown command (I, Z, S<level>, R<target>)");
        break;
    }
}

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 4000) {
    }
    analogWriteResolution(10);
    analogReadResolution(12);
    control_init(&ctrl);
    write_output(0);
    print_info();
}

void loop()
{
    while (Serial.available()) {
        const char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (line_len > 0) {
                line[line_len] = 0;
                handle_command(line);
                line_len = 0;
            }
        } else if (line_len < sizeof(line) - 1) {
            line[line_len++] = c;
        }
    }
}
