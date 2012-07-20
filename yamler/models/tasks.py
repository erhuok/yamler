#encoding:utf8
from flask import g, url_for
import datetime,time
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from yamler.database import Model, metadata 
from werkzeug import http_date
from wtforms import Form, TextField, validators
from sqlalchemy.sql import select, text
from yamler.utils import iphone_notify, datetimeformat
from yamler.models.users import UserNotice
import json

class Task(Model):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String(150))
    user_id = Column(Integer, ForeignKey('users.id'))
    to_user_id = Column(String(45), default=0)
    submit_user_id = Column(String(45), default=0)
    status = Column(Integer, default = 0)
    flag = Column(Integer, default = 0)
    board_id = Column(Integer, default = 0)
    note = Column(String(200),default='')
    description = Column(String(500),default='')
    priority = Column(Integer, default=1)
    end_time = Column(DateTime,default = '') 
    notify_time = Column(DateTime,default = '') 
    created_at = Column(DateTime, default=datetime.datetime.now()) 
    updated_at = Column(DateTime,default=datetime.datetime.now()) 

    def __init__(self, title=None, user_id=None, note=None, priority=None, end_time=None, to_user_id=None, created_at=None, submit_user_id=None):
        self.title = title
        self.note = note
        self.user_id = user_id
        self.to_user_id = to_user_id
        self.priority = priority
        self.end_time = end_time
        self.created_at = created_at
        self.submit_user_id = submit_user_id

    def __repr__(self):
        return '<Task %r>' % (self.title)

    def to_json(self):
        result = dict(id = self.id, title = self.title, description=self.description, note = self.note, user_id = self.user_id, to_user_id=self.to_user_id, priority = self.priority, status = self.status, created_at = self.created_at.strftime('%Y-%m-%d %T')) 
        if self.end_time: 
            result['end_time'] = self.end_time.strftime('%m-%d %l:%M %p')
        else:
            result['end_time'] = '' 

        return result

    def get_share_data(self, user_id, created_at=None, status=None):
        start_time = ''
        if created_at and created_at != '0':
            created_at = int(created_at) 
            now = datetime.datetime.now()
            days = int(now.strftime('%w')) - 1
            if created_at == 2:
                days = days + 7
            elif created_at == 1:
                days = days
            elif created_at == 3:
                days = 30
            start_time = now - datetime.timedelta(days=days)
            start_time = start_time.strftime('%Y-%m-%d')

        task_data_undone = {}
        task_data_complete = {}
        user_ids = []
        user_rows = []
        user_data = {}
        user_avatar = {} 
        #未完成
        if status != 'complete':
            sql = "SELECT id,user_id,to_user_id,title,status,comment_count,created_at,submit_user_id,unread, priority FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:to_user_id,to_user_id) AND status=:status"
            if status == 'undone' and start_time:
                sql += ' AND created_at >= :start_time'

            sql += " UNION ALL SELECT id,user_id,to_user_id,title,status,comment_count,created_at,submit_user_id, unread, priority FROM tasks WHERE is_del='0' AND user_id=:user_id AND submit_user_id <> '0' "
            if status == 'undone' and start_time:
                sql += ' AND created_at >= :start_time'
            sql += " AND status=:status ORDER BY unread DESC,id DESC"
            task_rows = g.db.execute(text(sql), to_user_id=user_id, user_id=user_id, status='0', start_time=start_time).fetchall()

            for row in task_rows:
                if row.user_id == user_id:
                    if not row.submit_user_id:
                        continue
                    submit_user_id = row.submit_user_id.split(',')
                    for user_id2 in submit_user_id:
                        user_id2 = int(user_id2)
                        if user_id2:
                            if not task_data_undone.has_key(user_id2):
                                user_ids.append(str(user_id2)) 
                                task_data_undone[user_id2] = [] 
                            new_row = dict(row)
                            new_row['ismine'] = False
                            new_row['created_at'] = datetimeformat(new_row['created_at']) if new_row['created_at'] else ''
                            task_data_undone[user_id2].append(new_row)
                else:
                    user_id2 = int(row.user_id)
                    if user_id2:
                        if not task_data_undone.has_key(user_id2): 
                            user_ids.append(str(user_id2)) 
                            task_data_undone[user_id2] = [] 
                        new_row = dict(row)
                        new_row['ismine'] = True
                        new_row['created_at'] = datetimeformat(new_row['created_at']) if new_row['created_at'] else ''
                        task_data_undone[user_id2].append(new_row)

        #已完成
        if status != 'undone':
            sql = "SELECT id,user_id,to_user_id,title,status,comment_count,created_at,submit_user_id,unread, priority FROM tasks WHERE is_del='0' AND  FIND_IN_SET(:to_user_id,to_user_id) AND status=:status"
            if start_time:
                sql += ' AND created_at >= :start_time'
            sql += " UNION ALL SELECT id,user_id,to_user_id,title,status,comment_count,created_at,submit_user_id, unread, priority FROM tasks WHERE is_del='0' AND user_id=:user_id AND submit_user_id <> '0' "
            if start_time:
                sql += ' AND created_at >= :start_time'
            sql += " AND status=:status ORDER BY unread DESC, id DESC"
            task_rows = g.db.execute(text(sql), to_user_id=user_id, user_id=user_id, status=1, start_time=start_time).fetchall()
            for row in task_rows:
                if row.user_id == user_id:
                    if not row.submit_user_id:
                        continue
                    submit_user_id = row.submit_user_id.split(',')
                    for user_id2 in submit_user_id:
                        user_id2 = int(user_id2)
                        if user_id2:
                            if not task_data_complete.has_key(user_id2):
                                user_ids.append(str(user_id2)) 
                                task_data_complete[user_id2] = [] 
                            new_row = dict(row)
                            new_row['ismine'] = False
                            new_row['created_at'] = datetimeformat(new_row['created_at']) if new_row['created_at'] else ''
                            task_data_complete[user_id2].append(new_row)
                else:
                    user_id2 = int(row.user_id)
                    if user_id2:
                        if not task_data_complete.has_key(user_id2): 
                            user_ids.append(str(user_id2)) 
                            task_data_complete[user_id2] = [] 
                        new_row = dict(row)
                        new_row['ismine'] = True
                        new_row['created_at'] = datetimeformat(new_row['created_at']) if new_row['created_at'] else ''
                        task_data_complete[user_id2].append(new_row)

        user_ids = list(set(user_ids)) 
        if len(user_ids) and ','.join(user_ids):
            sql = "SELECT id, realname, avatar, telephone FROM `users` WHERE is_active=:is_active AND id IN ({0})".format(','.join(user_ids)) 
            user_rows = g.db.execute(text(sql), is_active=1).fetchall()
            for user_row in user_rows:
                user_data[user_row.id] = user_row.realname 
                user_avatar[user_row.id] = url_for('static', filename='uploads/small/'+user_row.avatar) if user_row.avatar else ''

        return (task_data_undone, task_data_complete, user_data, [dict(zip(res.keys(), res)) for res in user_rows], user_avatar)
                    
