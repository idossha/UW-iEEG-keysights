"""Tests for src/lib/logger.py — SessionLogger class."""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.logger import SessionLogger


class TestSessionLoggerInit:
    def test_creates_log_and_csv_files(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        files = {f.suffix for f in tmp_path.iterdir()}
        assert '.log' in files
        assert '.csv' in files
        logger.close()

    def test_csv_has_header(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        content = csv_file.read_text()
        assert content.startswith('timestamp,protocol,condition,phase')
        logger.close()

    def test_creates_log_dir_if_missing(self, tmp_path):
        log_dir = str(tmp_path / 'nested' / 'logs')
        logger = SessionLogger(log_dir=log_dir)
        assert os.path.isdir(log_dir)
        logger.close()


class TestSessionLoggerLog:
    def test_writes_to_both_files(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('test_event', protocol='1/3', condition='test_cond', detail='some detail')

        # Check .log
        log_file = [f for f in tmp_path.iterdir() if f.suffix == '.log'][0]
        log_content = log_file.read_text()
        assert 'TEST' in log_content.upper() or 'test_event' in log_content

        # Check .csv
        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        rows = list(csv.DictReader(csv_file.open()))
        assert len(rows) == 1
        assert rows[0]['protocol'] == '1/3'
        assert rows[0]['condition'] == 'test_cond'
        logger.close()

    def test_csv_amplitude_columns(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('ramp_up_done', protocol='1/3', condition='test',
                   ch1_mA=4.0, ch2_mA=3.5)

        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        rows = list(csv.DictReader(csv_file.open()))
        assert rows[0]['ch1_mA'] == '4.00'
        assert rows[0]['ch2_mA'] == '3.50'
        logger.close()

    def test_csv_duration_column(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('stim_start', protocol='1/3', condition='test', duration=20.0)

        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        rows = list(csv.DictReader(csv_file.open()))
        assert rows[0]['duration_s'] == '20.0'
        logger.close()

    def test_empty_optional_columns(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('session_start', detail='mode=sine')

        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        rows = list(csv.DictReader(csv_file.open()))
        assert rows[0]['protocol'] == ''
        assert rows[0]['condition'] == ''
        assert rows[0]['ch1_mA'] == ''
        assert rows[0]['ch2_mA'] == ''
        assert rows[0]['duration_s'] == ''
        logger.close()

    def test_multiple_rows(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        for i in range(5):
            logger.log(f'event_{i}', detail=f'detail_{i}')

        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        rows = list(csv.DictReader(csv_file.open()))
        assert len(rows) == 5
        logger.close()

    def test_flush_survives_no_close(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('critical_event', detail='must survive')

        csv_file = [f for f in tmp_path.iterdir() if f.suffix == '.csv'][0]
        assert 'critical_event' in csv_file.read_text()

        log_file = [f for f in tmp_path.iterdir() if f.suffix == '.log'][0]
        assert 'critical_event' in log_file.read_text().lower() or 'CRITICAL' in log_file.read_text()
        # cleanup
        logger.close()


class TestSessionLoggerTimeline:
    def test_records_timeline_when_amplitude_provided(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('ramp_up_done', ch1_mA=4.0, ch2_mA=3.0)
        assert len(logger.timeline) == 1
        assert logger.timeline[0][1] == 4.0
        assert logger.timeline[0][2] == 3.0
        logger.close()

    def test_no_timeline_without_amplitude(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('session_start', detail='mode=sine')
        assert len(logger.timeline) == 0
        logger.close()

    def test_condition_start_gets_label(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.log('condition_start', protocol='1/3', ch1_mA=0.0, ch2_mA=0.0)
        assert logger.timeline[0][3] == '1/3'  # label
        logger.close()


class TestSessionLoggerClose:
    def test_close_is_idempotent(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        logger.close()
        logger.close()  # should not raise

    def test_png_path_set(self, tmp_path):
        logger = SessionLogger(log_dir=str(tmp_path))
        assert logger.png_path.endswith('.png')
        logger.close()
