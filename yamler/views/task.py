# encoding:utf8
from flask import Blueprint,request,render_template,session, g,jsonify
from sqlalchemy.sql import select, text 
from yamler.models.tasks import tasks, TaskShare, TaskSubmit, TaskUpdateData
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


@mod.route('/update/<int:id>', methods=['POST'])
def update(id):
    row = g.db.execute(text("SELECT id,board_id,user_id,to_user_id,submit_user_id,title,end_time,status FROM tasks WHERE id=:id"), id=id).first()
    update_ids = list(set(row.to_user_id) | set(row.submit_user_id))
    update_ids.append(row.user_id)

    if request.form.has_key('title'):
        g.db.execute(text("UPDATE tasks SET title=:title, flag='0' WHERE id=:id"), id=id, title=request.form['title'])
        if update_ids:
            TaskUpdateData().insert(user_ids=update_ids, data={'title':request.form['title']}, task_id=id)

        return jsonify(error=0, title=request.form['title'], id=id)
    if request.form.has_key('status'):
        end_time = datetime.now() if request.form['status'] else ''
        g.db.execute(text("UPDATE tasks SET status=:status, end_time=:end_time, flag='0' WHERE id=:id"), id=id, status=request.form['status'], end_time=end_time)
        if update_ids:
            TaskUpdateData().insert(user_ids=update_ids, data={'status':request.form['status']}, task_id=id)
        #if row.submit_user_id:
        #    ids = row.submit_user_id.split(',')
        #    sql = "UPDATE `task_submit` SET is_status='0' WHERE task_id=:task_id AND user_id IN ({0})".format(','.join(ids))
        #    g.db.execute(text(sql), task_id=id)
        
        return jsonify(error=0)
    if request.form.has_key('unread'):
        g.db.execute(text("UPDATE tasks SET unread=:unread WHERE id=:id"), id=id, unread=request.form['unread'])
        return jsonify(error=0)
    return jsonify(error=1)

@mod.route('/update_share/<int:id>', methods=['POST', 'GET'])
def share(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status FROM tasks WHERE id=:id"), id=id).first()
    if request.method == 'POST' and row:
        to_user_id = request.form['to_user_id'].lstrip(',')
        res = g.db.execute(text("UPDATE tasks SET to_user_id=:to_user_id, flag='0' WHERE id=:id"), to_user_id=request.form['to_user_id'].lstrip(','), id=id) 
        TaskShare().update(old_user_id=set(row.to_user_id.split(',')), share_user_id=set(to_user_id.split(',')), task_id=id, title=row.title, realname=g.user.realname, data=dict(row))
        return jsonify(error=0) 
    share_users = dict()
    if row.to_user_id:
        sql = "SELECT id, realname FROM users WHERE id IN ({0})".format(','.join(row.to_user_id.split(',')))
        user_rows = g.db.execute(text(sql)).fetchall()
        share_users = dict(user_rows)
        #share_users = [ user_row.realname  for user_row in user_rows]
    company_users = g.db.execute(text("SELECT id, realname  FROM users WHERE company_id=:company_id AND is_active=:is_active AND id <> :id"), company_id=g.company.id, is_active=1, id=g.user.id).fetchall()
    data_users = [ {'id': company_user.id, 'value': company_user.realname} for company_user in company_users]

    return jsonify(share_users_default=share_users.values(), data_users=data_users, to_user_id=row.to_user_id)
    '''
    return render_template('task/update_share.html', 
                           row=row, 
                           share_users_default=json.dumps(share_users.values()),
                           data_users = json.dumps(data_users),
                          )
    '''
@mod.route('/update_submit/<int:id>', methods=['POST', 'GET'])
def submit(id):
    row = g.db.execute(text("SELECT id,board_id,user_id,to_user_id,title,end_time,status,submit_user_id FROM tasks WHERE id=:id"), id=id).first()
    if request.method == 'POST' and row:
        submit_user_id = request.form['submit_user_id'].lstrip(',')
        res = g.db.execute(text("UPDATE tasks SET submit_user_id=:submit_user_id, flag='0' WHERE id=:id"), submit_user_id=request.form['submit_user_id'].lstrip(','), id=id) 
        TaskSubmit().update(old_user_id=set(row.submit_user_id.split(',')), share_user_id=set(submit_user_id.split(',')), task_id=id,  title=row.title, realname=g.user.realname, data=dict(row))
        return jsonify(error=0) 
    share_users = dict()
    if row.submit_user_id:
        sql = "SELECT id, realname FROM users WHERE ID IN ({0})".format(','.join(row.submit_user_id.split(',')))
        user_rows = g.db.execute(text(sql)).fetchall()
        share_users = dict(user_rows)

    company_users = g.db.execute(text("SELECT id, realname  FROM users WHERE company_id=:company_id AND is_active=:is_active AND id <> :id"), company_id=g.company.id, is_active=1, id=g.user.id).fetchall()
    data_users = [ {'id': company_user.id, 'value': company_user.realname} for company_user in company_users]

    return jsonify(to_user_id=row.submit_user_id, data_users=data_users, share_users_default=share_users.values())

@mod.route('/get/<int:id>')
def get(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status,comment_count,submit_user_id,created_at FROM tasks WHERE id=:id"), id=id).first()
    row = dict(row)
    row['share_users'] = []
    row['submit_users'] = []   
    row['created_at'] = row['created_at'].strftime('%m月%d日 %H:%m') 

    if row and row.has_key('to_user_id') and row['to_user_id']:
        user_ids = row['to_user_id'].lstrip(',').split(',')
        user_sql = "SELECT id, realname  FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
        result = g.db.execute(text(user_sql)).fetchall()
        row['share_users'] = [dict(zip(res.keys(), res)) for res in result]  
     
    if row and row.has_key('submit_user_id') and row['submit_user_id'] :
        user_ids = row['submit_user_id'].lstrip(',').split(',')
        user_sql = "SELECT id, realname  FROM `users` WHERE id IN ({0})".format(','.join(user_ids))
        result = g.db.execute(text(user_sql)).fetchall()
        row['submit_users'] = [dict(zip(res.keys(), res)) for res in result]   

    return jsonify(row=row)


@mod.route('/delete/<int:id>')
def delete(id):
    row = g.db.execute(text("SELECT id,user_id,to_user_id,title,status, submit_user_id FROM tasks WHERE id=:id"), id=id).first()
    if row and row['user_id'] == g.user.id:
        g.db.execute(text("UPDATE tasks SET is_del=:is_del, flag='0' WHERE id=:id"),is_del=1,id=id)
        update_ids = list(set(row.to_user_id) | set(row.submit_user_id))
        update_ids.append(row.user_id)
        if update_ids:
            TaskUpdateData().insert(user_ids=update_ids, data={'is_del':1}, task_id=id)
        return jsonify(id=id)
