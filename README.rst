=========
vkontakte-viomg
=========

Форк. Ограничивает частоту запросов к VK API согласно действующим лимитам. 
Gevent, redis locks.

Usage
=====

::

    >>> import vkontakte
    >>> vk = vkontakte.API('my_api_id', 'my_api_secret', ratelimit=3)  # 3 requests per second
    >>> print vk.getServerTime()
    1282689362

    >>> vk = vkontakte.API(token='my_access_token')
    >>> print vk.getServerTime()
    1282689362

    >>> profiles = vk.getProfiles(uids='1,2', fields='education')
    >>> pavel = profiles[0]
    >>> print pavel['last_name'], pavel['university_name']
    Дуров СПбГУ

    >>> # alternative syntax
    >>> profiles = vk.get('getProfiles', uids='1,2', fields='education')
    >>> pavel = profiles[0]
    >>> print pavel['last_name'], pavel['university_name']
    Дуров СПбГУ

    >>> # custom timeout example (default timeout = 1s)
    >>> vk = vkontakte.API('my_api_id', 'my_api_secret', timeout=5)
    >>> print vk.getServerTime()
    1282689362

    >>> # syntax sugar for 'secure.*' methods
    >>> print vk.secure.getSMSHistory()
    None
