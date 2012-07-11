#-*- encoding:utf-8 -*-
import datetime
from flask import Blueprint,request,render_template,session, g, jsonify
from yamler.models.tasks import tasks, task_comments
from sqlalchemy.sql import select, text
from yamler.utils import iphone_notify, datetimeformat

mod = Blueprint('comment', __name__, url_prefix='/comment')

@mod.route('/get/<int:task_id>')
def get(task_id):
    comment_rows = g.db.execute(text("SELECT id, task_id, user_id, content, created_at FROM task_comments WHERE task_id=:task_id"), task_id=task_id).fetchall() 
    data = []
    for row in comment_rows:
        new_row = {'id': row['id'], 'user_id': row['user_id'], 'content': row['content']} 
        new_row['created_at'] = row['created_at'].strftime('%Y-%m-%d %T')
        if row['user_id'] != g.user.id:
            result = g.db.execute(text("SELECT id, realname from users WHERE id=:user_id LIMIT 1"), user_id=row['user_id']).first()
            new_row['realname'] = result['realname']
        else:
            new_row['realname'] = g.user.realname

        data.append(new_row)
    return jsonify(data=data, task_id=task_id) 

@mod.route('/create/<int:task_id>', methods=['POST'])
def create(task_id):
    if request.form['comment_content'] and g.user.id:
        row = g.db.execute(text("SELECT id, user_id, submit_user_id, to_user_id FROM tasks WHERE id=:id"),id=task_id).fetchone()
        if row:
            created_at = datetime.datetime.now()
            res = g.db.execute(task_comments.insert().values({
                task_comments.c.user_id: g.user.id, 
                task_comments.c.task_id: task_id, 
                task_comments.c.content: request.form['comment_content'], 
                task_comments.c.created_at: created_at,
            }))
            if res.lastrowid:
                g.db.execute(text("UPDATE tasks SET comment_count = comment_count +1, unread=:unread, flag='0' WHERE id = :id"), id=task_id, unread=1)

                to_user_id = [] 
                submit_user_id = []
                #通知提醒
                if row.to_user_id:
                    to_user_id = row.to_user_id.split(',')
                    to_user_id.append(str(row.user_id))
                    to_user_id = [ user_id for user_id in to_user_id if user_id != str(g.user.id) ]
                    sql = " UPDATE task_share SET unread=:unread WHERE task_id=:task_id AND user_id IN ({0})".format(','.join(to_user_id)) 
                    g.db.execute(text(sql), task_id=task_id, unread=1)

                if row.submit_user_id:
                    g.db.execute(text("UPDATE task_submit SET is_comment=:is_comment WHERE task_id=:task_id"), task_id=task_id, is_comment=0)
                    submit_user_id = row.submit_user_id.split(',')
                    submit_user_id.append(str(row.user_id))
                    submit_user_id = [user_id for user_id in submit_user_id if user_id != str(g.user.id) ]
                    sql = " UPDATE task_submit SET unread=:unread WHERE task_id=:task_id AND user_id IN ({0})".format(','.join(submit_user_id)) 
                    g.db.execute(text(sql), task_id=task_id, unread=1)
                
                notify_user_id = list(set(to_user_id) | set(submit_user_id))
                if notify_user_id:
                    iphone_notify(notify_user_id, type="comment", realname=g.user.realname, title=request.form['comment_content'])
                    
            return jsonify(content=request.form['comment_content'], 
                           task_id=task_id, 
                           realname=g.user.realname, 
                           created_at=created_at.strftime('%Y-%m-%d %T')
                          )
