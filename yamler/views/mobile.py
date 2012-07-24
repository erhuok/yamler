# encoding:utf-8
from flask import Blueprint, request, session, jsonify, g
from yamler.database import db_session
from yamler.models.users import User, users, UserNotice
from yamler.models.tasks import Task, tasks, task_comments, TaskShare, TaskSubmit, TaskUpdateData, TaskComment
from yamler.models.companies import Company, companies 
from yamler.models.user_relations import UserRelation 
from sqlalchemy.sql import between
from sqlalchemy import or_, and_, select, text
from yamler.utils import convert_time, datetimeformat, iphone_notify
import datetime
import time
import base64

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
            url = 'http://'+request.host + '/i/' + base64.encodestring(str(result.company_id)) 
            return jsonify(error=0, code='success', message='登录成功', user_id = result.id, company_id=result.company_id, url=url, realname=result.realname)
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
                    telephone = request.form['telephone'] if request.form.has_key('telephone') else '',
                    company_id = request.form['company_id'] if request.form.has_key('company_id') else 0,
                    iphone_token = request.form['iphone_token'] if request.form.has_key('iphone_token') else '',
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
            url = 'http://'+request.host + '/i/' + base64.encodestring(str(g.company.id)) 
            return jsonify(error=0, code='success', message='成功注册', user_id = user.id, company_id=user.company_id, url=url, realname=user.realname)

    return jsonify(error=1, code = 'no_username_or_password', message='没有输入用户名或密码')

@mod.route('/task/create',methods=['POST'])
def task_create():
    if request.form['user_id'] and request.form['title']:
        res = g.db.execute(tasks.insert().values({
            tasks.c.title: request.form['title'], 
            tasks.c.flag: '0',
            tasks.c.unread: 1, 
            tasks.c.user_id: request.form['user_id'], 
            tasks.c.created_at: datetime.datetime.now(), 
            tasks.c.priority: request.form['priority'] if request.form.has_key('priority') else 1, 
            tasks.c.to_user_id: request.form['to_user_id'].lstrip(',') if request.form.has_key('to_user_id') else '', 
            tasks.c.submit_user_id: request.form['submit_user_id'].lstrip(',') if request.form.has_key('submit_user_id')  else '', 
            tasks.c.end_time: request.form['end_time'] if request.form.has_key('end_time') else '',
            tasks.c.notify_time: request.form['notify_time'] if request.form.has_key('notify_time') else '',
        })) 

        user_row = g.db.execute(text("SELECT id, realname FROM users WHERE id=:id"), id=request.form['user_id']).fetchone()

        if request.form.has_key('to_user_id') and request.form['to_user_id']:
            to_user_id = request.form['to_user_id'].lstrip(',').split(',')
            TaskShare().insert(task_id=res.lastrowid, own_id=request.form['user_id'], share_user_id=to_user_id, realname=user_row.realname, title=request.form['title'])

        if request.form.has_key('submit_user_id') and request.form['submit_user_id']:
            submit_user_id = request.form['submit_user_id'].lstrip(',').split(',')
            TaskSubmit().insert(task_id=res.lastrowid, own_id=request.form['user_id'], share_user_id=submit_user_id, realname=user_row.realname, title=request.form['title'])

        to_user_id = request.form['to_user_id'] if request.form.has_key('to_user_id') else '' 
        submit_user_id = request.form['submit_user_id'] if request.form.has_key('submit_user_id') else '' 
        update_ids = list(set(to_user_id.split(',')) | set(submit_user_id.split(',')))
        update_ids.append(request.form['user_id'])
        if update_ids:
            row = g.db.execute(text('SELECT * FROM tasks WHERE id=:id'), id=res.lastrowid).first()
            data = dict(row)
            data['mobile_time'] = int(time.mktime(row.created_at.timetuple())) 
            data['created_at'] = datetimeformat(row['created_at'])
            data['updated_at'] = datetimeformat(row['updated_at'])
            TaskUpdateData().insert(user_ids=update_ids, task_id=res.lastrowid, data=data)
        return jsonify(error=0, code='success', message='添加成功', id=res.lastrowid)

    return jsonify(error=1, code='failed', message='输入数据不合法')

