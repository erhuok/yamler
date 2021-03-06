# encoding:utf8
from datetime import datetime, date, timedelta
from flask import Blueprint,request,render_template,session, g, jsonify
from yamler.models.users import User,RegistrationForm,LoginForm
from yamler.database import db_session 
from yamler import app
from yamler.models.companies import companies
from yamler.models.groups import groups 
from yamler.models.tasks import Task, tasks, task_comments, TaskShare, TaskSubmit, TaskUpdateData
from yamler.models.boards import Board, boards
from yamler.models.users import UserNotice, UserContact 
from sqlalchemy.sql import select, text
from yamler.utils import required_login, get_remind, convert_time, datetimeformat 
import time

mod = Blueprint('home', __name__, url_prefix='/home')

@mod.route('/account', methods=['GET', 'POST'])
@required_login
@get_remind
def account():
    if g.task_submit_count:
        g.db.execute(text("UPDATE task_submit SET unread=:unread WHERE user_id=:user_id"), unread=0, user_id=g.user.id)
    return render_template('home/account.html', t=request.args.get('t',0))

@mod.route('/')
@required_login
def index():
    #自动创建第几周工作清单
    week = int(date.today().strftime('%W')) 
    year = int(date.today().strftime('%Y')) 
    sql = text('SELECT id FROM boards WHERE type=:type AND user_id=:user_id AND week=:week AND year=:year AND type=:type')
    res = g.db.execute(sql,user_id=g.user.id, week=week, year=year, type=1).fetchone()
    #不存在本周工作清单，则创建一个
    if res is None:
        title = "第%d周工作清单" % week
        g.db.execute(boards.insert().values(user_id=g.user.id, week=week, year=year, type=1, title=title, created_at=datetime.now())) 

    #获取工作清单列表
    sql = text("SELECT id, title FROM boards WHERE user_id=:user_id AND is_del=:is_del ORDER BY id DESC")
    rows = g.db.execute(sql, user_id=g.user.id, is_del=0).fetchall()
        
    return render_template('home/index.html', rows=rows, realname=g.user.realname, company_name=g.company.name)


@mod.route('/myfeed', methods=['GET', 'POST'])
@required_login
def myfeed():
    group_rows = g.db.execute(select([groups, groups.c.company_id==18])).fetchall()
    return render_template('home/myfeed.html', group_rows=group_rows, pagename='myfeed', args=request.args)

@mod.route('/share', methods=['GET', 'POST'])
@required_login
@get_remind
def share():
    created_at = request.form['created_at'] if request.form.has_key('created_at') else 2
    status = request.form['status'] if request.form.has_key('status') else ''
    task_data_undone, task_data_complete, user_data, user_rows, user_avatar = Task().get_share_data(user_id=g.user.id, created_at=created_at, status=status)
    if g.task_share_count:
        g.db.execute(text("UPDATE task_share SET unread=:unread WHERE user_id=:user_id"), unread=0, user_id=g.user.id)
    return render_template('home/share.html', 
                           user_data=user_data, 
                           task_data_undone=task_data_undone, 
                           task_data_complete=task_data_complete, 
                           user_rows=user_rows,
                           created_at=created_at,
                           status=status,
                          )

@mod.route('/mytask', methods=['GET', 'POST'])
def mytask():
    s = text("SELECT id,user_id,to_user_id,title,created_at,end_time,status FROM tasks WHERE user_id = :user_id") 
    task_rows = g.db.execute(s, user_id=g.user.id).fetchall()
    return render_template('home/mytask.html', task_rows=task_rows, pagename='mytask') 

