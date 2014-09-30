#coding: utf-8
from __future__ import with_statement

from gevent import monkey
monkey.patch_all(thread=False)

from vkontakte_viomg.utils import global_connection
from vkontakte_viomg.lock import Lock
from contextlib import closing

import httplib
import gevent
import time


LAST_CALL_TIME_KEY = 'vk_last_call_time_%s'
API_LOCK_KEY = 'vk_lock_%s'


def get_last_call_time(api_id):
    r = global_connection.redis
    try:
        return float(r.get(LAST_CALL_TIME_KEY % api_id) or 0)
    except ValueError:
        return 0


def set_last_call_time(api_id):
    r = global_connection.redis
    r.set(LAST_CALL_TIME_KEY % api_id, time.time(), 3600)


def do(connection, url, data, headers):
    connection.request("POST", url, data, headers)
    response = connection.getresponse()
    return response.status, response.read()


# urllib2 doesn't support timeouts for python 2.5 so
# custom function is used for making http requests

def post(url, data, headers, timeout, api_id, ratelimit, secure=False):
    api_id = api_id or '-'

    interval = 1.0 / ratelimit

    host_port = url.split('/')[2]
    timeout_set = False
    connection = httplib.HTTPSConnection if secure else httplib.HTTPConnection
    try:
        connection = connection(host_port, timeout=timeout)
        timeout_set = True
    except TypeError:
        connection = connection(host_port)

    with closing(connection):
        if not timeout_set:
            connection.connect()
            connection.sock.settimeout(timeout)
            timeout_set = True

        with Lock(API_LOCK_KEY % api_id, expires=180, timeout=300):

            while 1:
                delay = time.time() - get_last_call_time(api_id)
                if interval < delay:
                    break
                else:
                    gevent.sleep(interval - delay)

            print time.time() - get_last_call_time(api_id)

            set_last_call_time(api_id)
            gr = gevent.spawn(do, connection, url, data, headers)

        gr.join()
        return gr.value
