# encoding:utf8

from flask import Blueprint,request,render_template,session,flash,redirect,url_for,jsonify, g
from yamler.database import db_session 
from yamler.models.companies import Company,CompanyForm 
from yamler.models.users import users, UserInvite
from sqlalchemy.sql import select, text

mod = Blueprint('company',__name__,url_prefix='/company')

@mod.route('/create',methods=['GET','POST'])
def create():
    form = CompanyForm(request.form)
    if request.method=='POST' and g.user.id and form.validate():
        company = Company(user_id=g.user.id,
                          name=form.name.data,
                          scale=form.scale.data,
                          contact_name=form.contact_name.data,
                          telephone=form.telephone.data,
                          website=form.website.data,
                          address=form.address.data,
                          postcode=form.postcode.data,
                        )
        db_session.add(company)
        db_session.commit()
        if company.id:
            g.db.execute(users.update().values({users.c.company_id: company.id}).where(users.c.id==g.user.id))
            return redirect(url_for('home.account'))
    return render_template('company/create.html',form=form)


@mod.route('/get')
def get():
    if g.company.id: 
        rows = g.db.execute(text("SELECT id, realname FROM users WHERE company_id=:company_id AND is_active=:is_active AND id!=:id "), company_id=g.company.id, is_active=1, id=g.user.id).fetchall()
    else:
        rows = UserInvite().getbyid(user_id=g.user.id)
    data = []
    name = []
    for row in rows:
        data.append({'value': row['realname'], 'id': row['id']})
        name.append(row['realname'])
    return jsonify(data=data, name=name)
