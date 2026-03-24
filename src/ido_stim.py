 """
  run_stim.py — Keysight EDU stimulation controller
  ==================================================
  Edit the values below, then run:

      uv run python src/run_stim.py

  Press ESC at any time for an emergency stop.
  """

  from lib.stimulator import run

  DEVICE_RESOURCE = "USB0::10893::36097::CN61310059::0::INSTR"
  USE_PYVISA_PY = True
  MOCK_MODE = False


  """
    ┌─────┬────────────────────┬─────────┬─────────┬──────────┬──────────┬───────────┬────────────────────────────────┐
    │ Run │       Block        │ f1 (Hz) │ f2 (Hz) │ Ch1 (mA) │ Ch2 (mA) │ Beat (Hz) │            Purpose             │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ —   │ A: Baseline        │ —       │ —       │ 0        │ 0        │ —         │ 30s pre-stim (recording only)  │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ 1   │ B: QSA sweep       │ 4000    │ 4001    │ 4        │ 4        │ 1         │ 4 kHz carrier                  │
    │ 2   │ B                  │ 5000    │ 5001    │ 4        │ 4        │ 1         │ 5 kHz carrier                  │
    │ 3   │ B                  │ 6000    │ 6001    │ 4        │ 4        │ 1         │ 6 kHz carrier                  │
    │ 4   │ B                  │ 7000    │ 7001    │ 4        │ 4        │ 1         │ 7 kHz carrier                  │
    │ 5   │ B                  │ 8000    │ 8001    │ 4        │ 4        │ 1         │ 8 kHz carrier                  │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ 6   │ C: Reproducibility │ 4000    │ 4001    │ 4        │ 4        │ 1         │ Sweep repeat: 4 kHz            │
    │ 7   │ C                  │ 5000    │ 5001    │ 4        │ 4        │ 1         │ Sweep repeat: 5 kHz            │
    │ 8   │ C                  │ 6000    │ 6001    │ 4        │ 4        │ 1         │ Sweep repeat: 6 kHz            │
    │ 9   │ C                  │ 7000    │ 7001    │ 4        │ 4        │ 1         │ Sweep repeat: 7 kHz            │
    │ 10  │ C                  │ 8000    │ 8001    │ 4        │ 4        │ 1         │ Sweep repeat: 8 kHz            │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ 11  │ D: Controls        │ 8000    │ 8000    │ 4        │ 4        │ 0         │ Sham: no beat envelope         │
    │ 12  │ D                  │ 8000    │ —       │ 4        │ 0        │ —         │ Ch1 pair only                  │
    │ 13  │ D                  │ 8000    │ —       │ 4        │ 0        │ —         │ Ch1 pair only                  │
    │ 14  │ D                  │ —       │ 8000    │ 0        │ 4        │ —         │ Ch2 pair only                  │
    │ 15  │ D                  │ —       │ 8000    │ 0        │ 4        │ —         │ Ch2 pair only                  │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ 16  │ E: Dose-response   │ 8000    │ 8001    │ 2        │ 2        │ 1         │ 2.0                            │
    │ 17  │ E                  │ 8000    │ 8001    │ 2.5      │ 2.5      │ 1         │ 2.5                            │
    │ 18  │ E                  │ 8000    │ 8001    │ 3        │ 3        │ 1         │ 3.0                            │
    │ 19  │ E                  │ 8000    │ 8001    │ 3.5      │ 3.5      │ 1         │ 3.5                            │
    │ 20  │ E                  │ 8000    │ 8001    │ 4        │ 4        │ 1         │ 4.0                            │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ 21  │ F: Beat variation  │ 8000    │ 8001    │ 4        │ 4        │ 1         │ 1 Hz beat                      │
    │ 22  │ F                  │ 8000    │ 8010    │ 4        │ 4        │ 10        │ 10 Hz beat                     │
    │ 23  │ F                  │ 8000    │ 8050    │ 4        │ 4        │ 50        │ 50 Hz beat                     │
    │ 24  │ F                  │ 8000    │ 8130    │ 4        │ 4        │ 130       │ 130 Hz beat                    │
    ├─────┼────────────────────┼─────────┼─────────┼──────────┼──────────┼───────────┼────────────────────────────────┤
    │ —   │ G: Baseline        │ —       │ —       │ 0        │ 0        │ —         │ 30s post-stim (recording only) │
    └─────┴────────────────────┴─────────┴─────────┴──────────┴──────────┴───────────┴────────────────────────────────┘

    Timing: 10s ramp + 20s stim + 10s ramp + 15s rest = 55s/condition
    24 conditions × 55s ≈ 24 mins
  """


  MODE = "sine"


  SINE_CONDITION_MAP = {
      # ── Block B/C: QSA Frequency Sweep (Δf=1 Hz, 4 mA) ─────────────
      1: [4000, 4001, 4, 4],    # 4 kHz carrier
      2: [5000, 5001, 4, 4],    # 5 kHz carrier
      3: [6000, 6001, 4, 4],    # 6 kHz carrier
      4: [7000, 7001, 4, 4],    # 7 kHz carrier
      5: [8000, 8001, 4, 4],    # 8 kHz carrier
      # ── Block D: Controls (8 kHz reference) ──────────────────────────
      6: [8000, 8000, 4, 4],    # Sham: Δf=0, no beat envelope
      7: [8000, 8000, 4, 0],    # Ch1 only: isolate pair 1 field
      8: [8000, 8000, 0, 4],    # Ch2 only: isolate pair 2 field
      # ── Block E: Dose-Response (8 kHz, Δf=1 Hz) ─────────────────────
      9:  [8000, 8001, 2, 2],    # 2.0 p2p
      10: [8000, 8001, 2.5, 2.5],# 2.5 p2p
      11: [8000, 8001, 3, 3],    # 3.0 p2p
      12: [8000, 8001, 3.5, 3.5],# 3.5 p2p
      # condition 5 serves as 4 p2psat 8 kHz
      # ── Block F: Beat Frequency Variation (8 kHz, 4 mA) ─────────────
      # condition 5 serves as Δf=1 Hz
      13: [8000, 8010, 4, 4],    # Δf = 10 Hz
      14: [8000, 8050, 4, 4],    # Δf = 50 Hz
      15: [8000, 8130, 4, 4],    # Δf = 130 Hz
  }

  CONDITIONS = [
      # Block B: QSA sweep round 1
      1, 2, 3, 4, 5,
      # Block C: QSA sweep round 2 (reproducibility)
      1, 2, 3, 4, 5,
      # Block D: Controls
      6, 7, 8, 7, 8,
      # Block E: Dose-response (2 → 2.5 → 3 → 3.5 → 4 mA ascending)
      9, 10, 11, 12, 5,
      # Block F: Beat frequency variation (1 → 10 → 50 → 130 Hz)
      5, 13, 14, 15,
  ]


  RAMP_DURATION = 10  # seconds for amplitude ramp-up and ramp-down
  STIM_DURATION = 20  # seconds at target amplitude per rep (sine mode only)
  REST_DURATION = 15  # seconds of rest between reps
  REPETITIONS = 1     # ramp-up / hold / ramp-down cycles per condition

  # ── Safety ────────────────────────────────────────────────────────────────

  VOLTAGE_LIMIT = 2.0   # hardware voltage clamp on the device (Volts, ±)
  SAFETY_LIMIT_MA = 8.0  # script aborts if any amplitude exceeds this (mA)

  # ─────────────────────────────────────────────────────────────────────────

  if __name__ == "__main__":
      condition_map = SINE_CONDITION_MAP if MODE == "sine" else PHASE_CONDITION_MAP
      run(
          device_resource=DEVICE_RESOURCE,
          use_pyvisa_py=USE_PYVISA_PY,
          mock_mode=MOCK_MODE,
          mode=MODE,
          conditions=[condition_map[i] for i in CONDITIONS],
          ramp_duration=RAMP_DURATION,
          stim_duration=STIM_DURATION,
          rest_duration=REST_DURATION,
          repetitions=REPETITIONS,
          voltage_limit=VOLTAGE_LIMIT,
          safety_limit_ma=SAFETY_LIMIT_MA,
      )
