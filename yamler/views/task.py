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

@mod.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if request.method == 'POST':
        g.db.execute(text("UPDATE tasks SET title=:title, status=:status WHERE id=:id"), title=request.form['title'],status=request.form['status'], id=id)
        return '修改成功'
    row = g.db.execute(text("SELECT id,board_id,user_id,to_user_id,title,created_at,end_time,status FROM tasks WHERE id=:id"), id=id).first()
    row = dict(row)
    return render_template('task/update.html', row=row) 
    #return render_template('task/update.html', row=row, data_users=json.dumps(data_users), share_users_default=json.dumps(row['share_users'])) 


@mod.route('/update_status', methods=['POST'])
def update_status():
    if request.form.has_key('id') and request.form.has_key('status'):
        id = int(request.form['id'].strip('list')) 
        if request.form['status'] == 'todo_list':
            status = 0
        elif request.form['status'] == 'doing_list':
            status = 2
        elif request.form['status'] == 'done_list':
            status = 1
        if id and status is not None:
            g.db.execute(text("UPDATE tasks SET status=:status WHERE id=:id"), id=id, status=status)
            return jsonify(error=0)
    return jsonify(error=1)

@mod.route('/share/<int:id>')
def share():
    return render_template('task/share')


@mod.route('/get/<int:id>')
def get(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status FROM tasks WHERE id=:id"), id=id).first()
    row = dict(row)
    row['share_users'] = ''
    if row and row.has_key('to_user_id') and row['to_user_id']:
        if row['to_user_id']:
            sql = "SELECT GROUP_CONCAT( realname ) AS share_users FROM `users` WHERE id IN ("
            to_ids = ''
            for s in row['to_user_id'].split(','):
                if s:
                    to_ids += s.strip()+','
                    to_ids = to_ids.rstrip(',')
                    if to_ids != '0':
                        sql += to_ids
                        sql += ")" 
                        result = g.db.execute(text(sql)).first()
                        row['share_users'] = result['share_users']
                        return jsonify(row=row)

@mod.route('/delete/<int:id>')
def delete(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status FROM tasks WHERE id=:id"), id=id).first()
    if row and row['user_id'] == g.user.id:
        g.db.execute(text("UPDATE tasks SET is_del=:is_del WHERE id=:id"),is_del=1,id=id)
        return jsonify(id=id)
