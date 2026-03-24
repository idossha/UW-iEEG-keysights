"""Tests for src/lib/stimulator.py — focus on logging edge cases and user stoppage."""

import csv
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.logger import close_log
from lib import stimulator


# ── Helpers ────────────────────────────────────────────────────────────────

SINE_CONDITIONS = [[8000, 8130, 2, 2]]
PHASE_CONDITIONS = [[5000, 2, 2, 0.001, 10, 10]]


def _read_csv(log_dir):
    """Return list of dicts from the single CSV in log_dir."""
    files = sorted(os.listdir(log_dir))
    csv_files = [f for f in files if f.endswith('.csv')]
    assert len(csv_files) >= 1, f"Expected CSV in {log_dir}, found {files}"
    path = os.path.join(log_dir, csv_files[-1])
    with open(path) as f:
        return list(csv.DictReader(f))


def _run_mock(tmp_path, mode='sine', conditions=None, user_inputs=('y', 'y'),
              **kwargs):
    """Run stimulator.run() in mock mode with patched input and log dir."""
    if conditions is None:
        conditions = SINE_CONDITIONS if mode == 'sine' else PHASE_CONDITIONS

    log_dir = str(tmp_path)

    with patch('lib.logger.os.makedirs'), \
         patch('lib.logger.open', create=True) as mock_open, \
         patch('builtins.input', side_effect=list(user_inputs)), \
         patch('lib.stimulator._start_keyboard_listener'), \
         patch('lib.stimulator.open_log') as mock_open_log, \
         patch('lib.stimulator.close_log') as mock_close_log:

        # Set up a real CSV file in tmp_path
        import datetime
        fname = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
        path = os.path.join(log_dir, fname)
        real_file = open(path, 'w', newline='')
        real_writer = csv.writer(real_file)
        real_writer.writerow(['timestamp', 'event', 'detail'])
        real_file.flush()
        mock_open_log.return_value = (real_file, real_writer)

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
        finally:
            if not real_file.closed:
                real_file.close()

        return mock_close_log, path


# ── Tests: Successful session ──────────────────────────────────────────────

class TestSuccessfulSession:

    def test_sine_session_has_start_and_end(self, tmp_path):
        _, path = _run_mock(tmp_path, mode='sine')
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_start' in events
        assert 'session_end' in events

    def test_phase_session_has_start_and_end(self, tmp_path):
        _, path = _run_mock(tmp_path, mode='phase')
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_start' in events
        assert 'session_end' in events

    def test_sine_logs_condition_and_ramp(self, tmp_path):
        _, path = _run_mock(tmp_path, mode='sine')
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'condition_start' in events
        assert 'ramp_down_done' in events

    def test_phase_logs_pulses(self, tmp_path):
        _, path = _run_mock(tmp_path, mode='phase')
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'pulse' in events
        assert 'pulse_train_done' in events

    def test_close_log_called_on_success(self, tmp_path):
        mock_close, _ = _run_mock(tmp_path, mode='sine')
        mock_close.assert_called_once()


# ── Tests: User cancellation ──────────────────────────────────────────────

class TestUserCancellation:

    def test_cancel_at_first_prompt(self, tmp_path):
        mock_close, path = _run_mock(tmp_path, user_inputs=('n',))
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_abort' in events
        assert any('user_cancelled' in r['detail'] for r in rows)
        mock_close.assert_called_once()

    def test_cancel_at_launch_prompt(self, tmp_path):
        mock_close, path = _run_mock(tmp_path, user_inputs=('y', 'n'))
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_abort' in events
        assert any('user_cancelled_at_launch' in r['detail'] for r in rows)
        mock_close.assert_called_once()

    def test_cancel_still_writes_session_start(self, tmp_path):
        _, path = _run_mock(tmp_path, user_inputs=('n',))
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_start' in events


# ── Tests: Exception during protocol ──────────────────────────────────────

class TestExceptionHandling:

    def test_exception_logged_and_file_closed(self, tmp_path):
        """If the protocol raises, the error is logged and file is closed."""
        log_dir = str(tmp_path)

        import datetime
        fname = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
        path = os.path.join(log_dir, fname)
        real_file = open(path, 'w', newline='')
        real_writer = csv.writer(real_file)
        real_writer.writerow(['timestamp', 'event', 'detail'])
        real_file.flush()

        with patch('builtins.input', side_effect=['y', 'y']), \
             patch('lib.stimulator._start_keyboard_listener'), \
             patch('lib.stimulator.open_log', return_value=(real_file, real_writer)), \
             patch('lib.stimulator.close_log') as mock_close, \
             patch('lib.stimulator._run_sine_protocol', side_effect=RuntimeError('device exploded')):

            try:
                stimulator.run(
                    device_resource='MOCK',
                    conditions=SINE_CONDITIONS,
                    mode='sine',
                    mock_mode=True,
                    ramp_duration=0.01,
                    stim_duration=0,
                    condition_rest=0,
                )
            except RuntimeError:
                pass
            finally:
                if not real_file.closed:
                    real_file.close()

        mock_close.assert_called_once()

        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_error' in events
        assert any('device exploded' in r['detail'] for r in rows)


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

    def test_emergency_stop_logs_abort_and_closes(self, tmp_path):
        """_emergency_stop() should log session_abort and close the log file."""
        import datetime
        fname = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
        path = os.path.join(str(tmp_path), fname)
        real_file = open(path, 'w', newline='')
        real_writer = csv.writer(real_file)
        real_writer.writerow(['timestamp', 'event', 'detail'])
        real_file.flush()

        # Set module-level globals as run() would
        stimulator._log_file = real_file
        stimulator._writer = real_writer
        stimulator._device = stimulator._MockDevice()

        # Intercept os._exit so the test process survives
        with patch('lib.stimulator.os._exit') as mock_exit, \
             patch('lib.stimulator._restore_terminal'):
            stimulator._emergency_stop()
            mock_exit.assert_called_once_with(1)

        # File should be closed
        assert real_file.closed

        # CSV should contain the abort event
        rows = list(csv.DictReader(open(path)))
        events = [r['event'] for r in rows]
        assert 'session_abort' in events
        assert any('emergency_stop' in r['detail'] for r in rows)

    def test_interruptible_sleep_yields_in_mock(self):
        """In mock mode, _interruptible_sleep should return almost instantly."""
        import time
        t0 = time.time()
        stimulator._interruptible_sleep(999, mock_mode=True)
        elapsed = time.time() - t0
        assert elapsed < 1.0, "Mock sleep should be near-instant"

    def test_interruptible_sleep_real_mode(self):
        """In real mode, _interruptible_sleep should actually sleep."""
        import time
        t0 = time.time()
        stimulator._interruptible_sleep(0.15, mock_mode=False)
        elapsed = time.time() - t0
        assert elapsed >= 0.1, "Real sleep should actually wait"
