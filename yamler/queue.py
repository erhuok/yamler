#-*- encoding:utf-8 -*-
import redis
import json

class Queue(object):
    def __init__(self, key):
        pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
        self.db = redis.Redis(connection_pool=pool)
        self.key = key

    def lpush(self,value):
        if value:
            self.db.lpush(self.key, json.dumps(value))

    def rpop(self):
        return self.db.lpop(self.key) 

#queue = Queue('notify')
#queue.lpush({'message': 'hello world', 'iphone_token':'11111111111'})
#data = queue.rpop()
#if data:
#    print json.loads(data)