def process_task_data(rows, user_id):
    data = []
    for row in rows:
        new_row = {}
        new_row['id'] = row['id']
        new_row['comment_count'] = row['comment_count']
        new_row['user_id'] = row['user_id'] 
        new_row['title'] = row['title'] 
        new_row['status'] = row['status'] 
        new_row['priority'] = row['priority']
        new_row['share_users'] = None
        new_row['submit_users'] = None
        new_row['to_user_id'] = row['to_user_id']
        new_row['is_del'] = row['is_del']
        new_row['submit_user_id'] = row['submit_user_id']
        #手机端的时间
        new_row['mobile_time'] = int(time.mktime(row.created_at.timetuple())) if row.created_at and isinstance(row.created_at, datetime.datetime) else ''
        new_row['created_at'] = datetimeformat(row['created_at']) if row['created_at'] else '' 
        new_row['end_time'] = datetimeformat(row['end_time']) if row['end_time']  and isinstance(row.created_at, datetime.datetime) else '' 
        new_row['notify_time'] = row['notify_time'].strftime("%Y-%m-%d %T") if row.notify_time and isinstance(row.notify_time, datetime.datetime) else ''
        if row['to_user_id']:
            user_ids = row['to_user_id'].lstrip(',').split(',')
            #user_sql = "SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
            user_sql = "SELECT id, realname  FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
            result = g.db.execute(text(user_sql)).fetchall()
            new_row['share_users'] = [dict(zip(res.keys(), res)) for res in result]  

        if row['submit_user_id']:
            user_ids = row['submit_user_id'].lstrip(',').split(',')
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
            user_res = g.db.execute(text("SELECT id, realname FROM `users` WHERE id=:id"), id=row['user_id']).first()
            if user_res:
                new_row['realname'] = user_res.realname

        data.append(new_row)
    return data

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
    page = int(request.form['page'])  if request.form.has_key('page') else 1 

    limit = 500
    skip = (page-1) * limit
    next_page = 't='+str(t)+'&status='+str(status)+'&page='+str(page+1)+'&created_at='+str(created_at) 
    #只看我自己的
    if 1 == int(t):
        sql = "SELECT * FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=user_id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    elif 2 == int(t): 
        sql = "SELECT * FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id)"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql), submit_user_id=user_id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    else: 
        sql = "SELECT * FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status ' 
        
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " UNION ALL SELECT * FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id) "
        if status_value != 2:
            sql += ' AND status = :status ' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=user_id, submit_user_id=user_id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    data = process_task_data(rows, user_id)

    sql = "SELECT * FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:to_user_id,to_user_id) AND user_id <> :user_id"
    rows = g.db.execute(text(sql), user_id=user_id, to_user_id=user_id)
    data_tome = process_task_data(rows, user_id)

    return jsonify(data=data, next_page=next_page, data_tome=data_tome)

def get_task_data_by_ids(ids, user_id):
    data = []
    if ids:
        ids = ids.split(',')
        if len(ids):
            sql = "SELECT * FROM `tasks` WHERE id IN ({0})".format(','.join(ids))
            rows = g.db.execute(text(sql)).fetchall()
            data = process_task_data(rows, user_id)

    return data

@mod.route('/task/get_update', methods=['POST'])
def get_update():
    if request.form.has_key('user_id'):
        sql = "SELECT user_id, total_count FROM users_remind WHERE user_id=:user_id" 
        row = g.db.execute(text(sql), user_id=request.form['user_id']).first()
        return jsonify(error=0,data=dict(row))

@mod.route('/task/update_by_ids', methods=['POST'])
def update_by_ids():
    user_id = request.form['user_id']
    return jsonify(error=0)

