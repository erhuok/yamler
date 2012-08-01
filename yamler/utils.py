#encoding:utf8
import re
from flask import g, url_for, flash, abort, request, redirect, Markup, session 
from functools import wraps
from yamler import app
import datetime
from sqlalchemy.sql import select, text
from yamler.queue import Queue
from pyapns import configure, provision, notify

def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']

def required_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash(u'需要登录才能访问')
            return redirect(url_for('user.login', next=request.path))
        #if g.user.is_active == 0:
            #flash(u'账户还未激活，请等待......')
            #return redirect(url_for('user.active'))
        return f(*args, **kwargs)
    return decorated_function

def get_remind(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user:
            rows = g.db.execute(text("SELECT id,own_id FROM task_share WHERE unread=:unread AND user_id=:user_id"), user_id=g.user.id, unread=1).fetchall() 
            g.task_share_count = len(rows) 
            g.task_share_user = dict()
            if len(rows):
                for row in rows:
                    if not g.task_share_user.has_key(row['own_id']): g.task_share_user[row['own_id']] = 0
                    g.task_share_user[row['own_id']] += 1
    
            rows = g.db.execute(text("SELECT id FROM task_submit WHERE unread=:unread AND user_id=:user_id"), user_id=g.user.id, unread=1).fetchall() 
            g.task_submit_count = len(rows)
        return f(*args, **kwargs)
    return decorated_function

def required_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user.is_admin:
            abort(401)
            return f(*args, **kwargs)
    return requires_login(decorated_function)

def allowed_images(filename):
    return '' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

def convert_time(type):
    type = int(type)
    if type == 0:
        start_time = ''
    elif type == 1:
        start_time = datetime.date.today()
    elif type == 2:
        start_time = datetime.datetime.now() - datetime.timedelta(days=1)
    elif type == 3:
        start_time = datetime.datetime.now() - datetime.timedelta(weeks=1)
    elif type == 4:
        start_time = datetime.datetime.now() - datetime.timedelta(days=30)
    if start_time:
        return start_time.strftime("%Y-%m-%d") 

def datetimeformat(value, format='%m月%d日 %H:%M'):
    if isinstance(value, datetime.date):
        '''
        if value.strftime('%Y-%m-%d') == datetime.datetime.today().strftime('%Y-%m-%d'):
            new_value += '今天 '
            #new_value += value.strftime("%H:%M ")
        else:
            new_value += value.strftime("%m月%d日 ") 

        hour = int(value.strftime('%H')) 
        if hour <= 12:
            new_value += '上午'+str(hour)+'点 '
        elif hour > 12 and hour <=18:
            new_value += '下午'+str(hour-12)+'点 '
        elif hour > 18 and hour <=24: 
            new_value += '晚上'+str(hour-12)+'点 ' 
        '''
        new_value = value.strftime("%m-%d %H:%M ")

        default_week = {
            0: '周日',
            1: '周一', 
            2: '周二', 
            3: '周三', 
            4: '周四', 
            5: '周五', 
            6: '周六', 
        }
        week = int(value.strftime('%w'))
        new_value += default_week[week]
        return new_value
    return value


#IPhone手机端的提醒，入队列
def iphone_notify(user_ids, type, title=None, realname=None):
    user_sql = "SELECT id, realname, iphone_token  FROM `users` WHERE id IN ({0})".format(','.join(map(str,user_ids)))
    rows = g.db.execute(text(user_sql)).fetchall()
    if len(title) > 36:
        title = title[0:36] + '...'
    try:
        if type == 'share':
            message = '<'+realname+'>递交日志给您:"'+title+'"--我的云秘书'
            #message = '我的云任务秘书提醒您：有1条新日志递交给您！'
        elif type == 'submit':
            message = '<'+realname+'>安排任务给您:"'+title+'"--我的云秘书'
            #message = '我的云任务秘书提醒您：有1条新任务安排给您！'
        elif type == 'comment':
            message = '来自<'+realname+'>的回复:"'+title+'"--我的云秘书'
            #message = '我的云任务秘书提醒您：您的日志有1条新回复！'

        queue = Queue('notify')
        for row in rows:
            if row.iphone_token:
                value = {'iphone_token':row.iphone_token, 'message': message}
                queue.lpush(value)
    except:
        pass
