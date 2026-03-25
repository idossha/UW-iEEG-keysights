"""
logger.py — SessionLogger for Keysight EDU stimulation sessions.

Produces two output files per session:
  .log  — verbose, human-readable text log (the full story)
  .csv  — clean tabular data for parsing/analysis (structured columns)
"""

import csv
import os
import time
import datetime


class SessionLogger:
    """
    Dual-output session logger.

    On construction, creates a timestamped .log and .csv pair inside `log_dir`.
    Every call to `log()` writes to both files with format-appropriate content.
    On `close()`, generates a timeline PNG via lib.visualizer (if data exists).
    """

    # Events that appear at top level (no indent) in the .log file
    _TOP_LEVEL_EVENTS = {
        'session_start', 'session_end', 'session_abort', 'session_error',
        'condition_start', 'condition_done',
    }

    def __init__(self, log_dir='logs'):
        os.makedirs(log_dir, exist_ok=True)

        now = datetime.datetime.now()
        base = now.strftime('%Y-%m-%d_%H-%M-%S')

        self._log_path = os.path.join(log_dir, base + '.log')
        self._csv_path = os.path.join(log_dir, base + '.csv')
        self._png_path = os.path.join(log_dir, base + '.png')

        self._log_file = open(self._log_path, 'w')
        self._csv_file = open(self._csv_path, 'w', newline='')
        self._csv_writer = csv.writer(self._csv_file)

        # CSV header
        self._csv_writer.writerow([
            'timestamp', '#', 'condition',
        ])
        self._csv_file.flush()

        # .log file banner
        date_str = now.strftime('%Y-%m-%d %H:%M:%S')
        self._log_file.write('=' * 80 + '\n')
        self._log_file.write('  STIMULATION SESSION LOG\n')
        self._log_file.write(f'  {date_str}\n')
        self._log_file.write('=' * 80 + '\n')
        self._log_file.flush()

        # Timeline data for PNG generation: list of (elapsed, ch1, ch2, label)
        self._timeline = []

        # Session start time for elapsed calculations
        self._t0 = time.time()

        # Mode (set externally before/after construction)
        self._mode = None

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def timeline(self):
        """Return the collected timeline data points."""
        return self._timeline

    @property
    def png_path(self):
        """Return the path where the timeline PNG should be saved."""
        return self._png_path

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value

    # ── Logging ───────────────────────────────────────────────────────────

    def log(self, event, protocol='', condition='', detail='',
            ch1_mA=None, ch2_mA=None, duration=None):
        """
        Record an event to both the .log and .csv files.

        Parameters
        ----------
        event     : str   — machine-readable event name (e.g. 'ramp_up_start')
        protocol  : str   — protocol position like '1/24', or '' for session events
        condition : str   — human description of the condition
        detail    : str   — extra information
        ch1_mA    : float — channel 1 amplitude in mA (None if not applicable)
        ch2_mA    : float — channel 2 amplitude in mA (None if not applicable)
        duration  : float — duration of the phase in seconds (None if not applicable)
        """
        now = datetime.datetime.now()
        ts = now.strftime('%H:%M:%S')

        # ── Write .log ────────────────────────────────────────────────
        self._write_log_line(ts, event, protocol, condition, detail,
                             ch1_mA, ch2_mA, duration)

        # ── Write .csv ────────────────────────────────────────────────
        self._write_csv_row(ts, event, protocol, condition, detail,
                            ch1_mA, ch2_mA, duration)

        # ── Timeline data ─────────────────────────────────────────────
        if ch1_mA is not None:
            elapsed = time.time() - self._t0
            label = protocol if event == 'condition_start' else ''
            cond_info = condition if event == 'condition_start' else ''
            self._timeline.append((elapsed, ch1_mA, ch2_mA, label, cond_info, event))

        # Flush both files after every write
        self._log_file.flush()
        self._csv_file.flush()

    # ── Close / cleanup ───────────────────────────────────────────────────

    def close(self):
        """Close both output files and attempt to generate the timeline PNG."""
        if self._log_file and not self._log_file.closed:
            self._log_file.flush()
            self._log_file.close()
        if self._csv_file and not self._csv_file.closed:
            self._csv_file.flush()
            self._csv_file.close()

        if self._timeline:
            try:
                from lib.visualizer import generate_timeline
                generate_timeline(self._timeline, self._png_path,
                                  mode=self._mode, t0=self._t0)
            except Exception as e:
                print(f'  [Warn] Could not generate timeline plot: {e}')

    # ── Private helpers ───────────────────────────────────────────────────

    def _format_event_name(self, event):
        """
        Convert a machine event name into a readable .log label.

        Rules:
        - Uppercase everything
        - Replace underscores with spaces
        - Strip trailing ' START' for brevity (but keep ' DONE')
        """
        name = event.upper().replace('_', ' ')
        if name.endswith(' START'):
            name = name[:-6]
        return name

    def _write_log_line(self, ts, event, protocol, condition, detail,
                        ch1_mA, ch2_mA, duration):
        """Append a formatted entry to the .log file."""
        label = self._format_event_name(event)

        # Build the detail string that follows the label on the same line
        parts = []
        if ch1_mA is not None and ch2_mA is not None:
            if 'target' in detail.lower() or event in ('ramp_up_start', 'ramp_down_start'):
                parts.append(f'target={ch1_mA:.1f}/{ch2_mA:.1f}mA')
            else:
                parts.append(f'v1={ch1_mA:.4f} v2={ch2_mA:.4f}')
        if duration is not None:
            # For events that are "holding for" vs "over"
            if event in ('stim_start',):
                parts.append(f'holding for {duration:.1f}s')
            elif event in ('rest_start',):
                parts.append(f'{duration:.1f}s')
            elif 'ramp' in event:
                parts.append(f'over {duration:.1f}s')
            else:
                parts.append(f'{duration:.1f}s')
        if detail:
            # Only append raw detail if we haven't already extracted the info
            if not parts:
                parts.append(detail)

        suffix = (' ' * 6 + ' '.join(parts)) if parts else ''
        # Trim excessive whitespace but keep alignment
        suffix = suffix.rstrip()

        if event in self._TOP_LEVEL_EVENTS:
            # Top-level events: no indent
            self._log_file.write(f'\n[{ts}] {label}{suffix}\n')

            # condition_start gets a second line with parameters
            if event == 'condition_start' and condition:
                self._log_file.write(f'           {condition}\n')

        else:
            # Sub-events: indented with 2 spaces
            # Pad label to a fixed width for alignment
            padded_label = f'{label:<18s}'
            self._log_file.write(f'  [{ts}] {padded_label}{suffix}\n')

    # Events that get their own CSV row (one row per stim)
    _CSV_EVENTS = {'stim_start', 'pulse_train_start'}

    def _write_csv_row(self, ts, event, protocol, condition, detail,
                       ch1_mA, ch2_mA, duration):
        """Append a structured row to the .csv file (main stim events only)."""
        if event not in self._CSV_EVENTS:
            return

        # Extract just the number from "1/24" → "1"
        proto_num = protocol.split('/')[0] if '/' in protocol else protocol

        self._csv_writer.writerow([
            ts, proto_num, condition,
        ])
