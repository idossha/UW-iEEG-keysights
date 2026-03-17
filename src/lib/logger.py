import csv
import os
import datetime


def open_log(log_dir='logs'):
    '''
    Create a new log file named by the current datetime. Returns the open file and writer.
    The header is written and flushed immediately so the file is never truly empty.
    '''
    os.makedirs(log_dir, exist_ok=True)
    filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
    path = os.path.join(log_dir, filename)
    f = open(path, 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'event', 'detail'])
    f.flush()
    return f, writer


def log(writer, log_file, event, detail=''):
    '''
    Append one row: current timestamp, event name, detail string.
    Flushes to disk after every write so data survives abrupt exits.
    '''
    ts = datetime.datetime.now().strftime('%H-%M-%S')
    writer.writerow([ts, event, detail])
    log_file.flush()


def close_log(log_file):
    '''Flush and close the log file.'''
    if log_file and not log_file.closed:
        log_file.flush()
        log_file.close()

