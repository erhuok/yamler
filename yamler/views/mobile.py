# encoding:utf-8
from flask import Blueprint, request, session, jsonify, g
from yamler.database import db_session
from yamler.models.users import User, users
from yamler.models.tasks import Task
from yamler.models.companies import Company, companies 
from yamler.models.user_relations import UserRelation 
from sqlalchemy.sql import between
from sqlalchemy import or_, and_, select, text
from yamler.utils import convert_time
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
                    #note = request.form['note'] if request.form.has_key('note') else '', 
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
        print sql 
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

        new_row['created_at'] = row['created_at'].strftime('%m月%d日 %H:%m') if row['created_at'] else '' 
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
            if request.form.has_key('description'):
                task.description = request.form['description']
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

@mod.route('/rel/create', methods=['POST'])
def rel_create():
    if request.method == "POST" and request.form['user_id'] and request.form['username']:
        user = db_session.query(User).filter_by(username=request.form['username']).first() 
        if user is None:
            return jsonify(error=1, code='empty', message='用户名不存在')
        user_relations = db_session.query(UserRelation).filter_by(from_user_id=request.form['user_id']).filter_by(to_user_id=user.id).first()
        if user_relations is None:
            from_user = db_session.query(User).get(request.form['user_id'])
            rel = UserRelation(from_user_id=request.form['user_id'], to_user_id=user.id, status=0, from_user_name=from_user.username, to_user_name=request.form['username'])
            db_session.add(rel)
            db_session.commit()
            return jsonify(error=0, code='success', from_user_id=rel.from_user_id, to_user_id=rel.to_user_id, status=rel.status)

        return jsonify(error=0, code='success', from_user_id=request.form['user_id'], to_user_id=user_relations.to_user_id, status=user_relations.status)
    return jsonify(error=1, code='failed', message='参数传递不正确')

@mod.route('/rel/update', methods=['POST'])
def rel_update():
    if request.method == 'POST' and request.form['id'] and request.form['user_id']:
        rel = db_session.query(UserRelation).get(request.form['id'])
        if rel and rel.to_user_id == int(request.form['user_id']):
            if request.form.has_key('status'):
                rel.status = request.form['status']
            db_session.commit()
            return jsonify(error=0, code='success', from_user_id=rel.from_user_id, to_user_id=rel.to_user_id, status=rel.status)
    
    return jsonify(error=1, code='failed', message='参数传递不正确')

@mod.route('/rel/get', methods=['POST'])
def rel_get():
    if request.method == 'POST':
        if request.form.has_key('user_id') and request.form.has_key('status'):
            #rows = db_session.query(UserRelation).filter(or_(UserRelation.from_user_id==request.form['user_id'],UserRelation.to_user_id==request.form['user_id'])).filter_by(status=request.form['status']).all()
            rows = db_session.query(UserRelation,User).filter(User.id==UserRelation.to_user_id).filter(and_(UserRelation.from_user_id==request.form['user_id'],UserRelation.status==request.form['status'])).all()
            data = [ dict(user.to_json().items() + user_rel.to_json().items())  for user_rel, user in rows]
            rows2 = db_session.query(UserRelation,User).filter(User.id==UserRelation.from_user_id).filter(and_(UserRelation.to_user_id==request.form['user_id'],UserRelation.status==request.form['status'])).all()
            data_to = [ dict(user.to_json().items() + user_rel.to_json().items())  for user_rel, user in rows2]
            return jsonify(error=0, data=data, data_to=data_to)

        if request.form.has_key('to_user_id') and request.form.has_key('status'):
            rows = db_session.query(UserRelation).filter_by(to_user_id=request.form['to_user_id']).filter_by(status=request.form['status']).all() 
        elif request.form.has_key('from_user_id') and request.form.has_key('status'):
            rows = db_session.query(UserRelation).filter_by(from_user_id=request.form['from_user_id']).filter_by(status=request.form['status']).all() 

        data = [row.to_json() for row in rows]
        return jsonify(error=0, data=data)

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
    #sql = "SELECT id,user_id,to_user_id,title,status,comment_count FROM tasks WHERE is_del='0' AND :to_user_id IN (to_user_id) ORDER BY status ASC, id DESC"
    sql = "SELECT id,user_id,to_user_id,title,status,comment_count FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:to_user_id,to_user_id)  ORDER BY status ASC, id DESC"
    task_rows = g.db.execute(text(sql), to_user_id=request.form['user_id']).fetchall()
    task_data = {}
    user_ids = []
    for row in task_rows:
        if not task_data.has_key(row.user_id): 
            user_ids.append(str(row.user_id)) 
            task_data[row.user_id] = [] 
        task_data[row.user_id].append(dict(row))

    sql = "SELECT id, realname FROM `users` WHERE id IN ({0})".format(','.join(user_ids)) 
    user_rows = g.db.execute(text(sql)).fetchall()
    user_data = {}
    for row in user_rows:
        user_data[row.id] = row.realname

    return jsonify(task_data=task_data, user_data=user_data)