class TaskUpdateData():
    __tablename__ = 'task_update_data'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    task_id = Column(Integer)
    data = Column(String(1000))
    is_syn = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.now()) 
    updated_at = Column(DateTime,default=datetime.datetime.now()) 
    
    def __init__(self, user_id=None, task_id=None):
        self.task_id = task_id
        self.user_id = user_id

    def insert(self, user_ids, task_id, data):
        if len(user_ids):
            sql = "INSERT INTO task_update_data SET user_id=:user_id, task_id=:task_id, data=:data, created_at=:created_at"
            for uid in user_ids:
                if uid and uid != ',' and int(str(uid)) > 0:
                    g.db.execute(text(sql), user_id=uid, task_id=task_id, data=json.dumps(data), created_at=datetime.datetime.now())

class TaskComment(Model):
    __tablename__ = 'task_comments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    task_id = Column(Integer)
    content = Column(String(200))  
    created_at = Column(DateTime, default=datetime.datetime.now()) 
    updated_at = Column(DateTime,default=datetime.datetime.now()) 

    def __init__(self, user_id=None, task_id=None, content=None):
        self.user_id = user_id
        self.task_id = task_id
        self.content = content

    def insert(self, task_id, user_id, content, realname):
        row = g.db.execute(text("SELECT id, user_id, submit_user_id, to_user_id, comment_count FROM tasks WHERE id=:id"),id=task_id).fetchone()
        if row:
            created_at = datetime.datetime.now()
            res = g.db.execute(text("INSERT INTO task_comments SET user_id=:user_id, task_id=:task_id, content=:content, created_at=:created_at"), user_id=user_id, task_id=task_id, content=content, created_at=created_at)
            if res.lastrowid:
                g.db.execute(text("UPDATE tasks SET comment_count = comment_count +1, unread=:unread, flag='0' WHERE id = :id"), id=task_id, unread=1)
                update_ids = list(set(row.to_user_id.split(',')) | set(row.submit_user_id.split(','))) 
                update_ids.append(user_id)
                TaskUpdateData().insert(user_ids=update_ids, task_id=task_id, data={'comment_count': row.comment_count+1})

                to_user_id = [] 
                submit_user_id = []
                #通知提醒
                if row.to_user_id:
                    to_user_id = row.to_user_id.split(',')
                    to_user_id.append(str(row.user_id))
                    to_user_id = [ uid for uid in to_user_id if uid != str(user_id) ]
                    #sql = " UPDATE task_share SET unread=:unread WHERE task_id=:task_id AND user_id IN ({0})".format(','.join(to_user_id)) 
                    #g.db.execute(text(sql), task_id=task_id, unread=1)

                if row.submit_user_id:
                    #g.db.execute(text("UPDATE task_submit SET is_comment=:is_comment WHERE task_id=:task_id"), task_id=task_id, is_comment=0)
                    submit_user_id = row.submit_user_id.split(',')
                    submit_user_id.append(str(row.user_id))
                    submit_user_id = [ uid for uid in submit_user_id if uid != str(user_id) ]
                    #sql = " UPDATE task_submit SET unread=:unread WHERE task_id=:task_id AND user_id IN ({0})".format(','.join(submit_user_id)) 
                    #g.db.execute(text(sql), task_id=task_id, unread=1)
                notify_user_id = list(set(to_user_id) | set(submit_user_id))
                if notify_user_id:
                    for uid in notify_user_id:
                        if int(uid) != int(user_id):
                            UserNotice().process(user_id=uid, task_id=task_id, message=content, title="来自"+realname+"的回复")
                    iphone_notify(notify_user_id, type="comment", realname=realname, title=content)

                return res.lastrowid

