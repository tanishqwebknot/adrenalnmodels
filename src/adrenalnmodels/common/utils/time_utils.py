import datetime
import time

import dateutil

import config


def get_time_stamp():
    try:
        obj = int(time.time())
        return obj
    except Exception as err:
        return None


def get_datetime():
    try:
        date_time = datetime.datetime.now().strftime(config.DATETIME_FORMAT)
        return date_time
    except Exception as err:
        return None


def get_timestamp_diff(timestamp):
    try:
        dt1 = datetime.datetime.fromtimestamp(get_time_stamp())
        dt2 = datetime.datetime.fromtimestamp(timestamp)
        dt_diff = dateutil.relativedelta.relativedelta(dt1, dt2)
        diff_in_minute = (dt1 - dt2) // datetime.timedelta(minutes=1)
        print("In Minutes", diff_in_minute)
        print("Difference", dt_diff.days, dt_diff.hours, dt_diff.minutes, dt_diff.seconds)
        return diff_in_minute
    except Exception as err:
        return None


def get_auth_exp(timeout_in_minutes):
    try:
        ts = datetime.datetime.utcnow() + datetime.timedelta(minutes=timeout_in_minutes)
        return ts
    except Exception as err:
        return None