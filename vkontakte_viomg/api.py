# -*- coding: utf-8 -*-
from hashlib import md5
from functools import partial

from vkontakte_viomg import http

import warnings
import urllib
import random
import time
import json
import six


try:
    from urllib import urlencode
except:
    from urllib.parse import urlencode


API_URL = 'http://api.vk.com/api.php'
SECURE_API_URL = 'https://api.vk.com/method/'
DEFAULT_TIMEOUT = 1
DEFAULT_API_VERSION = '5.90'
REQUEST_ENCODING = 'utf8'


# See full list of VK API methods here:
# http://vk.com/developers.php?o=-1&p=%D0%A0%D0%B0%D1%81%D1%88%D0%B8%D1%80%D0%B5%D0%BD%D0%BD%D1%8B%D0%B5_%D0%BC%D0%B5%D1%82%D0%BE%D0%B4%D1%8B_API&s=0
# http://vk.com/developers.php?o=-1&p=%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5_%D0%BC%D0%B5%D1%82%D0%BE%D0%B4%D0%BE%D0%B2_API&s=0
COMPLEX_METHODS = [
    'secure', 'ads', 'messages', 'likes', 'friends',
    'groups', 'photos', 'wall', 'board', 'newsfeed', 'notifications', 'audio',
    'video', 'docs', 'places', 'storage', 'notes', 'pages',
    'activity', 'offers', 'questions', 'subscriptions', 'database',
    'users', 'status', 'polls', 'account', 'auth', 'stats'
]


class VKError(Exception):
    __slots__ = ["error"]

    def __init__(self, error_data):
        self.error = error_data
        Exception.__init__(self, str(self))

    @property
    def code(self):
        return self.error['error_code']

    @property
    def description(self):
        return self.error['error_msg']

    @property
    def params(self):
        return self.error['request_params']

    @property
    def captcha(self):
        data = None
        if self.code == 14:  # Capcha needed error
            data = {
                'sid': self.error['captcha_sid'],
                'img': self.error['captcha_img'],
            }
        return data

    @property
    def redirect_uri(self):
        data = None
        if self.code == 17:  # Validation required
            data = self.error['redirect_uri']
        return data

    def __str__(self):
        return "Error(code = '%s', description = '%s', params = '%s', captcha = '%s', redirect_uri = '%s')" % (self.code, self.description, self.params, self.captcha, self.redirect_uri)


def _encode(s):
    if isinstance(s, (dict, list, tuple)):
        s = json.dumps(s, ensure_ascii=False, encoding=REQUEST_ENCODING)

    if isinstance(s, str):
        s = s.encode(REQUEST_ENCODING)

    return s  # this can be number, etc.


def signature(api_secret, params):
    keys = sorted(params.keys())
    param_str = "".join(["%s=%s" % (str(key), _encode(params[key])) for key in keys])
    return md5(param_str + str(api_secret)).hexdigest()


# We have to support this:
#
#   >>> vk = API(key, secret)
#   >>> vk.get('getServerTime')  # "get" is a method of API class
#   >>> vk.friends.get(uid=123)  # "get" is a part of vkontakte method name
#
# It works this way: API class has 'get' method but _API class doesn't.


class _API(object):

    def __init__(self, api_id=None, api_secret=None, token=None, ratelimit=3, lock_timeout=60, lock_expires=2, **defaults):

        if not (api_id and api_secret or token):
            raise ValueError("Arguments api_id and api_secret or token are required")

        self.api_id = api_id
        self.api_secret = api_secret
        self.token = token

        self.ratelimit = ratelimit

        self.lock_timeout = lock_timeout
        self.lock_expires = lock_expires

        self.defaults = defaults
        self.method_prefix = ''

    def _get(self, method, timeout=DEFAULT_TIMEOUT, **kwargs):
        params = self.defaults.copy()
        params.update(kwargs)

        status, response = self._request(method, timeout=timeout, **params)
        if not (200 <= status <= 299):
            raise VKError({
                'error_code': status,
                'error_msg': "HTTP error",
                'request_params': params,
            })

        # there may be a response after errors
        errors = []
        data = json.loads(response.decode('utf-8'))

        if "error" in data:
            errors.append(data["error"])
        if "response" in data:
            for error in errors:
                warnings.warn("%s" % error)
            return data["response"]

        raise VKError(errors[0])

    def __getattr__(self, name):
        '''
        Support for api.<method>.<methodName> syntax
        '''
        if name in COMPLEX_METHODS:
            api = _API(
                api_id=self.api_id,
                api_secret=self.api_secret,
                token=self.token,
                ratelimit=self.ratelimit,
                lock_timeout=self.lock_timeout,
                lock_expires=self.lock_expires,
                **self.defaults
            )
            api.method_prefix = name + '.'
            return api

        # the magic to convert instance attributes into method names
        return partial(self, method=name)

    def __call__(self, **kwargs):
        method = kwargs.pop('method')
        params = self.defaults.copy()
        params.update(kwargs)
        return self._get(self.method_prefix + method, **params)

    def _signature(self, params):
        return signature(self.api_secret, params)

    def _request(self, method, timeout=DEFAULT_TIMEOUT, **kwargs):

        for key, value in six.iteritems(kwargs):
            kwargs[key] = _encode(value)

        if self.token:
            # http://vkontakte.ru/developers.php?oid=-1&p=Выполнение_запросов_к_API
            params = dict(
                access_token=self.token,
            )
            params.update(kwargs)
            params['timestamp'] = int(time.time())
            url = SECURE_API_URL + method
        else:
            # http://vkontakte.ru/developers.php?oid=-1&p=Взаимодействие_приложения_с_API
            params = dict(
                api_id=str(self.api_id),
                method=method,
                format='JSON',
                random=random.randint(0, 2 ** 30),
            )
            params.update(kwargs)
            params['timestamp'] = int(time.time())
            params['sig'] = self._signature(params)
            url = API_URL

        if 'v' not in params:
            params['v'] = DEFAULT_API_VERSION

        data = urlencode(params).encode('utf-8')

        headers = {"Accept": "application/json",
                   "Content-Type": "application/x-www-form-urlencoded"}

        # urllib2 doesn't support timeouts for python 2.5 so
        # custom function is used for making http requests
        return http.post(
            url,
            data,
            headers,
            timeout,
            self.api_id,
            self.token,
            self.ratelimit,
            self.lock_timeout,
            self.lock_expires,
        )


class API(_API):

    def get(self, method, timeout=DEFAULT_TIMEOUT, **kwargs):
        return self._get(method, timeout, **kwargs)
