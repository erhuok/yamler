# encoding:utf8
from flask import Blueprint,request,render_template,session, g,jsonify
from sqlalchemy.sql import select, text 
from yamler.models.tasks import tasks
from yamler.models.users import users 
from datetime import datetime
import json

mod = Blueprint('task', __name__, url_prefix='/task')

@mod.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST' and request.form.has_key('title'):
        res = g.db.execute(tasks.insert().values({tasks.c.title: request.form['title'], 
                                                  tasks.c.user_id: g.user.id,
                                                  tasks.c.created_at: datetime.now(), 
                                                  tasks.c.status: int(request.form['status']),
                                                  tasks.c.board_id: int(request.form['board_id']),
                                                 })) 
        return jsonify(error=0, title=request.form['title'], realname=g.user.realname, id=res.inserted_primary_key)
    return jsonify(error=1, msg="没有内容")

'''
@mod.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if request.method == 'POST':
        g.db.execute(text("UPDATE tasks SET title=:title, status=:status WHERE id=:id"), title=request.form['title'],status=request.form['status'], id=id)
        return '修改成功'
    row = g.db.execute(text("SELECT id,board_id,user_id,to_user_id,title,created_at,end_time,status FROM tasks WHERE id=:id"), id=id).first()
    row = dict(row)
    return render_template('task/update.html', row=row) 
    #return render_template('task/update.html', row=row, data_users=json.dumps(data_users), share_users_default=json.dumps(row['share_users'])) 
'''

@mod.route('/update/<int:id>', methods=['POST'])
def update(id):
    if request.form.has_key('title'):
        g.db.execute(text("UPDATE tasks SET title=:title WHERE id=:id"), id=id, title=request.form['title'])
        return jsonify(error=0, title=request.form['title'], id=id)
    if request.form.has_key('status'):
        g.db.execute(text("UPDATE tasks SET status=:status WHERE id=:id"), id=id, status=request.form['status'])
        return jsonify(error=0)
    return jsonify(error=1)

@mod.route('/update_share/<int:id>', methods=['POST', 'GET'])
def share(id):
    row = g.db.execute(text("SELECT id,board_id,user_id,to_user_id,title,created_at,end_time,status FROM tasks WHERE id=:id"), id=id).first()
    if request.method == 'POST' and row and request.form['to_user_id']:
        res = g.db.execute(text("UPDATE tasks SET to_user_id=:to_user_id WHERE id=:id"), to_user_id=request.form['to_user_id'].lstrip(','), id=id) 
        return jsonify(error=0) 
    share_users = dict()
    if row.to_user_id:
        sql = "SELECT id, realname FROM users WHERE ID IN ({0})".format(','.join(row.to_user_id.split(',')))
        user_rows = g.db.execute(text(sql)).fetchall()
        share_users = dict(user_rows)

    company_users = g.db.execute(text("SELECT id, realname  FROM users WHERE company_id=:company_id"), company_id=g.company.id).fetchall()
    data_users = [ {'id': company_user.id, 'value': company_user.realname} for company_user in company_users]
    return render_template('task/update_share.html', 
                           row=row, 
                           share_users_default=json.dumps(share_users.values()),
                           data_users = json.dumps(data_users),
                          )


@mod.route('/get/<int:id>')
def get(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status,comment_count FROM tasks WHERE id=:id"), id=id).first()
    row = dict(row)
    row['share_users'] = ''
    if row and row.has_key('to_user_id') and row['to_user_id']:
        sql = "SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN ({0})".format(','.join(row['to_user_id'].lstrip(',').split(','))) 
        result = g.db.execute(text(sql)).first()
        row['share_users'] = result['share_users']
    return jsonify(row=row)

@mod.route('/delete/<int:id>')
def delete(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status FROM tasks WHERE id=:id"), id=id).first()
    if row and row['user_id'] == g.user.id:
        g.db.execute(text("UPDATE tasks SET is_del=:is_del WHERE id=:id"),is_del=1,id=id)
        return jsonify(id=id)
