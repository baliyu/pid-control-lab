/* Runs firmware/feather_m0/feather_m0.ino against the stand-in Arduino library (tests/arduino_stub/Arduino.h).
 * Usage:  sim [--load VOLTS] [--stuck COUNTS] < commands      (commands: one per line, as typed into the Serial Monitor) */
#include "Arduino.h"
#include "../../firmware/feather_m0/feather_m0.ino"

int main(int argc, char **argv)
{
    SimBoard &b = board();
    for (int i = 1; i + 1 < argc; i += 2) {
        if (std::string(argv[i]) == "--load")  b.load_volts = atof(argv[i + 1]);
        if (std::string(argv[i]) == "--stuck") b.stuck_adc = atoi(argv[i + 1]);
    }
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, stdin)) > 0) b.input.append(buf, n);
    setup();
    while (Serial.available()) loop();
    loop();
    return 0;
}
