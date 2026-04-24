---
title: "BrainVision Trigger Compatibility"
subtitle: "Why Keysight Hardware Triggers Work on Neuralynx but Not BrainVision"
date: "2026-04-23"
author: "Keysight Control UW"
geometry: margin=1in
fontsize: 11pt
colorlinks: true
numbersections: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{float}
  - \floatplacement{table}{H}
---

# Overview

This document explains why the Keysight EDU33210 hardware trigger output
(Ext Trig BNC) is detected by Neuralynx systems but **not** by BrainVision
(BrainProducts) EEG systems, and describes solutions.

# Root Cause: Detection Architecture Difference

## Neuralynx --- Edge Detection

Neuralynx Digital Lynx SX uses **hardware edge detection** on TTL transitions.
It detects the rising edge of the trigger pulse with microsecond resolution.
A pulse as short as ~1 us is reliably captured.

## BrainVision --- Synchronous Polling

BrainVision amplifiers (BrainAmp, actiCHamp) **read the trigger port state
synchronously with each EEG sample**. A marker is generated only when a
**state change** is detected between two consecutive samples. If the pulse
arrives and returns to baseline between two sample points, the system never
sees it.

| Feature | Neuralynx | BrainVision |
|---------|-----------|-------------|
| Detection method | Hardware edge detection | Synchronous polling at sampling rate |
| Timestamp resolution | ~1 us | 1 / sampling\_rate (0.2--2 ms) |
| Minimum detectable pulse | ~1 us | >= 1 / sampling\_rate |
| Recommended minimum pulse | ~1 us | >= 2 / sampling\_rate |
| Reset to zero required | No (edge-based) | **Yes** (state-change based) |

# Why Our Trigger Is Invisible to BrainVision

The `*TRG` command (`stimulator.py:334`) produces a hardware trigger pulse on
the Ext Trig BNC with a width of **> 1 us** (Keysight 33500 series spec). This
is a fixed hardware characteristic --- there is no SCPI command to change it.

At typical BrainVision sampling rates:

| Sampling Rate | Sampling Interval | Required Min Pulse | Recommended (2x) | Our Pulse (~1 us) |
|---------------|-------------------|--------------------|-------------------|--------------------|
| 500 Hz | 2.0 ms | 2.0 ms | 4.0 ms | 2000x too short |
| 1000 Hz | 1.0 ms | 1.0 ms | 2.0 ms | 1000x too short |
| 2500 Hz | 0.4 ms | 0.4 ms | 0.8 ms | 400x too short |
| 5000 Hz | 0.2 ms | 0.2 ms | 0.4 ms | 200x too short |

The pulse comes and goes entirely within a single sampling interval.

# Additional BrainVision Requirements

## Reset to Zero

BrainVision detects **state changes**. Sending the same trigger value twice
without returning to 0 in between causes the second trigger to be invisible.
The Keysight BNC output likely returns to baseline naturally, but this should
be verified with an oscilloscope.

## Voltage Levels

| Amplifier | Required Voltage | Keysight Output (open) | Keysight Output (50 ohm) | Compatible? |
|-----------|-----------------|------------------------|--------------------------|-------------|
| actiCHamp | 3.3V LVTTL | 3 Vpp | 1.5 Vpp | Yes (open) / Marginal (50 ohm) |
| BrainAmp | 5V TTL | 3 Vpp | 1.5 Vpp | Marginal / No |

Ensure the BrainVision trigger input presents a **high impedance** load (not
50 ohm terminated) so the Keysight outputs 3 Vpp. If using BrainAmp, a level
shifter (3.3V to 5V) may be needed.

# Solutions

## Option A: Software Trigger via Parallel Port (Recommended)

Send a trigger from Python with explicit duration control. This bypasses the
Keysight's fixed-width hardware pulse entirely.

```python
import time
from psychopy import parallel  # or equivalent library

port = parallel.ParallelPort(address=0x0378)

# In the pulse loop (stimulator.py, after *TRG):
dev.write('*TRG')           # fire stimulation burst
port.setData(trigger_value) # trigger ON (1-255)
time.sleep(0.010)           # hold for 10 ms (safe for all sampling rates)
port.setData(0)             # MUST reset to zero
```

- 10 ms hold time is safe for all BrainVision sampling rates (500--5000 Hz)
- Adds ~10 ms overhead per pulse; negligible vs. 900--1100 ms ITI
- `port.setData(0)` reset is **mandatory** between consecutive triggers

## Option B: BrainProducts TriggerBox with Pulse Stretching

Route the Keysight BNC through a BrainProducts TriggerBox:

1. Connect Keysight Ext Trig BNC to TriggerBox input (bit 7 or bit 15)
2. TriggerBox automatically stretches the pulse to ~5 ms (+/- 1 ms)
3. TriggerBox feeds the amplifier via its D-sub connector

No code changes required. The TriggerBox also provides optical isolation and
debouncing.

## Option C: External Hardware Pulse Stretcher

Place a monostable multivibrator between the Keysight BNC and the BrainVision
trigger input:

- 555 timer or SN74121 one-shot circuit
- Configure output pulse width to 5--10 ms
- Triggered by the rising edge of the Keysight pulse

This is the most robust hardware solution but requires building a small circuit.

# Signal Path Comparison

```
Current (Neuralynx --- works):
  Keysight *TRG -> Ext Trig BNC (~1 us pulse) -> Neuralynx TTL input
                                                  (edge detection -> OK)

Current (BrainVision --- FAILS):
  Keysight *TRG -> Ext Trig BNC (~1 us pulse) -> BrainVision trigger input
                                                  (polling -> MISSED)

Solution A (parallel port):
  Keysight *TRG -> stimulation output
  Python code  -> parallel port (10 ms pulse) -> BrainVision trigger input

Solution B (TriggerBox):
  Keysight *TRG -> Ext Trig BNC -> TriggerBox (stretch to 5 ms) -> amplifier

Solution C (pulse stretcher):
  Keysight *TRG -> Ext Trig BNC -> monostable (stretch to 5-10 ms) -> BrainVision
```

# References

- Keysight 33500B/33600A Series Datasheet (5992-2572)
- Keysight 33500 Series User's Guide (33500-90901)
- Brain Products Trigger Beginner's Guide: <https://pressrelease.brainproducts.com/trigger-beginners-guide/>
- Brain Products Trigger Code Design: <https://pressrelease.brainproducts.com/trigger-code-design/>
- Brain Products TriggerBox Tips: <https://pressrelease.brainproducts.com/triggerbox-tips/>
- Neuralynx TTL Input Documentation: <https://neuralynx.fh-co.com/article/ttl-input/>
- BrainVision Parallel Port Latency Testing: <https://github.com/sappelhoff/brainvision_pp_latency_testing>
