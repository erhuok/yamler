#-*- encoding:utf-8 -*-

import redis
import json
import MySQLdb
import sys 
reload(sys) 
sys.setdefaultencoding('utf8') 

if not sys.argv[1:]:
    print "Usage python pagedata.py [OPTIONS] query words\n"
    print "Options are:"
    print "-t, --type \t 请输入类型，如iphone"
    sys.exit(0)

#参数解析
i = 1
while (i<len(sys.argv)):
    arg = sys.argv[i]
    if arg == '-t' or arg == '--type':
        i +=1
        type = sys.argv[i]
    i += 1

pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
redis = redis.Redis(connection_pool=pool)

conn = MySQLdb.connect(host='127.0.0.1',user='root',passwd='data',db='yamler_development',charset='utf8',sql_mode="NO_ENGINE_SUBSTITUTION") 
cursor = conn.cursor(MySQLdb.cursors.DictCursor)

def morning():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> ''")
    rows = cursor.fetchall() 
    for row in rows:
        value = {'iphone_token': row['iphone_token'], 'message': '一天工作开始了，先写点你将要做什么吧！'}
        res = redis.lpush('notify',json.dumps(value))

def evening():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> ''")
    rows = cursor.fetchall() 
    for row in rows:
        value = {'iphone_token': row['iphone_token'], 'message': '快下班了哦，总结下今天的工作吧！'}
        res = redis.lpush('notify',json.dumps(value))

if type == 'morning':
    morning()
elif type == 'evening':
    evening()
