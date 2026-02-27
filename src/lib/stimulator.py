"""
stimulator.py — core stimulation logic for the Keysight EDU controller.

Not intended to be edited by end users. All user-facing parameters are
configured in run_stim.py.
"""

import os
import sys
import time
import datetime

import numpy as np
import pyvisa as visa
from pynput import keyboard as pynput_keyboard


from lib.logger import open_log, log

# ── Mock device (for testing without hardware) ─────────────────────────────

class _MockDevice:
    """Simulates a pyvisa resource — echoes commands, returns plausible responses."""
    def write(self, cmd):
        print(f'  [mock] {cmd}')
    def query(self, cmd):
        # Return a plausible voltage string for VOLT? queries, else "0"
        return '+0.00000E+00'
    def close(self):
        print('  [mock] device closed')


# ── Internal state ─────────────────────────────────────────────────────────

_device = None   # set on connect; read by the emergency-stop callback


# ── Emergency stop ─────────────────────────────────────────────────────────

def _emergency_stop():
    print("\n\033[1;31mEMERGENCY STOP — ESC pressed\033[0m")
    if _device is not None:
        try:
            _device.write(':OUTPut1:STATe 0')
            _device.write(':OUTPut2:STATe 0')
            _device.write('SYSTem:BEEPer:IMMediate')
            _device.write('*WAI')
            _device.close()
        except Exception:
            pass
    os._exit(1)


def _start_keyboard_listener():
    def on_press(key):
        if key == pynput_keyboard.Key.esc:
            _emergency_stop()
    pynput_keyboard.Listener(on_press=on_press, daemon=True).start()


# ── Device helpers ─────────────────────────────────────────────────────────

def _setup_device(dev, voltage_limit):
    """Configure both channels: sinusoidal, infinite triggered burst, outputs off."""
    for ch in (1, 2):
        dev.write(f':OUTPut{ch}:LOAD INFinity')
        dev.write(f':SOURce{ch}:FUNCtion SIN')
        dev.write(f':SOURce{ch}:BURSt:NCYCles INFinity')
        dev.write(f':SOURce{ch}:BURSt:STATe 1')
        dev.write(f':SOURce{ch}:BURSt:MODE TRIGgered')
        dev.write(f':SOURce{ch}:BURSt:PHASe 0')
        dev.write(f':OUTPut{ch}:STATe OFF')


def _ramp(dev, current_v, target_v, duration):
    """
    Linearly ramp both channel voltages from current_v → target_v over `duration` s.
    Modifies current_v in-place (100 ms steps) and returns it.
    """
    n_steps = int(duration * 10)
    delta   = [(target_v[i] - current_v[i]) / n_steps for i in range(2)]
    arrow   = '↑' if delta[0] >= 0 else '↓'
    spinner = ['◜', '◝', '◞', '◟']

    for i in range(n_steps):
        sys.stdout.write(f'\r  {arrow} Ramping … {spinner[i % 4]}  ')
        sys.stdout.flush()
        for ch_idx in range(2):
            current_v[ch_idx] = max(0.0, round(current_v[ch_idx] + delta[ch_idx], 4))
            dev.write(f':SOURce{ch_idx + 1}:VOLTage {current_v[ch_idx]:G}')
        time.sleep(0.1)

    return current_v


# ── Public entry point ─────────────────────────────────────────────────────