@mod.route('/task/update', methods=['POST'])
def task_update():
    if request.method == 'POST' and request.form['id'] and request.form['user_id']:
        task = g.db.execute(text("SELECT * FROM tasks WHERE id=:id"), id=request.form['id']).first()
        old_to_user_id = set(task.to_user_id.split(',')) 
        old_submit_user_id = set(task.submit_user_id.split(',')) 
        update_ids = list(set(task.to_user_id.split(',')) | set(task.submit_user_id.split(',')))
        update_ids.append(task.user_id)
        user_row = g.db.execute(text("SELECT id, realname FROM users WHERE id=:id"), id=task.user_id).fetchone()
        my_user = g.db.execute(text("SELECT id, realname FROM users WHERE id=:id"), id=request.form['user_id']).fetchone()
        if task:
            if request.form.has_key('status') : 
                sql = "UPDATE tasks SET status=:status WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['status'])
                '''
                if str(request.form['status']) == '1':
                    if len(update_ids):
                        for notice_user_id in update_ids:
                            if str(request.form['user_id']) != str(notice_user_id):
                                UserNotice().process(user_id=notice_user_id, task_id=task.id, message=task.title, title=my_user.realname+"完成了")
                '''
            if request.form.has_key('title'):
                sql = "UPDATE tasks SET title=:title WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['title'])
            if request.form.has_key('priority'):
                sql = "UPDATE tasks SET priority=:priority WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['priority'])
            if request.form.has_key('end_time'):
                sql = "UPDATE tasks SET end_time=:end_time WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['end_time'])
            if request.form.has_key('notify_time'):
                sql = "UPDATE tasks SET notify_time=:notify_time WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['notify_time'])
            if request.form.has_key('to_user_id'):
                sql = "UPDATE tasks SET to_user_id=:to_user_id WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['to_user_id'])
            if request.form.has_key('submit_user_id'):
                sql = "UPDATE tasks SET submit_user_id=:submit_user_id WHERE id=:id"
                g.db.execute(text(sql), id=task.id, status=request.form['submit_user_id'])
            if request.form.has_key('is_del'):
                sql = "UPDATE tasks SET is_del=:is_del WHERE id=:id"
                g.db.execute(text(sql), id=task.id, is_del=1)
                if len(update_ids):
                    for notice_user_id in update_ids:
                        if str(request.form['user_id']) != str(notice_user_id):
                            UserNotice().process(user_id=notice_user_id, task_id=task.id, message=task.title, title=my_user.realname+"删除了")

            data = []
            if request.form.has_key('to_user_id') or request.form.has_key('submit_user_id'):
                data = dict(task)
                data['created_at'] = datetimeformat(data['created_at'])
                data['updated_at'] = datetimeformat(data['updated_at'])
                data['notify_time'] = data['notify_time'].strftime('%Y-%m-%d %T') if task.notify_time and isinstance(task.notify_time, datetime.datetime) else ''
                data['end_time'] = data['end_time'].strftime('%Y-%m-%d %T') if task.end_time and isinstance(task.end_time, datetime.datetime) else ''

            if request.form.has_key('to_user_id') and request.form['to_user_id']:
                TaskShare().update(old_user_id=old_to_user_id, share_user_id=set(request.form['to_user_id'].split(',')), own_id=task.user_id, task_id=task.id, title=task.title, realname=user_row.realname, data=data)
            elif request.form.has_key('submit_user_id') and request.form['submit_user_id']:
                TaskSubmit().update(old_user_id=old_submit_user_id, share_user_id=set(request.form['submit_user_id'].split(',')), task_id=task.id, own_id=task.id, title=task.title, realname=user_row.realname, data=data)
            else:
                data = dict(request.form)
                del data['id']
                TaskUpdateData().insert(user_ids=update_ids, task_id=task.id, data=data)
            
            return jsonify(error=0, code='success', message='修改成功', id=task.id)
    
    return jsonify(error=1, code='failed', message='修改失败')

@mod.route('/task/delete', methods=['POST'])
def task_delete():
    if request.method == 'POST' and request.form['id'] and request.form['user_id']:
        row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status FROM tasks WHERE id=:id"), id=request.form['id']).first()
        if row and row.user_id == int(request.form['user_id']):
            g.db.execute(text("UPDATE tasks SET is_del=:is_del, flag='1' WHERE id=:id"),is_del=1,id=request.form['id'])
            g.db.execute(text("UPDATE task_submit SET is_del=:is_del WHERE task_id=:id"),is_del=1,id=request.form['id'])
            return jsonify(error=0, code='success', message='删除成功', id=row.id)
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
            #rows = g.db.execute(select([users.c.id, users.c.company_id, users.c.username, users.c.realname, users.c.telephone, users.c.is_active], and_(users.c.company_id==request.form['company_id'], is_active==1))).fetchall()
            rows = g.db.execute(text('SELECT id, company_id, username, realname, telephone, is_active FROM users WHERE company_id=:company_id AND is_active=:is_active'), company_id=request.form['company_id'], is_active=1).fetchall()
            #rows = UserNotice().getbyid(request.form['user_i:'])
            data = [dict(zip(row.keys(), row)) for row in rows]  
            return jsonify(error=0, data=data)
    return jsonify(error=1)


