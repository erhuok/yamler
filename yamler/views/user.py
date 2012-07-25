# encoding:utf8

from flask import Blueprint,request,render_template,session,flash,redirect,url_for,jsonify, g, make_response 
from yamler.models.users import User,RegistrationForm,LoginForm, users, UserInvite
from yamler.database import db_session
from yamler.utils import request_wants_json, required_login, allowed_images
from datetime import date, datetime
from yamler import app
from werkzeug import secure_filename
import os
import Image
import base64
from sqlalchemy.sql import select, text

mod = Blueprint('user',__name__,url_prefix='/user')

@mod.route('/')
def index():
    print request.form
    return 'ok'

@mod.route('/login',methods=['GET','POST'])
def login():
    url = request.args.get('next') if request.args.get('next') else 'home.account'
    if g.user:
        return redirect(url_for(url))
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User(form.username.data,form.password.data)
        result = User.query.filter_by(username = user.username).filter_by(password = user.password).first()
        if result:
            session['user_id']=result.id
            g.db.execute(text("UPDATE users SET last_login_time=:last_login_time WHERE id=:id"), last_login_time=datetime.now(), id=result.id) 
            #session['group_id'] = result.group_id
            #session['company_id'] = result.company_id
            return redirect(url_for(url))
    return render_template('user/login.html',form=form)

@mod.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    key = request.args.get('key')
    if request.method=='POST' and form.validate():
        user=User(form.username.data, 
                  form.password.data, 
                  is_active=1,
                  realname = request.form['realname'] if request.form.has_key('realname')   else '',
                  #company_id = company_id,
                  telephone = request.form['telephone'],
                 )
        result = User.query.filter_by(username=user.username).first()
        if result:
            return redirect(url_for('user.register', key=key))
      
        db_session.add(user)
        db_session.commit()
        
        session['user_id'] = user.id 

        if request.args.has_key('key'):
            invite_user_id = base64.decodestring(key)
            invite_user = g.db.execute(text("SELECT id, company_id FROM users WHERE id=:id"), id=invite_user_id).first()
            if invite_user and invite_user.company_id:
                g.db.execute(text("UPDATE users SET company_id=:company_id WHERE id=:id"), id=user.id, company_id=invite_user.company_id)

            #row = g.db.execute(text("SELECT id, level, user_id, invite_user_id FROM user_invites WHERE user_id=:user_id"), user_id=invite_user_id).first() 
            #if row:
            #    level = int(row.level) + 1
            g.db.execute(text("INSERT INTO user_invites SET user_id=:user_id, invite_user_id=:invite_user_id, created_at=:created_at"), user_id=user.id, invite_user_id=invite_user_id, created_at=datetime.now()) 
            #联系人列表
            contact = g.db.execute(text("SELECT id, user_id, contact_user_id FROM user_contacts WHERE user_id=:user_id"), user_id=invite_user_id).first()
            if contact:
                old_contact_user_id = contact.contact_user_id.split(',')
                contact_user_id = list(set(old_contact_user_id) | set([str(user.id)])) 
                g.db.execute(text("UPDATE user_contacts SET contact_user_id=:contact_user_id WHERE user_id=:user_id"), contact_user_id=','.join(contact_user_id), user_id=invite_user_id) 
            else:
                g.db.execute(text("INSERT INTO user_contacts SET contact_user_id=:contact_user_id, user_id=:user_id, created_at=:created_at"), user_id=invite_user_id, contact_user_id=user.id,created_at=datetime.now())

            return redirect(url_for('home.account'))
    return render_template('user/register.html', form=form)

@mod.route('/active', methods=['GET', 'POST'])
def active():
    return render_template('user/active.html')

@mod.route('/logout')
def logout():
    if 'user_id' in session:
        del session['user_id']
    return redirect(request.referrer or url_for(''))
    
@mod.route('/invite')
def invite():
    url = 'http://' + request.host + '/i/' + base64.encodestring(str(g.user.id))  
    return render_template('user/invite.html', url=url)

@mod.route('/setting', methods=['GET', 'POST'])
@required_login
def setting():
    if request.method == 'POST':
        file = request.files['avatar']
        filename = g.user.avatar
        if file and allowed_images(file.filename):
            filename = secure_filename(file.filename)
            today = date.today().strftime('%Y-%m-%d')
            filename = today + '/' + str(g.user.id) + '__' + filename
            if not os.path.isdir(app.config['UPLOAD_FOLDER'] + 'original/'+today):
                os.makedirs(app.config['UPLOAD_FOLDER']+'original/' + today) 
            if not os.path.isdir(app.config['UPLOAD_FOLDER'] + 'small/'+today):
                os.makedirs(app.config['UPLOAD_FOLDER'] + 'small/'+today) 
            if not os.path.isdir(app.config['UPLOAD_FOLDER'] + 'big/'+today):
                os.makedirs(app.config['UPLOAD_FOLDER'] + 'big/'+today) 

            file.save(os.path.join(app.config['UPLOAD_FOLDER']+'original/', filename))
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER']+'original/', filename)):
                print 'ok'
                im = Image.open(os.path.join(app.config['UPLOAD_FOLDER']+'original/', filename))
                im.thumbnail((30, 30), Image.ANTIALIAS)
                im.save(os.path.join(app.config['UPLOAD_FOLDER'],'small/'+filename))
                print im

                im = Image.open(os.path.join(app.config['UPLOAD_FOLDER']+'original/', filename))
                im.thumbnail((120, 120), Image.ANTIALIAS)
                im.save(os.path.join(app.config['UPLOAD_FOLDER'],'big/'+filename))

                if g.user.avatar: 
                    original_file = os.path.join(app.config['UPLOAD_FOLDER']+'original/', g.user.avatar)
                    big_file = os.path.join(app.config['UPLOAD_FOLDER']+'big/', g.user.avatar)
                    small_file = os.path.join(app.config['UPLOAD_FOLDER']+'small/', g.user.avatar)
                    if os.path.isfile(original_file):
                        os.unlink(original_file)
                    if os.path.isfile(big_file):
                        os.unlink(big_file)
                    if os.path.isfile(small_file):
                        os.unlink(small_file)
                g.user.avatar = filename
        g.db.execute(users.update().where(users.c.id==g.user.id).values(avatar=filename, realname=request.form['realname'], telephone=request.form['telephone']))
        redirect(url_for("user.setting"))
    return render_template('user/setting.html',user=g.user)

@mod.route('/get_avatar_url', methods=['GET'])
def get_avatar_url():
    return ''
    key = request.args.get('key','') 
    if key:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], key)
        if os.path.isfile(filepath):
            im = Image.open(filepath)
            response = make_response(im)
            #response.headers['Content-Type'] = 'image/jpeg'
            #response.headers['Content-Disposition'] = 'attachment; filename=myfile.jpg'
            return response
    #filename = 'upload/' + key
    #return url_for("static", filename=filename)
