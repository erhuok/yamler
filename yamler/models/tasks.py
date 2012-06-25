#encoding:utf8
from flask import g
import datetime,time
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from yamler.database import Model, metadata 
from werkzeug import http_date
from wtforms import Form, TextField, validators
from sqlalchemy.sql import select, text

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

    def __init__(self, title, user_id, note=None, priority=None, end_time=None, to_user_id=None, created_at=None, submit_user_id=None):
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
    
    def insert(self, task_id, share_user_id):
        if not task_id or not share_user_id:
            return False
        for user_id in share_user_id:
            res = g.db.execute(text("SELECT id FROM task_share WHERE user_id=:user_id AND task_id=:task_id"), user_id=user_id, task_id=task_id).fetchone()
            if res is None:
                g.db.execute(text("INSERT INTO task_share SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=g.user.id, unread=1, created_at=datetime.datetime.now() )        
    
    def update(self, share_user_id, old_user_id, task_id):
        insert_ids = share_user_id.difference(old_user_id)
        if insert_ids:
            for user_id in insert_ids:
                if int(user_id) > 0:
                    g.db.execute(text("INSERT INTO task_share SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=g.user.id, unread=1, created_at=datetime.datetime.now() )        

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
    
    def insert(self, task_id, share_user_id):
        if not task_id or not share_user_id:
            return False
        for user_id in share_user_id:
            if user_id > 0:
                res = g.db.execute(text("SELECT id FROM task_submit WHERE user_id=:user_id AND task_id=:task_id"), user_id=user_id, task_id=task_id).fetchone()
                if res is None:
                    g.db.execute(text("INSERT INTO task_submit SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=g.user.id, unread=1, created_at=datetime.datetime.now() )        
    
    def update(self, share_user_id, old_user_id, task_id):
        insert_ids = share_user_id.difference(old_user_id)
        if insert_ids:
            for user_id in insert_ids:
                if int(user_id) > 0:
                    g.db.execute(text("INSERT INTO task_submit SET user_id=:user_id, own_id=:own_id, task_id=:task_id, unread=:unread, created_at=:created_at"), task_id=task_id, user_id=user_id, own_id=g.user.id, unread=1, created_at=datetime.datetime.now() )        
        
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

