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

  

class UserRemind(Model):
    __tablename__ = 'users_remind'
    id = Column(Integer, primary_key=True)
    submit_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    def __init__(self, submit_count=None, share_count=None):
        self.submit_count = submit_count
        self.share_count = share_count
    
    def update_submit(self, submit_user_id):
        if submit_user_id:
            sql = 'INSERT INTO users_remind(user_id, submit_count) VALUES(:user_id, 1) ON DUPLICATE KEY UPDATE submit_count=submit_count+1'
            for user_id in submit_user_id:
                if user_id:
                    g.db.execute(text(sql), user_id=user_id)
    
    def update_share(self, share_user_id):
        if share_user_id:
            sql = 'INSERT INTO users_remind(user_id, share_count) VALUES(:user_id, 1) ON DUPLICATE KEY UPDATE share_count=share_count+1'
            for user_id in share_user_id:
                if user_id: 
                    g.db.execute(text(sql), user_id=user_id)

users = Table('users', metadata, autoload=True)
users_remind = Table('users_remind', metadata, autoload=True)

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