def run(
    device_resource,
    conditions,
    ramp_duration   = 5,
    stim_duration   = 10,
    rest_duration   = 10,
    repetitions     = 3,
    voltage_limit   = 2.0,
    safety_limit_ma = 8.0,
    use_pyvisa_py   = True,
    mock_mode       = False,
):
    """
    Connect to the device and run the full stimulation protocol.

    Parameters
    ----------
    device_resource  : VISA resource string (e.g. 'USB0::10893::...')
    conditions       : list of [freq_ch1, freq_ch2, amp_ch1_mA, amp_ch2_mA]
    ramp_duration    : seconds for linear amplitude ramp up/down
    stim_duration    : seconds at target amplitude per rep
    rest_duration    : seconds of rest between reps
    repetitions      : ramp/hold/ramp cycles per condition
    voltage_limit    : hardware voltage clamp (Volts, ±)
    safety_limit_ma  : abort if any amplitude exceeds this (mA)
    use_pyvisa_py    : True = pyvisa-py backend (macOS/Linux), False = NI-VISA (Windows)
    mock_mode        : True = run without hardware (for testing)
    """
    global _device

    # --- Safety pre-flight (before touching hardware) ---
    all_amps = [a for con in conditions for a in con[2:]]
    if any(a > safety_limit_ma for a in all_amps):
        print(f'\033[1;31m[ABORT] Amplitude exceeds safety limit of {safety_limit_ma} mA.\033[0m')
        sys.exit(1)

    # --- Logger ---
    _log_file, _writer = open_log()

    log(_writer, 'session_start',
        f'condtions={len(conditions)} reps={repetitions} '
        f'ramp={ramp_duration}s stim={stim_duration}s res{rest_duration}s')

    # --- Summary ---
    print(f'\n\033[96m{"─" * 60}')
    print(f'  Keysight EDU Stimulation Controller{"  [MOCK]" if mock_mode else ""}')
    print(f'{"─" * 60}\033[0m')
    print(f'  Conditions  : {len(conditions)}')
    print(f'  Repetitions : {repetitions} per condition')
    print(f'  Ramp        : {ramp_duration} s  |  Stim: {stim_duration} s  |  Rest: {rest_duration} s')
    print(f'  Amplitudes  : {all_amps} mA')

    # --- Connect ---
    if mock_mode:
        _device = _MockDevice()
        print('\n\033[33m  [Mock mode] No hardware will be used.\033[0m')
    else:
        rm = visa.ResourceManager('@py') if use_pyvisa_py else visa.ResourceManager()
        print(f'\n  Available resources: {rm.list_resources()}')
        _device = rm.open_resource(device_resource)
        _device.write('*CLS')
        _device.write('*WAI')
        time.sleep(1)
        print('\033[32m  Device connected.\033[0m')

    # --- Keyboard listener (ESC = emergency stop) ---
    _start_keyboard_listener()
    print('\033[32m  [ESC] emergency stop active.\033[0m\n')

    # --- Configure device ---
    _setup_device(_device, voltage_limit)

    for ch in (1, 2):
        _device.write(f':TRIGger{ch}:SOURce BUS')
    _device.write(':OUTPut1:TRIGger:STATe 1')
    if not mock_mode:
        time.sleep(1)

    for ch in (1, 2):
        _device.write(f':SOURce{ch}:VOLTage:LIMit:HIGH  {voltage_limit:G}')
        _device.write(f':SOURce{ch}:VOLTage:LIMit:LOW  -{voltage_limit:G}')
        _device.write(f':SOURce{ch}:VOLTage:LIMit:STATe 1')
        _device.write(f':SOURce{ch}:VOLTage 0.01')
        _device.write(f':OUTPut{ch}:STATe ON')

    _device.write(f'SOUR1:FREQ {conditions[0][0]}')
    _device.write(f'SOUR2:FREQ {conditions[0][1]}')
    _device.write('*WAI')
    if not mock_mode:
        time.sleep(0.5)

    # --- User confirmation ---
    if input(f'  About to run {len(conditions)} condition(s). Continue? [y/n]: ').strip() != 'y':
        _device.write(':OUTPut1:STATe 0')
        _device.write(':OUTPut2:STATe 0')
        _device.close()
        sys.exit(0)

    if input('  Launch STIMULATION [y/n]: ').strip() != 'y':
        _device.write(':OUTPut1:STATe 0')
        _device.write(':OUTPut2:STATe 0')
        _device.close()
        sys.exit(0)

    # --- Stimulation loop ---
    t_start  = time.time()
    voltages = [0.0, 0.0]

    for cond_idx, con in enumerate(conditions):
        f1, f2, a1, a2 = con
        target  = [float(a1), float(a2)]
        beat_hz = abs(f2 - f1)

        print(f'\n\033[96m  Condition {cond_idx + 1}/{len(conditions)}: '
              f'{f1} Hz + {f2} Hz  →  {beat_hz} Hz envelope  |  {a1}/{a2} mA\033[0m')

        log(_writer, 'condition_start', 
            f'cond={cond_idx+1} f1={f1} f2={f2} a1={a1} a2={a2} beat={beat_hz}Hz')

        _device.write(f'SOUR1:FREQ {f1}')
        _device.write(f'SOUR2:FREQ {f2}')
        _device.write('*WAI')

        for rep in range(repetitions):
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            print(f'  Rep {rep + 1}/{repetitions}  @  {ts}')
            log(_writer, 'rep_start', f'cond={cond_idx+1} rep={rep+1}')

            _device.write('SYSTem:BEEPer:IMMediate')
            _device.write('*TRG')

            voltages = _ramp(_device, voltages, target, ramp_duration)
            print(f'\r  ↑ Ramp up complete — {a1}/{a2} mA              ')

            if not mock_mode:
                time.sleep(stim_duration)

                v1 = float(_device.query('SOUR1:VOLT?'))
                v2 = float(_device.query('SOUR2:VOLT?'))
                if not np.allclose([v1, v2], voltages, atol=0.01):
                    print(f'  \033[33m[Warn] Voltage mismatch — '
                          f'expected {voltages}, got [{v1:.3f}, {v2:.3f}]\033[0m')
                voltages = [v1, v2]

            voltages = _ramp(_device, voltages, [0.0, 0.0], ramp_duration)

            log(_writer, 'ramp_down_done', f'cond={cond_idx+1} rep={rep+1}')
            print(f'\r  ↓ Ramp down complete              ')

            is_last = (cond_idx == len(conditions) - 1) and (rep == repetitions - 1)
            if not is_last and not mock_mode:
                print(f'  ⏸  Rest {rest_duration} s …')
                time.sleep(rest_duration)

    # --- Done ---
    elapsed = time.time() - t_start

    log(_writer, 'session_end', f'total_time={elapsed:.1f}s')
    print(f'\n\033[32m  Stimulation complete.  Total time: {elapsed:.1f} s\033[0m')

    for _ in range(3):
        _device.write('SYSTem:BEEPer:IMMediate')
        if not mock_mode:
            time.sleep(0.15)

    _device.write(':OUTPut1:STATe 0')
    _device.write(':OUTPut2:STATe 0')
    _device.write('*WAI')
    _device.close()
    if not mock_mode:
        rm.close()
