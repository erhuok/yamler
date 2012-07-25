#encoding:utf8
from flask import g
import datetime,hashlib
from sqlalchemy import Table, Column, Integer, String, DateTime
from yamler.database import Model, metadata  
from wtforms import Form, BooleanField, TextField, PasswordField, validators, ValidationError
from sqlalchemy.sql import select, text

class User(Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(20), unique=True)
    password = Column(String(32))
    realname = Column(String(45))
    telephone = Column(String(45))
    avatar = Column(String(45), default='')
    iphone_token = Column(String(64), default='')
    company_id = Column(Integer, default=0)
    is_active = Column(Integer, default=0)
    last_login_time = Column(DateTime, default=datetime.datetime.now())
    created_at = Column(DateTime,default=datetime.datetime.now())
    updated_at = Column(DateTime,default=datetime.datetime.now())

    def __init__(self, username=None, password=None,is_active=None, realname=None, company_id=None, telephone=None, iphone_token=None):
        self.username = username
        self.is_active = is_active
        self.password = hashlib.md5(password).hexdigest() 
        self.realname = realname
        self.company_id = company_id
        self.telephone = telephone
        self.iphone_token = iphone_token

    def __repr__(self):
        return '<User %r>' % (self.username)

    def to_json(self):
        result = dict(id=self.id,
                      username=self.username,
                      password=self.password,
                      realname=self.realname,
                      is_active=self.is_active,
                      company_id=self.company_id,
                     )
        return result

    def register(self):
        pass


class UserInvite(Model):
    __tablename__ = 'user_invites'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    invite_user_id = Column(Integer)

    created_at = Column(DateTime,default=datetime.datetime.now())
    updated_at = Column(DateTime,default=datetime.datetime.now())

    def __init__(self, user_id=None, invite_user_id=None, user_name=None, invite_user_name=None):
        self.user_id = user_id
        self.invite_user_id = invite_user_id
    
    def getbyid(self, user_id):
        data_user_ids = []
        sql = "SELECT user_id, invite_user_id, level FROM user_invites WHERE user_id=:user_id"
        row = g.db.execute(text(sql), user_id=user_id).first()

        if row and int(row.level) == 0:
            row1 = g.db.execute(text("SELECT GROUP_CONCAT(user_id) AS user_id FROM user_invites WHERE invite_user_id=:invite_user_id"), invite_user_id=user_id).first()
            if row1.user_id:
                row1_user_id = row1.user_id.split(',') 
                sql = "SELECT GROUP_CONCAT(user_id) AS user_id FROM user_invites WHERE invite_user_id IN ({0})".format(','.join(row1_user_id)) 
                row2 = g.db.execute(text(sql)).first()
                row2_user_id = row2.user_id.split(',') if  row2.user_id else []
                data_user_ids = list(set(row1_user_id) | set(row2_user_id))
    
        if row and int(row.level) == 1:
            row0_user_id = [str(row.invite_user_id)] 
            sql = "SELECT GROUP_CONCAT(user_id) AS user_id FROM user_invites WHERE invite_user_id=:invite_user_id"
            row2 = g.db.execute(text(sql), invite_user_id=row.user_id).first()
            row2_user_id = row2.user_id.split(',') if row2.user_id else []
            data_user_ids = list(set(row0_user_id) | set(row2_user_id))

        if row and int(row.level) == 2:
            row1_user_id = [str(row.invite_user_id)]
            row2 = g.db.execute(text("SELECT GROUP_CONCAT(user_id) AS user_id FROM user_invites WHERE invite_user_id=:invite_user_id"), invite_user_id=row.invite_user_id).first()
            row2_user_id = row2.user_id.split(',') if row2.user_id else []
            row0 = g.db.execute(text("SELECT invite_user_id FROM user_invites WHERE user_id=:user_id"), user_id=row.invite_user_id).first()
            row0_user_id = [str(row0.invite_user_id)] if row0.invite_user_id else []
            data_user_ids = list(set(row1_user_id) | set(row2_user_id) | set(row0_user_id))

        if len(data_user_ids):
            sql = "SELECT id, realname, avatar FROM users WHERE id IN ({0})".format(','.join(data_user_ids))
            return g.db.execute(text(sql)).fetchall()

