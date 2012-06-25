#encoding:utf8

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from flask import Flask,session,g,render_template


app = Flask(__name__)
app.config.from_object('config')
import datetime 
import time
from yamler.database import db_session, engine

from yamler.views import home
from yamler.views import user
from yamler.views import company
from yamler.views import group
from yamler.views import task
from yamler.views import mobile 
from yamler.views import site 
from yamler.views import comment 
from yamler.views import board 

app.register_blueprint(home.mod)
app.register_blueprint(user.mod)
app.register_blueprint(company.mod)
app.register_blueprint(group.mod)
app.register_blueprint(task.mod)
app.register_blueprint(mobile.mod)
app.register_blueprint(site.mod)
app.register_blueprint(comment.mod)
app.register_blueprint(board.mod)

from yamler.models.users import User
from yamler.models.companies import Company 

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.before_request
def load_current_user():
    g.db = engine.connect()
    g.user = User.query.filter_by(id=session['user_id']).first() if 'user_id' in session else None
    g.company = Company.query.filter_by(id=g.user.company_id).first() if g.user else None
    #if g.user:
        #task_share_rows = g.db.execute(text("SELECT id, task_id, own_id, user_id, unread FROM task_share WHERE unread=:unread AND user_id=:user_id"), unread=1, user_id=g.user.id).fetchall()
        #print task_share_rows

@app.teardown_request
def remove_db_session(exception):
    db_session.remove()

@app.after_request
def close_db(response):
    g.db.close()
    return response

@app.template_filter('datetimeformat')
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
