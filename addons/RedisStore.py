#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import base64
try:
    import cPickle as pickle
except ImportError:
    import pickle
import logging

import web
from web.session import Store

import redis

SESSION_MARKUP='SESSION_'


class RedisStore(Store):
    """
    Store for saving a session in redis
    """

    def __init__(self, ip="127.0.0.1", port=6379, db=0):

        self.db = redis.StrictRedis(host=ip, port=port, db=db)
        self.timeout = web.webapi.config.session_parameters.timeout

    def __contains__(self, key):
        #"判定是否存在key"
        try:
            return bool(self.db.exists(SESSION_MARKUP+key))
        except redis.ConnectionError:
            sys.stderr.write('Error: Can not Connect Redis')
            sys.exit()

    def __getitem__(self, key):

        v = self.db.get(SESSION_MARKUP+key)
        if v:
            self.db.expire(SESSION_MARKUP+key, 600)
            return self.decode(v)
        else:
            raise KeyError

    def __setitem__(self, key, value):

        self.db.setex(SESSION_MARKUP+key, 600, self.encode(value))

    def __delitem__(self, key):
        self.db.delete(SESSION_MARKUP+key)

    def cleanup(self, timeout):
        pass

    def decode(self, session_data):
        """ 重写decode方法
        避免：Error: Incorrect padding 报错

        Decode base64, padding being optional.

        :param session_data: Base64 data as an ASCII byte string
        :returns: The decoded byte string.
        """
        missing_padding = 4 - len(session_data) % 4
        if missing_padding:
            session_data += b'='* missing_padding

        pickled = base64.decodestring(session_data)
        try:
            return pickle.loads(pickled)
        except pickle.UnpicklingError:
            logging.error('UnpicklingError: '+pickled)
            return pickle.loads(pickled)
