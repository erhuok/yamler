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
    sql = "SELECT id,user_id,to_user_id,title,status,comment_count,created_at FROM tasks WHERE is_del='0' AND :to_user_id IN (to_user_id)"
    task_rows = g.db.execute(text(sql), to_user_id=g.user.id).fetchall()
    #for key, row in enumerate(task_rows):
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

    return render_template('home/share.html', task_data=task_data, user_data=user_data)

@mod.route('/mytask', methods=['GET', 'POST'])
def mytask():
    s = text("SELECT id,user_id,to_user_id,title,created_at,end_time,status FROM tasks WHERE user_id = :user_id") 
    task_rows = g.db.execute(s, user_id=g.user.id).fetchall()
    return render_template('home/mytask.html', task_rows=task_rows, pagename='mytask') 

@mod.route('/publish', methods=['GET', 'POST'])
def publish():
    if request.method == 'POST' and request.form['title']:
        res = g.db.execute(tasks.insert().values({tasks.c.title: request.form['title'], 
                                            tasks.c.user_id: g.user.id,
                                            tasks.c.created_at: datetime.now(), 
                                            tasks.c.to_user_id: request.form['to_user_id'].lstrip(',')
                                           })) 
        return jsonify(title=request.form['title'], ismine=True, realname=g.user.realname, id=res.inserted_primary_key, share_users=request.form['share_users'].lstrip(','))

@mod.route('/getMyFeed')
def getMyFeed():
    t = int(request.args.get('t',0))
    page = int(request.args.get('page',1))
    limit = 20
    skip = (page-1) * limit
    rows = g.db.execute(text("SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count FROM tasks WHERE user_id=:user_id AND is_del='0' ORDER BY status ASC, created_at DESC LIMIT :skip, :limit"),user_id=g.user.id, skip=skip, limit=limit).fetchall();

    _test = '''
    if t == 1:
    elif t == 2:
        rows = g.db.execute(text("SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count FROM tasks WHERE to_user_id IN (:to_user_id) AND is_del='0' ORDER BY created_at DESC LIMIT :skip, :limit"),to_user_id=g.user.id, skip=skip, limit=limit).fetchall();
    else:
        s = text("SELECT id,user_id,to_user_id,title,created_at,end_time,status,comment_count FROM tasks WHERE user_id = :user_id AND is_del='0' UNION ALL SELECT id,user_id,to_user_id,title,created_at,end_time,status, comment_count FROM tasks WHERE to_user_id IN (:to_user_id) AND is_del='0' ORDER BY created_at DESC LIMIT :skip, :limit") 
        rows = g.db.execute(s, user_id=g.user.id, to_user_id=g.user.id, skip=skip, limit=limit).fetchall()
    '''

    #user_sql = text("SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN ( :id )")
    data = []
    #user_sql = "SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN :id "
    for row in rows:
        new_row = {}
        new_row['id'] = row['id']
        new_row['comment_count'] = row['comment_count']
        new_row['user_id'] = row['user_id'] 
        new_row['created_at'] = row['created_at'].strftime('%m月%d日 %H:%M') if row['created_at'] else ''
        new_row['title'] = row['title'] 
        new_row['status'] = row['status'] 
        new_row['realname'] = g.user.realname
        new_row['share_users'] = ''
        if row['to_user_id']:
            user_ids = row['to_user_id'].lstrip(',').split(',')
            user_sql = "SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
            result = g.db.execute(text(user_sql)).first()
            new_row['share_users'] = result['share_users'] 
        data.append(new_row)
    return jsonify(data=data)
