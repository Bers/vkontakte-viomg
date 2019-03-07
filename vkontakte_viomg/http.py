# -*- coding: utf-8 -*-
from __future__ import with_statement

import gevent
from gevent import monkey
monkey.patch_all(thread=False)

from vkontakte_viomg.utils import global_connection
from vkontakte_viomg.lock import Lock

import urllib2
import time

try:
    # python3
    from urllib.request import urlopen, Request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, Request


LAST_CALL_TIME_KEY = 'vk_last_call_time_%s'
API_LOCK_KEY = 'vk_lock_%s_%s'


def get_last_call_time(api_id):
    r = global_connection.redis
    try:
        return float(r.get(LAST_CALL_TIME_KEY % api_id) or 0)
    except ValueError:
        return 0


def set_last_call_time(api_id):
    r = global_connection.redis
    r.set(LAST_CALL_TIME_KEY % api_id, time.time(), 3600)


def do(url, data, headers, timeout):
    req = Request(url, data, headers=headers)
    response = urlopen(req, timeout=timeout)
    code = response.getcode()
    content = response.read()
    return code, content


def post(url, data, headers, timeout, api_id, token, ratelimit, lock_timeout=300, lock_expires=2):
    api_id = api_id or '-'

    interval = 1.0 / ratelimit

    with Lock(API_LOCK_KEY % (api_id, token), timeout=lock_timeout, expires=lock_expires):

        while 1:
            delay = time.time() - get_last_call_time(api_id)
            if interval < delay:
                break
            else:
                gevent.sleep(interval - delay)

        # print time.time() - get_last_call_time(api_id)

        set_last_call_time(api_id)
        gr = gevent.spawn(do, url, data, headers, timeout)

    gr.join()
    return gr.value