class UserNotice(Model):
    __tablename__ = 'user_notices'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    task_id = Column(Integer)
    unread = Column(Integer)
    message = Column(String(255))

    created_at = Column(DateTime,default=datetime.datetime.now())
    updated_at = Column(DateTime,default=datetime.datetime.now())

    def __init__(self, user_id=None, task_id=None, unread=None, message=None):
        self.user_id = user_id
        self.task_id = task_id
        self.unread = unread
        self.message = message
    
    def process(self, user_id, task_id, message, title):
        #通知
        sql = "INSERT INTO user_notices SET user_id=:user_id, task_id=:task_id, message=:message, created_at=:created_at, title=:title"
        g.db.execute(text(sql), user_id=user_id, task_id=task_id, created_at=datetime.datetime.now(), message=message, title=title)
            
        sql = 'INSERT INTO users_remind(user_id, total_count) VALUES(:user_id, 1) ON DUPLICATE KEY UPDATE total_count=total_count+1'
        g.db.execute(text(sql), user_id=user_id)

class UserContact(Model):
    __tablename__ = 'user_contacts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    contact_user_id = Column(String(255))

    created_at = Column(DateTime,default=datetime.datetime.now())
    updated_at = Column(DateTime,default=datetime.datetime.now())

    def __init__(self, user_id=None, contact_user_id=None):
        self.user_id = user_id
        self.contact_user_id = contact_user_id
    
    def process(self, user_id, contact_user_id):
        contact = g.db.execute(text("SELECT id, user_id, contact_user_id FROM user_contacts WHERE user_id=:user_id"), user_id=user_id).first()
        if contact:
            g.db.execute(text("UPDATE user_contacts SET contact_user_id=:contact_user_id WHERE user_id=:user_id"), contact_user_id=contact_user_id, user_id=user_id) 
        else:
            g.db.execute(text("INSERT INTO user_contacts SET contact_user_id=:contact_user_id, user_id=:user_id, created_at=:created_at"), user_id=user_id, contact_user_id=contact_user_id,created_at=datetime.datetime.now())

    def  get(self, user_id):
        user = g.db.execute(text("SELECT id, company_id FROM users WHERE id=:id"), id=user_id).first()
        contact = g.db.execute(text("SELECT user_id, contact_user_id FROM user_contacts WHERE user_id=:user_id"), user_id=user_id).first()
        contact_rows = dict()
        if contact and contact.contact_user_id:
            contact_user_id = contact.contact_user_id.split(',')
            sql = "SELECT id, realname, avatar, company_id, telephone, is_active, username FROM users WHERE is_active=:is_active AND id IN ({0})".format(','.join(contact_user_id))
            sql += " ORDER BY FIELD (`id`,{0})".format(','.join(contact_user_id))
            contact_rows = g.db.execute(text(sql), is_active=1).fetchall()
            contact_data = [dict(zip(row.keys(), row)) for row in contact_rows]  

        rows = g.db.execute(text('SELECT id, company_id, username, realname, telephone, is_active FROM users WHERE company_id=:company_id AND is_active=:is_active'), company_id=user.company_id, is_active=1).fetchall()
        data = [dict(zip(row.keys(), row)) for row in rows]  

        return (data, contact_data)

users = Table('users', metadata, autoload=True)
user_notices = Table('user_notices', metadata, autoload=True)

class RegistrationForm(Form):
    def check_email_exists(form, field):
        row = g.db.execute(text("SELECT id FROM users WHERE username=:username"), username=field.data).fetchone()   
        if row: 
            raise ValidationError('邮箱已经存在,请换一个')

    username = TextField('电子邮箱', [validators.Length(min=4, max=45),validators.required(message="必填"), validators.email(message='请输入正确的邮箱地址'), check_email_exists])
    realname = TextField('真实姓名', [validators.required(message="必填")])
    telephone = TextField('电话号码', [validators.required(message="必填")])
    password = PasswordField('登录密码', [
        validators.Required(message="必填"),
        validators.EqualTo('confirm', message='两次密码输入不一致')
    ])
    confirm = PasswordField('确认密码')
    #accept_tos = BooleanField('我同意注册协议', [validators.Required()])
    
  
class LoginForm(Form):
    username = TextField('邮箱', validators=[validators.required()])
    password = PasswordField('密码', validators=[validators.required()])
    created_at = Column(DateTime,default=datetime.datetime.now())