@mod.route('/publish', methods=['GET', 'POST'])
@required_login
def publish():
    if request.method == 'POST' and request.form['title']:
        created_at = datetime.now()
        to_user_id = request.form['to_user_id'].lstrip(',') if request.form['to_user_id'] else '', 
        submit_user_id = request.form['submit_user_id'].lstrip(',') if request.form['submit_user_id'] else '', 
        res = g.db.execute(tasks.insert().values({
            tasks.c.title: request.form['title'], 
            tasks.c.unread: 1, 
            tasks.c.user_id: g.user.id, 
            tasks.c.created_at: created_at, 
            tasks.c.to_user_id: request.form['to_user_id'].lstrip(',') if request.form['to_user_id'] else '', 
            tasks.c.submit_user_id: request.form['submit_user_id'].lstrip(',') if request.form['submit_user_id'] else '', 
        })) 
        share_users = [ {'realname': row } for row in request.form['share_users'].lstrip(',').split(',') if row] 
        submit_users = [ {'realname': row } for row in request.form['submit_users'].lstrip(',').split(',') if row] 
            
        #id = res.inserted_primary_key[0]
        if request.form['to_user_id']:
            to_user_id = request.form['to_user_id'].lstrip(',').split(',')
            TaskShare().insert(task_id=res.lastrowid, share_user_id=to_user_id, realname=g.user.realname, title=request.form['title'])

        if request.form['submit_user_id']:
            submit_user_id = request.form['submit_user_id'].lstrip(',').split(',')
            TaskSubmit().insert(task_id=res.lastrowid, share_user_id=submit_user_id, realname=g.user.realname, title=request.form['title'])
       

        update_ids = list(set(request.form['to_user_id'].split(',')) | set(request.form['submit_user_id'].split(',')))
        update_ids.append(g.user.id)
        if update_ids:
            row = g.db.execute(text('SELECT * FROM tasks WHERE id=:id'), id=res.lastrowid).first()
            data = dict(row)
            data['mobile_time'] = int(time.mktime(row.created_at.timetuple())) 
            data['created_at'] = datetimeformat(row['created_at'])
            data['updated_at'] = datetimeformat(row['updated_at'])
            TaskUpdateData().insert(user_ids=update_ids, task_id=res.lastrowid, data=data)

        return jsonify(title=request.form['title'], 
                       ismine=True, 
                       realname=g.user.realname, 
                       id=res.inserted_primary_key, 
                       share_users=share_users, 
                       submit_users=submit_users,
                       created_at = datetimeformat(created_at),
                       comment_count = 0,
                      )

@mod.route('/getMyFeed', methods=['GET', 'POST'])
@required_login
def getMyFeed():
    t = int(request.args.get('t',0))
    default_status = {'complete':1 , 'undone':0 , 'all':2} 
    status = request.args.get('status','all')
    status_value = int(default_status[status]) 

    created_at = request.args.get('created_at', 0)
    start_time = convert_time(created_at) if created_at else '' 
    page = int(request.args.get('page',1))
    limit = 20
    skip = (page-1) * limit
    next_page = '/home/getMyFeed?t='+str(t)+'&status='+str(status)+'&page='+str(page+1)+'&created_at='+str(created_at) 
    #只看我自己的
    if 1 == int(t):
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id,unread,priority FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=g.user.id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    elif 2 == int(t): 
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id, unread,priority FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id)"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql), submit_user_id=g.user.id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    else: 
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id, unread,priority FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status ' 
        
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " UNION ALL SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id, unread, priority FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id) "
        if status_value != 2:
            sql += ' AND status = :status ' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=g.user.id, submit_user_id=g.user.id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()

    data = []
    for row in rows:
        new_row = {}
        new_row['id'] = row['id']
        new_row['comment_count'] = row['comment_count']
        new_row['user_id'] = row['user_id'] 
        new_row['title'] = row['title'] 
        new_row['status'] = row['status'] 
        new_row['priority'] = row['priority'] 
        new_row['share_users'] = []
        new_row['submit_users'] = [] 
        if row.user_id != g.user.id:
            new_row['unread'] = row['unread']
        new_row['created_at'] = datetimeformat(row['created_at']) if row['created_at'] else '' 
        '''
        if row['to_user_id']:
            user_ids = row['to_user_id'].lstrip(',').split(',')
            #user_sql = "SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
            user_sql = "SELECT id, realname  FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
            result = g.db.execute(text(user_sql)).fetchall()
            new_row['share_users'] = [dict(zip(res.keys(), res)) for res in result]  

        if row['submit_user_id']:
            user_ids = row.submit_user_id.lstrip(',').split(',')
            user_sql = "SELECT id, realname  FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
            result = g.db.execute(text(user_sql)).fetchall()
            new_row['submit_users'] = [dict(zip(res.keys(), res)) for res in result]  
        '''
        #我自己的
        if row['user_id'] == g.user.id:
            new_row['realname'] = '我' 
            new_row['ismine'] = 1 
        #安排给我的
        else:
            new_row['ismine'] =  0 
            new_row['realname'] = g.db.execute(text("SELECT id, realname FROM `users` WHERE id=:id"), id=row['user_id']).first().realname
        data.append(new_row)
    return jsonify(data=data, next_page=next_page)


@mod.route('/me')
@required_login
def me():
    data, contact_data = UserContact().get(user_id=g.user.id, type=True)
    return render_template('home/me.html', data=data, contact_data=contact_data)
