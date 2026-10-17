#!/usr/bin/env bash
# One-off setup for Ubuntu (WSL2): a C compiler and a Python environment for the tests. Asks for your password because it installs programs.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${PID_VENV:-$HOME/.venvs/stm32-pid-control-lab}"

if ! command -v gcc >/dev/null || ! python3 -c "import venv, ensurepip" 2>/dev/null; then
  sudo apt-get update
  sudo apt-get install -y build-essential python3 python3-venv python3-pip
fi
[ -d "$VENV" ] || python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r "$REPO/requirements.txt"
echo "gcc:    $(gcc --version | head -1)"
echo "Python: $(python --version)  numpy $(python -c 'import numpy; print(numpy.__version__)')  pytest $(python -c 'import pytest; print(pytest.__version__)')"
echo "Environment: $VENV   (activate it with:  source $VENV/bin/activate)"
