#-*- encoding:utf-8 -*-
import datetime
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

pool = redis.ConnectionPool(host='10.241.12.130', port=6379, db=0)
redis = redis.Redis(connection_pool=pool)

conn = MySQLdb.connect(host='127.0.0.1',user='souduanzu',passwd='hifly@2012',db='yamler_product',charset='utf8',sql_mode="NO_ENGINE_SUBSTITUTION") 
cursor = conn.cursor(MySQLdb.cursors.DictCursor)

def morning():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> '' GROUP BY iphone_token")
    rows = cursor.fetchall() 
    for row in rows:
        value = {'iphone_token': row['iphone_token'], 'message': '云秘书提醒您：一天工作开始了，先写点你将要做什么吧！'}
        res = redis.lpush('notify',json.dumps(value))

def evening():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> '' GROUP BY iphone_token")
    rows = cursor.fetchall() 
    for row in rows:
        value = {'iphone_token': row['iphone_token'], 'message': '云秘书提醒您：快下班了哦，总结下今天的工作吧！'}
        res = redis.lpush('notify',json.dumps(value))

#周一工作计划提醒
def monday():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> '' GROUP BY iphone_token")
    rows = cursor.fetchall() 
    for row in rows:
        value = {'iphone_token': row['iphone_token'], 'message': '云秘书提醒您：新的一周开始了，写下本周的工作计划吧！'}
        res = redis.lpush('notify',json.dumps(value))

def twodays():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> '' GROUP BY iphone_token")
    rows = cursor.fetchall() 
    today = datetime.datetime.now() 
    week = int(today.strftime('%w'))
    if week == 1 or week == 0 or week == 6:
        start_time = today - datetime.timedelta(days=4)
    else:
        start_time = today - datetime.timedelta(days=2)
    for row in rows:
        sql = "SELECT id FROM tasks WHERE user_id='%s' AND created_at > '%s'" % (row['id'], start_time)
        cursor.execute(sql)
        result = cursor.fetchone()
        if result is None:
            value = {'iphone_token': row['iphone_token'], 'message': '云秘书提醒您：您有两天没有写工作日志了！'}
            res = redis.lpush('notify',json.dumps(value))

def task_status():
    cursor.execute("SELECT id, iphone_token FROM users WHERE iphone_token <> '' GROUP BY iphone_token")
    rows = cursor.fetchall() 
    for row in rows:
        sql = "SELECT count(*) AS status_count FROM tasks WHERE user_id='%s' AND status='%s' AND is_del='%s'" % (row['id'], 0, 0)
        cursor.execute(sql)
        result = cursor.fetchone()
        if result and result['status_count'] > 3:
            value = {'iphone_token': row['iphone_token'], 'message': '云秘书提醒您：您还有三个未完成的工作等待您的处理！'}
            res = redis.lpush('notify',json.dumps(value))


if type == 'morning':
    morning()
elif type == 'evening':
    evening()
elif type == 'monday':
    monday()
elif type == 'task_status':
    task_status()
elif type == 'twodays':
    twodays()
