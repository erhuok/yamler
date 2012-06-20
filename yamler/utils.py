#encoding:utf8
import re
from flask import g, url_for, flash, abort, request, redirect, Markup, session 
from functools import wraps
from yamler import app
import datetime

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
    if type == 1:
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
        new_value = ''
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

        default_week = {
            0: '星期天',
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
