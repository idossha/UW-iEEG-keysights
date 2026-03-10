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

# ── Mode ──────────────────────────────────────────────────────────────────
#
#   "sine"  → amplitude modulation via beat frequency (two sines, delta-f)
#   "phase" → phase-modulation pulse delivery (finite burst pulses)

MODE = "phase"

# ── Condition library: Sine Stim ────────────────────────────────────────
#
# [freq_ch1 Hz, freq_ch2 Hz, amp_ch1 mA, amp_ch2 mA]
# Envelope (beat) frequency = |freq_ch2 − freq_ch1|

SINE_CONDITION_MAP = {
    1: [8000, 8130, 5, 2],   # 130 Hz envelope
    2: [4000, 4130, 4, 4],   # 130 Hz envelope
    3: [7000, 7130, 4, 4],   # 130 Hz envelope
    4: [1000, 1130, 4, 4],   # 130 Hz envelope
}

# ── Condition library: Phase Stim ───────────────────────────────────────
#
# [carrier_freq Hz, amp_ch1 mA, amp_ch2 mA, pulse_width s, num_pulses, pulse_frequency Hz]
#
# carrier_freq    : base frequency of the sine wave
# amp_ch1/ch2     : amplitude per channel (mA)
# pulse_width     : duration of each burst pulse (seconds)
# num_pulses      : total number of pulses per rep
# pulse_frequency : pulse repetition rate (Hz)

PHASE_CONDITION_MAP = {
    1: [5000, 4, 4, 0.001, 100, 10],   # 5 kHz, 1 ms pulses, 100 @ 10 Hz
    2: [8000, 5, 5, 0.002,  50,  5],   # 8 kHz, 2 ms pulses,  50 @  5 Hz
}

# ── Session ───────────────────────────────────────────────────────────────
#
# List the condition keys to run, in order.  Repeats are allowed.

CONDITIONS = [1, 2]

RAMP_DURATION = 10     # seconds for amplitude ramp-up and ramp-down
STIM_DURATION = 30     # seconds at target amplitude per rep (sine mode only)
REST_DURATION = 15     # seconds of rest between reps
REPETITIONS   = 3      # ramp-up / hold / ramp-down cycles per condition

# ── Safety ────────────────────────────────────────────────────────────────

VOLTAGE_LIMIT   = 2.0  # hardware voltage clamp on the device (Volts, ±)
SAFETY_LIMIT_MA = 8.0  # script aborts if any amplitude exceeds this (mA)

# ─────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    condition_map = SINE_CONDITION_MAP if MODE == 'sine' else PHASE_CONDITION_MAP
    run(
        device_resource = DEVICE_RESOURCE,
        use_pyvisa_py   = USE_PYVISA_PY,
        mock_mode       = MOCK_MODE,
        mode            = MODE,
        conditions      = [condition_map[i] for i in CONDITIONS],
        ramp_duration   = RAMP_DURATION,
        stim_duration   = STIM_DURATION,
        rest_duration   = REST_DURATION,
        repetitions     = REPETITIONS,
        voltage_limit   = VOLTAGE_LIMIT,
        safety_limit_ma = SAFETY_LIMIT_MA,
    )
