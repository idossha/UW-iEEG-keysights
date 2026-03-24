"""Tests for src/lib/stimulator.py — focus on logging edge cases and user stoppage."""

import csv
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.logger import SessionLogger
from lib import stimulator


# ── Helpers ────────────────────────────────────────────────────────────────

SINE_CONDITIONS = [[8000, 8130, 2, 2]]
PHASE_CONDITIONS = [[5000, 2, 2, 0.001, 10, 10]]


def _run_mock(tmp_path, mode='sine', conditions=None, user_inputs=('y', 'y'),
              **kwargs):
    """Run stimulator.run() in mock mode with patched input and log dir."""
    if conditions is None:
        conditions = SINE_CONDITIONS if mode == 'sine' else PHASE_CONDITIONS

    log_dir = str(tmp_path)
    real_logger = SessionLogger(log_dir=log_dir)

    with patch('builtins.input', side_effect=list(user_inputs)), \
         patch('lib.stimulator._start_keyboard_listener'), \
         patch('lib.stimulator.SessionLogger', return_value=real_logger):

        try:
            stimulator.run(
                device_resource='MOCK',
                conditions=conditions,
                mode=mode,
                mock_mode=True,
                ramp_duration=0.01,
                stim_duration=0,
                condition_rest=0,
                **kwargs,
            )
        except SystemExit:
            pass

    # Find the CSV file
    csv_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.csv')])
    csv_path = os.path.join(log_dir, csv_files[-1]) if csv_files else None

    return real_logger, csv_path


def _read_events(csv_path):
    """Read events from CSV file."""
    if csv_path and os.path.exists(csv_path):
        with open(csv_path) as f:
            return [r['phase'] for r in csv.DictReader(f)]
    return []


# ── Tests: Successful session ──────────────────────────────────────────────

class TestSuccessfulSession:

    def test_sine_session_has_start_and_end(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, mode='sine')
        events = _read_events(csv_path)
        assert 'session_start' in events
        assert 'session_end' in events

    def test_phase_session_has_start_and_end(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, mode='phase')
        events = _read_events(csv_path)
        assert 'session_start' in events
        assert 'session_end' in events

    def test_sine_logs_condition_and_ramp(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, mode='sine')
        events = _read_events(csv_path)
        assert 'condition_start' in events
        assert 'ramp_down_done' in events

    def test_phase_logs_pulses(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, mode='phase')
        events = _read_events(csv_path)
        assert 'pulse' in events
        assert 'pulse_train_done' in events


# ── Tests: User cancellation ──────────────────────────────────────────────

class TestUserCancellation:

    def test_cancel_at_first_prompt(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, user_inputs=('n',))
        events = _read_events(csv_path)
        assert 'session_abort' in events

    def test_cancel_at_launch_prompt(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, user_inputs=('y', 'n'))
        events = _read_events(csv_path)
        assert 'session_abort' in events

    def test_cancel_still_writes_session_start(self, tmp_path):
        _, csv_path = _run_mock(tmp_path, user_inputs=('n',))
        events = _read_events(csv_path)
        assert 'session_start' in events


# ── Tests: Safety validation ──────────────────────────────────────────────

class TestSafetyValidation:

    def test_rejects_amplitude_over_limit(self):
        with patch('lib.stimulator._start_keyboard_listener'):
            try:
                stimulator.run(
                    device_resource='MOCK',
                    conditions=[[8000, 8130, 99, 99]],  # way over 8 mA
                    mode='sine',
                    mock_mode=True,
                )
            except SystemExit as e:
                assert e.code == 1

    def test_rejects_unknown_mode(self):
        with patch('lib.stimulator._start_keyboard_listener'):
            try:
                stimulator.run(
                    device_resource='MOCK',
                    conditions=SINE_CONDITIONS,
                    mode='unknown',
                    mock_mode=True,
                )
            except SystemExit as e:
                assert e.code == 1


# ── Tests: Emergency stop (ESC) in mock mode ─────────────────────────────

class TestEmergencyStopMockMode:

    def test_interruptible_sleep_compressed_in_mock(self):
        """In mock mode, _interruptible_sleep should be ~100x faster."""
        import time
        t0 = time.time()
        stimulator._interruptible_sleep(10, mock_mode=True)
        elapsed = time.time() - t0
        assert elapsed < 1.0, "Mock sleep should be compressed"

    def test_interruptible_sleep_real_mode(self):
        """In real mode, _interruptible_sleep should actually sleep."""
        import time
        t0 = time.time()
        stimulator._interruptible_sleep(0.15, mock_mode=False)
        elapsed = time.time() - t0
        assert elapsed >= 0.1, "Real sleep should actually wait"
