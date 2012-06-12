# encoding:utf8

from flask import Blueprint,request,render_template,session,flash,redirect,url_for,jsonify, g, make_response 
from yamler.models.users import User,RegistrationForm,LoginForm, users
from yamler.database import db_session
from yamler.utils import request_wants_json, required_login, allowed_images
from datetime import date
from yamler import app
from werkzeug import secure_filename
import os
import Image

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
            #session['group_id'] = result.group_id
            #session['company_id'] = result.company_id
            return redirect(url_for(url))
    return render_template('user/login.html',form=form)

@mod.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method=='POST' and form.validate():
        user=User(form.username.data, 
                  form.password.data, 
                  is_active=1,
                  realname = request.form['realname'] if request.form.has_key('realname')   else '',
                  company_id = request.args.get('company_id','0') 
                 )
        result = User.query.filter_by(username=user.username).first()
        if result:
            return redirect(url_for('user.register'))
        db_session.add(user)
        db_session.commit()
        session['user_id']=user.id 
        flash('Thanks for registering')
        return redirect(url_for('home.myfeed'))
    return render_template('user/register.html', form=form)

@mod.route('/active', methods=['GET', 'POST'])
def active():
    return render_template('user/active.html')

@mod.route('/avatar', methods=['GET', 'POST'])
@required_login
def avatar():
    if request.method == 'POST':
        file = request.files['avatar']
        if file and allowed_images(file.filename):
            filename = secure_filename(file.filename)
            today = date.today().strftime('%Y-%m-%d')
            filename = today + '/' + str(g.user.id) + '__' + filename
            if not os.path.isdir(app.config['UPLOAD_FOLDER'] + today):
                os.makedirs(app.config['UPLOAD_FOLDER'] + today) 
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                g.db.execute(users.update().where(users.c.id==g.user.id).values(avatar=filename))
                if g.user.avatar: 
                    old_file = os.path.join(app.config['UPLOAD_FOLDER'], g.user.avatar)
                    if os.path.isfile(old_file):
                        os.unlink(old_file)
                g.user.avatar = filename
    return render_template('user/avatar.html',user=g.user)

@mod.route('/get_avatar_url', methods=['GET'])
def get_avatar_url():
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
