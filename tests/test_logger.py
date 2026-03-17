"""Tests for src/lib/logger.py — open, write, flush, close behaviour."""

import csv
import os
import tempfile

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.logger import open_log, log, close_log


class TestOpenLog:
    """open_log() should create a file with a header row, flushed to disk."""

    def test_creates_file_with_header(self, tmp_path):
        f, writer = open_log(log_dir=str(tmp_path))
        # File should exist on disk already (header flushed)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].suffix == '.csv'

        # Read back — should have exactly the header
        content = files[0].read_text()
        assert content.startswith('timestamp,event,detail')
        close_log(f)

    def test_header_flushed_immediately(self, tmp_path):
        """Even before close, the header must be on disk."""
        f, writer = open_log(log_dir=str(tmp_path))
        path = list(tmp_path.iterdir())[0]
        size = path.stat().st_size
        assert size > 0, "Header should be flushed to disk immediately"
        close_log(f)

    def test_creates_log_dir_if_missing(self, tmp_path):
        log_dir = str(tmp_path / 'nested' / 'logs')
        f, writer = open_log(log_dir=log_dir)
        assert os.path.isdir(log_dir)
        close_log(f)


class TestLog:
    """log() should append a row and flush to disk immediately."""

    def test_row_persisted_after_log(self, tmp_path):
        f, writer = open_log(log_dir=str(tmp_path))
        log(writer, f, 'test_event', 'some detail')

        path = list(tmp_path.iterdir())[0]
        rows = list(csv.reader(path.open()))
        assert len(rows) == 2  # header + 1 data row
        assert rows[1][1] == 'test_event'
        assert rows[1][2] == 'some detail'
        close_log(f)

    def test_multiple_rows(self, tmp_path):
        f, writer = open_log(log_dir=str(tmp_path))
        for i in range(5):
            log(writer, f, f'event_{i}', f'detail_{i}')

        path = list(tmp_path.iterdir())[0]
        rows = list(csv.reader(path.open()))
        assert len(rows) == 6  # header + 5
        close_log(f)

    def test_flush_survives_no_close(self, tmp_path):
        """Data should be on disk even if we never call close_log."""
        f, writer = open_log(log_dir=str(tmp_path))
        log(writer, f, 'critical_event', 'must survive')

        path = list(tmp_path.iterdir())[0]
        content = path.read_text()
        assert 'critical_event' in content
        # cleanup
        f.close()

    def test_default_detail_empty(self, tmp_path):
        f, writer = open_log(log_dir=str(tmp_path))
        log(writer, f, 'no_detail')

        path = list(tmp_path.iterdir())[0]
        rows = list(csv.reader(path.open()))
        assert rows[1][2] == ''
        close_log(f)


class TestCloseLog:
    """close_log() should flush and close; repeat calls should be safe."""

    def test_close_flushes(self, tmp_path):
        f, writer = open_log(log_dir=str(tmp_path))
        log(writer, f, 'before_close')
        close_log(f)
        assert f.closed

        path = list(tmp_path.iterdir())[0]
        assert 'before_close' in path.read_text()

    def test_double_close_safe(self, tmp_path):
        f, writer = open_log(log_dir=str(tmp_path))
        close_log(f)
        close_log(f)  # should not raise

    def test_close_none_safe(self):
        close_log(None)  # should not raise
