import csv
import os
import datetime


def open_log(log_dir='logs'):
    '''
    Create a new log file named by the current datetime. Returns the open file and writer.
    '''
    os.makedirs(log_dir,exist_ok=True)
    filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
    path = os.path.join(log_dir, filename)
    f = open(path, 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'event', 'detail'])
    return f, writer

def log(writer, event, detail=''):
    '''
    Append one row: current timestamp, event name, detail string.
    '''
    ts = datetime.datetime.now().strftime('%H-%M-%S')
    writer.writerow([ts, event, detail])