@mod.route('/comment/get', methods=['POST'])
def commit_get():
    if request.method == 'POST' and request.form.has_key('task_id') and request.form.has_key('id'):
        rows = g.db.execute(text("SELECT tc.id, tc.user_id, tc.task_id, u.realname, content, tc.created_at FROM task_comments tc LEFT JOIN users u ON tc.user_id=u.id WHERE task_id=:task_id AND tc.id > :id"), task_id=request.form['task_id'], id=request.form['id']).fetchall() 
        data = []
        for row in rows:
            new_row = {'id': row.id, 'user_id': row.user_id, 'task_id': row.task_id, 'realname': row.realname, 'content': row.content}
            new_row['created_at'] = datetimeformat(row['created_at']) if row['created_at'] else '' 
            data.append(new_row)
        return jsonify(error=0, data=data)

@mod.route('/comment/create', methods=['POST'])
def comment_create():
    if request.method == 'POST' and request.form.has_key('task_id') and request.form.has_key('content') and request.form.has_key('user_id'):
        task_id = request.form['task_id']
        user_id = request.form['user_id']
        user_row = g.db.execute(text("SELECT id, realname FROM users WHERE id=:id"), id=user_id).fetchone()
        insert_id = TaskComment().insert(user_id=user_id, task_id=task_id, content=request.form['content'], realname=user_row.realname)
        return jsonify(error=0, id=insert_id) 

@mod.route('/task/share', methods=['GET', 'POST'])
def share():
    user_id = request.form['user_id']
    user_id = int(user_id)
    created_at = request.form['created_at'] if request.form.has_key('created_at') else 2
    status = request.form['status'] if request.form.has_key('status') else 'all'
    task_data_undone, task_data_complete, user_data, user_rows, user_avatar = Task().get_share_data(user_id=user_id, created_at=created_at, status=status)
    return jsonify(user_data=user_data, user_rows=user_rows, task_data_undone=task_data_undone, task_data_complete=task_data_complete, user_avatar=user_avatar)


#用户通知页面
@mod.route('/notice/get', methods=['POST'])
def notice_get():
    user_id = int(request.form['user_id']) 
    rows = g.db.execute(text("SELECT id, user_id, task_id, message, unread, created_at, updated_at, title FROM user_notices WHERE user_id=:user_id AND is_syn=:is_syn ORDER BY id ASC"), user_id=user_id, is_syn=0).fetchall() 
    data_notice = []
    for row in rows:
        new_row = {'id':row.id, 'user_id':row.user_id, 'task_id':row.task_id, 'message':row.message, 'title':row.title, 'unread':row.unread}
        new_row['created_at'] = datetimeformat(row['created_at']) 
        new_row['updated_at'] = datetimeformat(row['updated_at'])
        data_notice.append(dict(new_row))
        #data_notice.append(dict(row))data_notice = [dict(zip(row.keys(), row)) for row in rows]  
    
    rows = g.db.execute(text("SELECT id, user_id, task_id, data, is_syn FROM task_update_data WHERE user_id=:user_id AND is_syn=:is_syn ORDER BY ID ASC"), user_id=user_id, is_syn=0).fetchall()
    data_update = [dict(zip(row.keys(), row)) for row in rows ]

    return jsonify(data_update=data_update, data_notice=data_notice)

@mod.route('/notice/update', methods=['POST'])
def notice_update():
    user_id = int(request.form['user_id']) 
    data_notice_ids = request.form['data_notice_ids'] if request.form.has_key('data_notice_ids') else []
    data_update_ids = request.form['data_update_ids'] if request.form.has_key('data_update_ids') else []
    if user_id:
        if data_notice_ids:
            data_notice_ids = data_notice_ids.split(',')
            if len(data_notice_ids):
                sql = " UPDATE user_notices SET unread=:unread, is_syn=:is_syn WHERE user_id=:user_id AND id IN ({0})".format(','.join(data_notice_ids)) 
                res = g.db.execute(text(sql), user_id=user_id, unread=0, is_syn=1)
                num = int(res.rowcount)
                g.db.execute(text("INSERT INTO users_remind(user_id, total_count) VALUES(:user_id, 0) ON DUPLICATE KEY UPDATE total_count=total_count-:num"), user_id=user_id, num=num)

        if data_update_ids:
            data_update_ids = data_update_ids.split(',')
            if len(data_update_ids):
                sql = " UPDATE task_update_data SET is_syn=:is_syn WHERE user_id=:user_id AND id IN ({0})".format(','.join(data_update_ids)) 
                res = g.db.execute(text(sql), is_syn=1, user_id=user_id)

        return jsonify(error=0)
    return jsonify(error=1)
