# encoding:utf-8
from flask import Blueprint, request, session, jsonify, g
from yamler.database import db_session
from yamler.models.users import User, users
from yamler.models.tasks import Task
from yamler.models.companies import Company, companies 
from yamler.models.user_relations import UserRelation 
from sqlalchemy.sql import between
from sqlalchemy import or_, and_, select, text
from yamler.utils import convert_time, datetimeformat
import datetime
import time

mod = Blueprint('mobile',__name__,url_prefix='/mobile')

@mod.route('/login',methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if username and password:
        user = User(username,password)
        result = User.query.filter_by(username=user.username, password=user.password).first()
        if result:
            session['user_id'] = result.id
            if request.form.has_key('iphone_token'): 
                sql = "UPDATE users SET last_login_time=:last_login_time,iphone_token=:iphone_token WHERE id=:id"
                g.db.execute(text(sql), id=result.id, last_login_time=datetime.datetime.now(), iphone_token=request.form['iphone_token']) 
            else:
                sql = "UPDATE users SET last_login_time=:last_login_time WHERE id=:id"
                g.db.execute(text(sql), id=result.id, last_login_time=datetime.datetime.now()) 
            return jsonify(error=0, code='success', message='登录成功', user_id = result.id, company_id=result.company_id)
        else:
            return jsonify(error=1, code='username_or_password_error',message='用户名或密码错误',)
    else:
        return jsonify(error=1, code='no_username_or_password', message='没有输入用户名或密码')

@mod.route('/register',methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    if username and password:
        user = User(username, 
                    password, 
                    realname = request.form['realname'] if request.form.has_key('realname') else '',
                    company_id = request.form['company_id'] if request.form.has_key('company_id') else 0,
                    iphone_token = request.form['iphone_token'] if request.form.has_key('iphone_token') else 0,
                   )
        result = User.query.filter_by(username = user.username).first() 

        if result:
            return jsonify(error=1, code='username_exists', message='用户名已经存在')
        else:
            db_session.add(user)
            db_session.commit()
            if request.form.has_key('company_name'):
                row = g.db.execute(select([companies.c.id], and_(companies.c.name==request.form['company_name']))).fetchone()
                company_id = g.db.execute(companies.insert(), name=request.form['company_name'], user_id=user.id).inserted_primary_key[0] if row is None else row['id']
                g.db.execute(users.update().values({users.c.company_id: company_id, users.c.is_active: 1}).where(users.c.id==user.id))
            return jsonify(error=0, code='success', message='成功注册', user_id = user.id, company_id=user.company_id)

    return jsonify(error=1, code = 'no_username_or_password', message='没有输入用户名或密码')

@mod.route('/task/create',methods=['POST'])
def task_create():
    if request.form['user_id'] and request.form['title']:
        task = Task(title = request.form['title'], 
                    user_id = request.form['user_id'], 
                    to_user_id = request.form['to_user_id'] if request.form.has_key('to_user_id') else 0,
                    submit_user_id = request.form['submit_user_id'] if request.form.has_key('submit_user_id') else 0,
                    priority = request.form['priority'] if request.form.has_key('priority') else 1, 
                    end_time = request.form['end_time'] if request.form.has_key('end_time') else '',
                    #created_at = request.form['created_at'] if request.form.has_key('created_at') else '',
                    created_at = datetime.datetime.now(),
                    ) 
        db_session.add(task)
        db_session.commit()
        return jsonify(error=0, code='success', message='添加成功', id=task.id)
    return jsonify(error=1, code='failed', message='输入数据不合法')


@mod.route('/task/get',methods=['POST'])
def task_get():
    if not request.form.has_key('user_id'):
        return jsonify(errro=1)

    user_id = request.form['user_id']
    t = int(request.form['t']) if request.form.has_key('t') else 0
    default_status = {'complete':1 , 'undone':0 , 'all':2} 
    status = request.args.get('status','all')
    status_value = int(default_status[status]) 

    created_at = request.form['created_at'] if request.form.has_key('created_at') else ''
    start_time = convert_time(created_at) if created_at else '' 
    page = request.form['page'] if request.form.has_key('page') else 1 

    limit = 20
    skip = (page-1) * limit
    next_page = 't='+str(t)+'&status='+str(status)+'&page='+str(page+1)+'&created_at='+str(created_at) 
    #只看我自己的
    if 1 == int(t):
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=user_id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    elif 2 == int(t): 
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id)"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql), submit_user_id=user_id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    else: 
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status ' 
        
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " UNION ALL SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id) "
        if status_value != 2:
            sql += ' AND status = :status ' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=user_id, submit_user_id=user_id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()

    data = []
    for row in rows:
        new_row = {}
        new_row['id'] = row['id']
        new_row['comment_count'] = row['comment_count']
        new_row['user_id'] = row['user_id'] 
        new_row['title'] = row['title'] 
        new_row['status'] = row['status'] 
        new_row['share_users'] = None
        new_row['submit_users'] = None
        #手机端的时间
        new_row['mobile_time'] = time.mktime(row.created_at.timetuple()) if row.created_at else ''
        new_row['created_at'] = datetimeformat(row['created_at']) if row['created_at'] else '' 
        new_row['end_time'] = datetimeformat(row['end_time']) if row['end_time'] else '' 
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

        #我自己的
        if row['user_id'] == user_id:
            new_row['realname'] = '我' 
            new_row['ismine'] = True
        #安排给我的
        else:
            new_row['ismine'] = False 
            new_row['realname'] = g.db.execute(text("SELECT id, realname FROM `users` WHERE id=:id"), id=row['user_id']).first().realname

        data.append(new_row)
    return jsonify(data=data, next_page=next_page)

@mod.route('/task/update', methods=['POST'])
def task_update():
    if request.method == 'POST' and request.form['id']:
        task = db_session.query(Task).get(request.form['id']) 
        if task:
            if request.form.has_key('status') : 
                task.status = request.form['status']
            if request.form.has_key('title'):
                task.title = request.form['title']
            if request.form.has_key('note'):
                task.note = request.form['note']
            if request.form.has_key('priority'):
                task.priority = request.form['priority']
            if request.form.has_key('end_time'):
                task.end_time = request.form['end_time']
            if request.form.has_key('to_user_id'):
                task.to_user_id = request.form['to_user_id']
            if request.form.has_key('submit_user_id'):
                task.submit_user_id = request.form['submit_user_id']
            db_session.commit()
            return jsonify(error=0, code='success', message='修改成功', id=task.id)
    
    return jsonify(error=1, code='failed', message='修改失败')

@mod.route('/task/delete', methods=['POST'])
def task_delete():
    if request.method == 'POST' and request.form['id'] and request.form['user_id']:
        task = db_session.query(Task).get(request.form['id']) 
        if task and task.user_id == int(request.form['user_id']) :
            db_session.delete(task)
            db_session.commit()
            return jsonify(error=0, code='success', message='删除成功', id=task.id)

    return jsonify(error=1, code='failed', message='删除失败')

@mod.route('/company/get', methods=['POST'])
def company_get(): 
    fields = [companies.c.id, companies.c.user_id, companies.c.name, companies.c.scale, companies.c.contact_name, companies.c.telephone, companies.c.address, companies.c.postcode, companies.c.website]
    if request.method == 'POST':
        if request.form.has_key('company_id'):
            row = g.db.execute(select(fields, and_(companies.c.id==request.form['company_id']))).fetchone()
            data = dict(zip(row.keys(), row))
            return jsonify(error=0, data=data)

    rows = g.db.execute(select(fields)).fetchall()
    data = [dict(zip(row.keys(), row)) for row in rows]  
    return jsonify(error=0, data=data)


@mod.route('/user/get', methods=['POST'])
def user_get():
    if request.method == 'POST':
        if request.form.has_key('company_id'):
            rows = g.db.execute(select([users.c.id, users.c.company_id, users.c.username, users.c.realname, users.c.telephone, users.c.is_active], and_(users.c.company_id==request.form['company_id']))).fetchall()
            data = [dict(zip(row.keys(), row)) for row in rows]  
            return jsonify(error=0, data=data)
    return jsonify(error=1)


@mod.route('/comment/get', methods=['POST'])
def commit_get():
    if request.method == 'POST' and request.form.has_key('task_id'):
        rows = g.db.execute(text("SELECT id, user_id, task_id, content FROM task_comments WHERE task_id=:task_id"), task_id=request.form['task_id']).fetchall() 
        data = [dict(zip(row.keys(), row)) for row in rows]
        return jsonify(error=0, data=data)

@mod.route('/comment/create', methods=['POST'])
def comment_create():
    if request.method == 'POST' and request.form.has_key('task_id') and request.form.has_key('content') and request.form.has_key('user_id'):
        res = g.db.execute(text("INSERT INTO task_comments (user_id, task_id, content, created_at) VALUES (:user_id, :task_id, :content, :created_at)"),user_id=request.form['user_id'], task_id=request.form['task_id'], content=request.form['content'], created_at=datetime.datetime.now())
        return jsonify(error=0, id=res.lastrowid) 

@mod.route('/task/share', methods=['GET', 'POST'])
def share():
    '''
    sql = "SELECT id,user_id,to_user_id,title,status,comment_count,created_at,submit_user_id FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:to_user_id,to_user_id)  UNION ALL SELECT id,user_id,to_user_id,title,status,comment_count,created_at,submit_user_id FROM tasks WHERE is_del='0' AND user_id=:user_id AND submit_user_id <> '0' ORDER BY status ASC, id DESC"
    task_rows = g.db.execute(text(sql), to_user_id=user_id, user_id=user_id).fetchall()
    task_data = {}
    user_ids = []
    for row in task_rows:
        if row.user_id == user_id:
            if not row.submit_user_id: 
                continue
                submit_user_id = row.submit_user_id.split(',')
                for user_id in submit_user_id:
                    user_id = int(user_id)
                    if not task_data.has_key(user_id):
                        user_ids.append(str(user_id)) 
                        task_data[user_id] = [] 
                    new_row = dict(row)
                    new_row['ismine'] = False
                    new_row['created_at'] = datetimeformat(new_row['created_at']) if new_row['created_at'] else ''
                    task_data[user_id].append(new_row)
        else:
            if not task_data.has_key(row.user_id): 
                user_ids.append(str(row.user_id)) 
                task_data[row.user_id] = [] 
        new_row = dict(row)
        new_row['ismine'] = True
        new_row['created_at'] = datetimeformat(new_row['created_at']) if new_row['created_at'] else ''
        task_data[row.user_id].append(new_row)

    sql = "SELECT id, realname FROM `users` WHERE id IN ({0})".format(','.join(user_ids)) 
    user_rows = g.db.execute(text(sql)).fetchall()
    user_data = {}
    for row in user_rows:
        user_data[row.id] = row.realname
    return jsonify(task_data=task_data, user_data=user_data)
    '''
    user_id = request.form['user_id']
    created_at = request.form['created_at'] if request.form.has_key('created_at') else 2
    status = request.form['status'] if request.form.has_key('status') else 'all'
    task_data_undone, task_data_complete, user_data, user_rows, user_avatar = Task().get_share_data(user_id=user_id, created_at=created_at, status=status)
    return jsonify(user_data=user_data, user_rows=user_rows, task_data_undone=task_data_undone, task_data_complete=task_data_complete, user_avatar=user_avatar)
