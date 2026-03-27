"""
ERP_stim.py — Keysight EDU phase-stimulation controller
=======================================================
Phase-only stimulation configuration for ERP-style pulse trains.

Run with:
    uv run python src/ERP_stim.py

Press ESC at any time for an emergency stop.
"""

from lib.stimulator import run

# ── Device ────────────────────────────────────────────────────────────────

DEVICE_RESOURCE = "USB0::10893::36097::CN61310059::0::INSTR"
USE_PYVISA_PY = True
MOCK_MODE = False

# ── Mode ──────────────────────────────────────────────────────────────────

MODE = "phase"

# ── Condition library: Phase Stim ────────────────────────────────────────
#
# [carrier_freq Hz, amp_ch1 mA, amp_ch2 mA, pulse_width s, num_pulses, pulse_frequency Hz]
#
# pulse_frequency is kept for backward compatibility and as a fallback
# fixed interval when PHASE_ITI_RANGE = (None, None).
#
# Example below:
# - 8 kHz carrier
# - 4 mA on each channel
# - 1 ms burst width
# - 100 total pulses
# - 10 Hz fallback pulse repetition
#1: [5000, 4, 4, 0.001, 100, 10],  # 5 kHz, 1 ms pulses, 100 @ 10 Hz
#2: [8000, 5, 5, 0.002, 50, 5],  # 8 kHz, 2 ms pulses,  50 @  5 Hz

PHASE_CONDITION_MAP = {
    1: [8000, 4, 4, 0.001, 1000, 1],
}

# List the condition keys to run, in order.
CONDITIONS = [1]

RAMP_DURATION = 10   # seconds for amplitude ramp-up and ramp-down
CONDITION_REST = 15  # seconds of rest between conditions
PHASE_ITI_RANGE = (0.9, 1.1)  # seconds, each interstimulus interval is randomly sampled between min and max
# Set to (None, None) to fall back to the fixed interval from pulse_frequency.

# ── Safety ────────────────────────────────────────────────────────────────

VOLTAGE_LIMIT = 2.0   # hardware voltage clamp on the device (Volts, ±)
SAFETY_LIMIT_MA = 8.0  # script aborts if any amplitude exceeds this (mA)


if __name__ == "__main__":
    run(
        device_resource=DEVICE_RESOURCE,
        use_pyvisa_py=USE_PYVISA_PY,
        mock_mode=MOCK_MODE,
        mode=MODE,
        conditions=[PHASE_CONDITION_MAP[i] for i in CONDITIONS],
        ramp_duration=RAMP_DURATION,
        condition_rest=CONDITION_REST,
        phase_iti_range=PHASE_ITI_RANGE,
        voltage_limit=VOLTAGE_LIMIT,
        safety_limit_ma=SAFETY_LIMIT_MA,
    )
