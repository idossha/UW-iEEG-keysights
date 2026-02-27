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
uv run python src/run_stim.py
```

Press **ESC** at any time for an immediate emergency stop (outputs turn off, device closes).

---

## Configuration (`src/run_stim.py`)

Everything a user needs to change is in `src/run_stim.py`.

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

### 2. Condition library

Define all available stimulation conditions here. Each entry maps an integer key to `[freq_ch1 Hz, freq_ch2 Hz, amp_ch1 mA, amp_ch2 mA]`:

```python
CONDITION_MAP = {
    1: [8000, 8130, 5, 2],   # 130 Hz envelope
    2: [4000, 4130, 4, 4],   # 130 Hz envelope
    3: [7000, 7130, 4, 4],   # 130 Hz envelope
    4: [1000, 1130, 4, 4],   # 130 Hz envelope
}
```

### 3. Session

Pick which conditions to run and in what order using their integer keys. Repeats are allowed:

```python
CONDITIONS = [1, 2, 3, 4]   # run all four in order
CONDITIONS = [2, 2, 1]      # repeat condition 2 twice, then condition 1
CONDITIONS = [3]             # run only condition 3
```

### 4. Timing

```python
RAMP_DURATION = 5    # seconds — linear amplitude ramp up / ramp down
STIM_DURATION = 10   # seconds — hold at target amplitude
REST_DURATION = 10   # seconds — no-stim pause between reps
REPETITIONS   = 3    # number of ramp/hold/ramp cycles per condition
```

Per condition, one repetition follows this timeline:

```
0 ──[ramp up: RAMP_DURATION]──► peak ──[hold: STIM_DURATION]──► peak ──[ramp down: RAMP_DURATION]──► 0 ──[rest: REST_DURATION]──► …
```

### 5. Safety

```python
VOLTAGE_LIMIT   = 2.0   # hardware clamp applied to the device outputs (Volts, ±)
SAFETY_LIMIT_MA = 8.0   # script aborts before connecting if any amplitude exceeds this
```

---

## Testing without hardware

Set `MOCK_MODE = True` in `run_stim.py`. Every SCPI command that would be sent to the device is printed to the terminal instead, and hardware wait times are skipped, so the full protocol runs in seconds.

---

## Repository structure

```
src/
├── run_stim.py          ← user-facing: configuration only
└── lib/
    └── stimulator.py    ← all stimulation logic (device setup, ramp, safety, loop)
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `pyvisa` | VISA instrument communication |
| `pyvisa-py` | Pure-Python VISA backend (macOS / Linux) |
| `pyusb` | USB transport for pyvisa-py |
| `numpy` | Numerical helpers (ramp calculations, voltage checks) |
| `pynput` | Cross-platform keyboard listener (ESC emergency stop) |
| `psutil` / `zeroconf` | Suppress pyvisa-py network discovery warnings |
