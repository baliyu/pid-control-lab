#!/usr/bin/env bash
# Static checks on the PID core. Exits with an error if either tool finds anything.
# CI and you both run this same script. Run it from the repo root.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "--- cppcheck ---"
cppcheck --enable=warning,style,performance,portability --inconclusive --std=c99 \
  --suppress=missingIncludeSystem --error-exitcode=1 -q -I core core/*.c
echo "cppcheck: no findings"
echo "--- clang-tidy ---"
clang-tidy core/*.c -- -std=c99 -I core
echo "clang-tidy: no findings"