class TaskShare(Model):
    __tablename__ = 'task_share'
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    user_id = Column(Integer)
    own_id = Column(Integer)
    unread = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.now()) 
    updated_at = Column(DateTime,default=datetime.datetime.now()) 
    
    def insert(self, task_id, share_user_id, own_id=None, title=None, realname=None):
        own_id = own_id if own_id else g.user.id
        if not task_id or not share_user_id:
            return False
        for user_id in share_user_id:
            res = g.db.execute(text("SELECT id FROM task_share WHERE user_id=:user_id AND task_id=:task_id"), user_id=user_id, task_id=task_id).fetchone()
            if res is None:
                g.db.execute(text("INSERT INTO task_share SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=own_id, unread=1, created_at=datetime.datetime.now() )        
            UserNotice().process(user_id=user_id, task_id=task_id, message=title, title=realname+'递交给我') 
        iphone_notify(share_user_id, type='share', title=title, realname=realname) 
        
    def update(self, share_user_id, old_user_id, task_id, own_id=None, title=None, realname=None, data=None):
        own_id = own_id if own_id else g.user.id
        insert_ids = share_user_id.difference(old_user_id)
        if len(insert_ids):
            g.db.execute(text("UPDATE tasks SET unread=:unread WHERE id=:id"), id=task_id) 
            for user_id in insert_ids:
                if int(user_id) > 0:
                    g.db.execute(text("INSERT INTO task_share SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=own_id, unread=1, created_at=datetime.datetime.now() )        

                    UserNotice().process(user_id=user_id, task_id=task_id, message=title, title=realname+"递交给我")
            if data:
                TaskUpdateData().insert(user_ids=insert_ids, data=data, task_id=task_id)
            iphone_notify(insert_ids, type='share', title=title, realname=realname)

        delete_ids = old_user_id.difference(share_user_id)
        if len(delete_ids):
            for user_id in delete_ids:
                g.db.execute(text("DELETE FROM `task_share` WHERE user_id=:user_id AND task_id=:task_id"), task_id=task_id, user_id=user_id)
                g.db.execute(text("DELETE FROM `user_notices` WHERE user_id=:user_id AND task_id=:task_id"), user_id=user_id, task_id=task_id)
                g.db.execute(text("INSERT INTO users_remind(user_id, total_count) VALUES(:user_id, 0) ON DUPLICATE KEY UPDATE total_count=total_count-1"), user_id=user_id)

            TaskUpdateData().insert(user_ids=delete_ids, data={'is_del':1}, task_id=task_id)

class TaskSubmit(Model):
    __tablename__ = 'task_submit'
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    user_id = Column(Integer)
    own_id = Column(Integer)
    unread = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.now()) 
    updated_at = Column(DateTime,default=datetime.datetime.now()) 
    
    def insert(self, task_id, share_user_id, own_id=None, title=None, realname=None):
        own_id = own_id if own_id else g.user.id
        if not task_id or not share_user_id:
            return False
        for user_id in share_user_id:
            if user_id > 0:
                res = g.db.execute(text("SELECT id FROM task_submit WHERE user_id=:user_id AND task_id=:task_id"), user_id=user_id, task_id=task_id).fetchone()
                if res is None:
                    g.db.execute(text("INSERT INTO task_submit SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=own_id, unread=1, created_at=datetime.datetime.now() )        
                UserNotice().process(user_id=user_id, task_id=task_id, message=title, title=realname+"安排给我")

        iphone_notify(share_user_id, type='submit', title=title, realname=realname)
                

    def update(self, share_user_id, old_user_id, task_id, own_id=None, title=None, realname=None, data=None):
        own_id = own_id if own_id else g.user.id
        insert_ids = share_user_id.difference(old_user_id)
        if len(insert_ids):
            g.db.execute(text("UPDATE tasks SET unread=:unread WHERE id=:id"), id=task_id) 
            for user_id in insert_ids:
                if int(user_id) > 0:
                    g.db.execute(text("INSERT INTO task_submit SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=own_id, unread=1, created_at=datetime.datetime.now() )        
                    UserNotice().process(user_id=user_id, task_id=task_id, message=title, title=realname+"安排给我")

            if data:
                TaskUpdateData().insert(user_ids=insert_ids, data=data, task_id=task_id)
            iphone_notify(insert_ids, type='submit', title=title, realname=realname)
        
        delete_ids = old_user_id.difference(share_user_id)
        if len(delete_ids):
            for user_id in delete_ids:
                if user_id > 0:
                    g.db.execute(text("UPDATE `task_submit` SET is_del=:is_del WHERE user_id=:user_id AND task_id=:task_id"), task_id=task_id, user_id=user_id, is_del=1)
                    g.db.execute(text("DELETE FROM `user_notices` WHERE user_id=:user_id AND task_id=:task_id"), user_id=user_id, task_id=task_id)
                    g.db.execute(text("INSERT INTO users_remind(user_id, total_count) VALUES(:user_id, 0) ON DUPLICATE KEY UPDATE total_count=total_count-1"), user_id=user_id)
                    TaskUpdateData().insert(user_ids=delete_ids, data={'is_del':1}, task_id=task_id)



tasks = Table('tasks', metadata, autoload=True)
task_comments = Table('task_comments', metadata, autoload=True)
task_share = Table('task_share', metadata, autoload=True)
task_submit = Table('task_submit', metadata, autoload=True)

class TaskForm(Form):
    title = TextField('标题', [validators.required()])

