# encoding:utf8
from datetime import datetime, date
from flask import Blueprint,request,render_template,session, g, jsonify
from yamler.models.users import User,RegistrationForm,LoginForm
from yamler.database import db_session 
from yamler import app
from yamler.utils import required_login
from yamler.models.companies import companies
from yamler.models.groups import groups 
from yamler.models.tasks import tasks, task_comments
from yamler.models.boards import Board, boards
from sqlalchemy.sql import select, text
from yamler.utils import convert_time 

mod = Blueprint('home', __name__, url_prefix='/home')

@mod.route('/account', methods=['GET', 'POST'])
@required_login
def account():
    return render_template('home/account.html')

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
def share():
    sql = "SELECT id,user_id,to_user_id,title,status,comment_count,created_at FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:to_user_id,to_user_id)  ORDER BY status ASC, id DESC"
    task_rows = g.db.execute(text(sql), to_user_id=g.user.id).fetchall()

    #sql = "SELECT id,user_id,to_user_id,title,status,comment_count,created_at FROM tasks WHERE is_del='0' AND  user_id=:user_id AND to_user_id <> '' ORDER BY status ASC, id DESC"
    #task_my_rows = g.db.execute(text(sql), user_id=g.user.id).fetchall()
    #for key, row in enumerate(task_rows):
    task_data = {}
    user_ids = []
    user_data = {}
    if task_rows:
        for row in task_rows:
            if not task_data.has_key(row.user_id): 
                user_ids.append(str(row.user_id)) 
                task_data[row.user_id] = [] 
                #for my_row in task_my_rows:
                    #if str(row.user_id)  in my_row.to_user_id:
                        #new_row = dict(my_row)
                        #new_row['ismine'] = True
                        #task_data[row.user_id].append(my_row)
                        #del my_row
            task_data[row.user_id].append(dict(row))
          
        if task_rows and ','.join(user_ids):
            sql = "SELECT id, realname FROM `users` WHERE id IN ({0})".format(','.join(user_ids)) 
            user_rows = g.db.execute(text(sql)).fetchall()
            for row in user_rows:
                user_data[row.id] = row.realname
    return render_template('home/share.html', task_data=task_data, user_data=user_data)

@mod.route('/mytask', methods=['GET', 'POST'])
def mytask():
    s = text("SELECT id,user_id,to_user_id,title,created_at,end_time,status FROM tasks WHERE user_id = :user_id") 
    task_rows = g.db.execute(s, user_id=g.user.id).fetchall()
    return render_template('home/mytask.html', task_rows=task_rows, pagename='mytask') 

@mod.route('/publish', methods=['GET', 'POST'])
def publish():
    if request.method == 'POST' and request.form['title']:
        created_at = datetime.now()
        res = g.db.execute(tasks.insert().values({tasks.c.title: request.form['title'], 
                                                  tasks.c.user_id: g.user.id,
                                                  tasks.c.created_at: created_at, 
                                                  tasks.c.to_user_id: request.form['to_user_id'].lstrip(','), 
                                                  tasks.c.submit_user_id: request.form['submit_user_id'].lstrip(',') 
                                                 })) 
        share_users = [ {'realname': row } for row in request.form['share_users'].lstrip(',').split(',') if row] 
        submit_users = [ {'realname': row } for row in request.form['submit_users'].lstrip(',').split(',') if row] 
        return jsonify(title=request.form['title'], 
                       ismine=True, 
                       realname=g.user.realname, 
                       id=res.inserted_primary_key, 
                       share_users=share_users, 
                       submit_users=submit_users,
                       created_at = created_at.strftime('%m月%d日 %H:%m'),
                      )

@mod.route('/getMyFeed')
def getMyFeed():
    t = int(request.args.get('t',0))
    default_status = {'complete':1 , 'undone':0 , 'all':2} 
    status = request.args.get('status','all')
    status_value = int(default_status[status]) 

    created_at = request.args.get('created_at', '')
    start_time = convert_time(created_at) if created_at else '' 
    print start_time
    page = int(request.args.get('page',1))
    limit = 20
    skip = (page-1) * limit
    next_page = '/home/getMyFeed?t='+str(t)+'&status='+str(status)+'&page='+str(page+1)+'&created_at='+str(created_at) 
    #只看我自己的
    if 1 == int(t):
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id FROM tasks WHERE user_id=:user_id AND is_del='0'"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql),user_id=g.user.id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
    elif 2 == int(t): 
        sql = "SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count,submit_user_id FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:submit_user_id,submit_user_id)"
        if status_value != 2:
            sql += ' AND status = :status' 
        if start_time:
            sql += ' AND created_at > :created_at'
        sql += " ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"
        rows = g.db.execute(text(sql), submit_user_id=g.user.id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()
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
        rows = g.db.execute(text(sql),user_id=g.user.id, submit_user_id=g.user.id, skip=skip, limit=limit, status=str(status_value), created_at=start_time).fetchall()

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
        if row['user_id'] == g.user.id:
            new_row['realname'] = '我' 
            new_row['ismine'] = True
        #安排给我的
        else:
            new_row['ismine'] = False 
            new_row['realname'] = g.db.execute(text("SELECT id, realname FROM `users` WHERE id=:id"), id=row['user_id']).first().realname

        data.append(new_row)
    return jsonify(data=data, next_page=next_page)
