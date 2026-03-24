# Keysight EDU Function Generator — Stimulation Controller

Python controller for Keysight EDU-series dual-channel function generators, used to deliver transcranial electrical stimulation (tES) protocols with precise frequency pairing and amplitude ramping.

---


## Setup

**Requirements:** Python ≥ 3.10, [uv](https://github.com/astral-sh/uv)

**macOS / Linux** — install `libusb` before first use:
```bash
brew install libusb        # macOS
sudo apt install libusb-1.0-0  # Ubuntu / Debian
```

**Install dependencies:**
```bash
uv sync
```

---

## Running

```bash
uv run python src/basic_stim.py   # generic template
uv run python src/ido_stim.py     # experiment-specific protocol
```

Press **ESC** at any time for an immediate emergency stop (outputs turn off, device closes).

---

## Configuration

Everything a user needs to change is in a stim script (e.g. `src/basic_stim.py`, `src/ido_stim.py`). Copy one to create your own protocol.

### 1. Device

```python
DEVICE_RESOURCE = 'USB0::10893::36097::CN61310059::0::INSTR'
USE_PYVISA_PY   = True    # True = macOS/Linux,  False = Windows (NI-VISA)
MOCK_MODE       = False   # True = no hardware, prints all commands instead
```

To find your device's resource string:
```bash
uv run python -c "import pyvisa; print(pyvisa.ResourceManager('@py').list_resources())"
```

### 2. Mode

```python
MODE = "sine"    # "sine" = beat-frequency AM,  "phase" = pulse delivery
```

### 3. Condition library

Define all available stimulation conditions. Each entry maps an integer key to its parameters.

**Sine mode** — `[freq_ch1 Hz, freq_ch2 Hz, amp_ch1 mA, amp_ch2 mA]`:

```python
SINE_CONDITION_MAP = {
    1: [8000, 8130, 5, 2],   # 130 Hz envelope
    2: [4000, 4130, 4, 4],   # 130 Hz envelope
}
```

**Phase mode** — `[carrier_freq Hz, amp_ch1 mA, amp_ch2 mA, pulse_width s, num_pulses, pulse_freq Hz]`:

```python
PHASE_CONDITION_MAP = {
    1: [5000, 4, 4, 0.001, 100, 10],  # 5 kHz, 1 ms pulses, 100 @ 10 Hz
}
```

### 4. Session

Pick which conditions to run and in what order using their integer keys. To repeat a condition, list it multiple times:

```python
CONDITIONS = [1, 2, 3, 4]   # run all four in order
CONDITIONS = [2, 2, 1]      # run condition 2 twice, then condition 1
CONDITIONS = [3]             # run only condition 3
```

### 5. Timing

```python
RAMP_DURATION  = 10   # seconds — linear amplitude ramp up / ramp down
STIM_DURATION  = 20   # seconds — hold at target amplitude (sine mode only)
CONDITION_REST = 15   # seconds — no-stim pause between conditions
```

Each condition follows this timeline:

```
0 ──[ramp up]──► peak ──[hold: STIM_DURATION]──► peak ──[ramp down]──► 0 ──[rest: CONDITION_REST]──► next condition
```

The last condition has no rest period after it.

### 6. Safety

```python
VOLTAGE_LIMIT   = 2.0   # hardware clamp applied to the device outputs (Volts, ±)
SAFETY_LIMIT_MA = 8.0   # script aborts before connecting if any amplitude exceeds this
```

---

## Testing without hardware

Set `MOCK_MODE = True` in your stim script. Every SCPI command that would be sent to the device is printed to the terminal instead, and hardware wait times are skipped, so the full protocol runs in seconds.

---

## Repository structure

```
src/
├── basic_stim.py        ← generic template with example conditions
├── ido_stim.py          ← experiment-specific protocol
└── lib/
    ├── stimulator.py    ← all stimulation logic (device setup, ramp, safety, loop)
    └── logger.py        ← CSV session logging
tests/
├── test_stimulator.py   ← stimulator unit tests
└── test_logger.py       ← logger unit tests
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `pyvisa` | VISA instrument communication |
| `pyvisa-py` | Pure-Python VISA backend (macOS / Linux) |
| `pyusb` | USB transport for pyvisa-py |
| `numpy` | Numerical helpers (ramp calculations, voltage checks) |
| `psutil` / `zeroconf` | Suppress pyvisa-py network discovery warnings |
