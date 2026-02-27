"""
run_stim.py — Keysight EDU stimulation controller
==================================================
Edit the values below, then run:

    uv run python src/run_stim.py

Press ESC at any time for an emergency stop.
"""

from lib.stimulator import run

# ── Device ────────────────────────────────────────────────────────────────

# VISA resource string.  To list connected devices run:
#   uv run python -c "import pyvisa; print(pyvisa.ResourceManager('@py').list_resources())"
DEVICE_RESOURCE = 'USB0::10893::36097::CN61310059::0::INSTR'

# True  → pyvisa-py backend  (macOS / Linux)
# False → NI-VISA backend    (Windows)
USE_PYVISA_PY = True

# Set True to run without hardware (prints commands instead of sending them).
MOCK_MODE = True

# ── Condition library ─────────────────────────────────────────────────────
#
# Define all available conditions here as:
#   integer key → [freq_ch1 Hz, freq_ch2 Hz, amp_ch1 mA, amp_ch2 mA]
#
# Envelope (beat) frequency = |freq_ch2 − freq_ch1|

CONDITION_MAP = {
    1: [8000, 8130, 5, 2],   # 130 Hz envelope
    2: [4000, 4130, 4, 4],   # 130 Hz envelope
    3: [7000, 7130, 4, 4],   # 130 Hz envelope
    4: [1000, 1130, 4, 4],   # 130 Hz envelope
}

# ── Session ───────────────────────────────────────────────────────────────
#
# List the condition keys to run, in order.  Repeats are allowed.

CONDITIONS = [1, 2, 3, 4]

RAMP_DURATION = 2     # seconds for amplitude ramp-up and ramp-down
STIM_DURATION = 5    # seconds at target amplitude per rep
REST_DURATION = 5    # seconds of rest between reps
REPETITIONS   = 2     # ramp-up / hold / ramp-down cycles per condition

# ── Safety ────────────────────────────────────────────────────────────────

VOLTAGE_LIMIT   = 2.0  # hardware voltage clamp on the device (Volts, ±)
SAFETY_LIMIT_MA = 8.0  # script aborts if any amplitude exceeds this (mA)

# ─────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    run(
        device_resource = DEVICE_RESOURCE,
        use_pyvisa_py   = USE_PYVISA_PY,
        mock_mode       = MOCK_MODE,
        conditions      = [CONDITION_MAP[i] for i in CONDITIONS],
        ramp_duration   = RAMP_DURATION,
        stim_duration   = STIM_DURATION,
        rest_duration   = REST_DURATION,
        repetitions     = REPETITIONS,
        voltage_limit   = VOLTAGE_LIMIT,
        safety_limit_ma = SAFETY_LIMIT_MA,
    )
