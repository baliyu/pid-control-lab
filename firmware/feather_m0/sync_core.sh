#!/bin/sh
# Copies the portable C core next to the sketch, because the Arduino IDE compiles every .c file in the sketch folder and does not look elsewhere.
# The copies are generated (git-ignored): always edit core/, then run this again before uploading.
#
#   cd /mnt/c/stm32-pid-control-lab && sh firmware/feather_m0/sync_core.sh
set -e
cd "$(dirname "$0")"
for f in pid.c pid.h supervisor.c supervisor.h control.c control.h actuator.c actuator.h gains.h; do
  cp "../../core/$f" "./$f"
done
echo "copied core/ into firmware/feather_m0/: open feather_m0.ino in the Arduino IDE (board: Adafruit Feather M0) and upload"
