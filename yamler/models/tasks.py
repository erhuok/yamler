#encoding:utf8
from flask import g, url_for
import datetime,time
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from yamler.database import Model, metadata 
from werkzeug import http_date
from wtforms import Form, TextField, validators
from sqlalchemy.sql import select, text
from yamler.utils import iphone_notify, datetimeformat

class Task(Model):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String(150))
    user_id = Column(Integer, ForeignKey('users.id'))
    to_user_id = Column(String(45), default=0)
    submit_user_id = Column(String(45), default=0)
    status = Column(Integer, default = 0)
    board_id = Column(Integer, default = 0)
    note = Column(String(200),default='')
    description = Column(String(500),default='')
    priority = Column(Integer, default=1)
    end_time = Column(DateTime,default = '') 
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
                    

class TaskComment(Model):
    __tablename__ = 'task_comments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    task_id = Column(Integer)
    content = Column(String(200))  
    created_at = Column(DateTime, default=datetime.datetime.now()) 
    updated_at = Column(DateTime,default=datetime.datetime.now()) 

    def __init__(self, user_id, task_id, content):
        self.user_id = user_id
        self.task_id = task_id
        self.content = content

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
        iphone_notify(share_user_id, type='share', title=title, realname=realname) 
        
    def update(self, share_user_id, old_user_id, task_id, own_id=None, title=None, realname=None):
        own_id = own_id if own_id else g.user.id
        insert_ids = share_user_id.difference(old_user_id)
        if insert_ids:
            g.db.execute(text("UPDATE tasks SET unread=:unread WHERE id=:id"), id=task_id) 
            for user_id in insert_ids:
                if int(user_id) > 0:
                    g.db.execute(text("INSERT INTO task_share SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=own_id, unread=1, created_at=datetime.datetime.now() )        
            iphone_notify(insert_ids, type='share', title=title, realname=realname)

        delete_ids = old_user_id.difference(share_user_id)
        if delete_ids:
            for user_id in delete_ids:
                g.db.execute(text("DELETE FROM `task_share` WHERE user_id=:user_id AND task_id=:task_id"), task_id=task_id, user_id=user_id)

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
                    g.db.execute(text("INSERT INTO task_submit SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=g.user.id, unread=1, created_at=datetime.datetime.now() )        
        iphone_notify(share_user_id, type='submit', title=title, realname=realname)

    def update(self, share_user_id, old_user_id, task_id, own_id=None, title=None, realname=None):
        own_id = own_id if own_id else g.user.id
        insert_ids = share_user_id.difference(old_user_id)
        if insert_ids:
            g.db.execute(text("UPDATE tasks SET unread=:unread WHERE id=:id"), id=task_id) 
            for user_id in insert_ids:
                if int(user_id) > 0:
                    g.db.execute(text("INSERT INTO task_submit SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=own_id, unread=1, created_at=datetime.datetime.now() )        
            iphone_notify(insert_ids, type='submit', title=title, realname=realname)
        
        delete_ids = old_user_id.difference(share_user_id)
        if delete_ids:
            for user_id in delete_ids:
                if user_id > 0:
                    g.db.execute(text("DELETE FROM `task_submit` WHERE user_id=:user_id AND task_id=:task_id"), task_id=task_id, user_id=user_id)

tasks = Table('tasks', metadata, autoload=True)
task_comments = Table('task_comments', metadata, autoload=True)
task_share = Table('task_share', metadata, autoload=True)
task_submit = Table('task_submit', metadata, autoload=True)

class TaskForm(Form):
    title = TextField('标题', [validators.required()])

