#-*- encoding:utf-8 -*-
from flask import Blueprint, request, render_template, g, jsonify, redirect, url_for, flash, abort
from yamler.models.boards import Board, boards
from datetime import datetime, date
from sqlalchemy.sql import select, text
from yamler.utils import required_login

mod =Blueprint('board', __name__, url_prefix='/board')

@mod.route('/view/<int:id>', methods=['GET', 'POST'])
@required_login
def view(id):
    board_row = g.db.execute(text("SELECT id, user_id, title, year, week, is_del, to_user_id FROM boards WHERE id=:id "), id=id).fetchone()
    if board_row is None or board_row.is_del == 1 or board_row.user_id != g.user.id:
        abort(404)
    sql = text("SELECT id, user_id, title, status, comment_count FROM tasks WHERE board_id=:board_id AND user_id=:user_id AND is_del='0' ORDER BY id DESC") 
    rows = g.db.execute(sql, board_id=id, user_id=g.user.id).fetchall()
    todo = []
    doing = [] 
    done = [] 
    for row in rows:
        status = int(row.status)
        if status == 0:
            todo.append(row)
        elif status == 1:
            done.append(row)
        elif status == 2:
            doing.append(row)
    if g.company and g.company.id:
        company_rows = g.db.execute(text("SELECT id, realname FROM users WHERE company_id=:company_id"), company_id=g.company.id).fetchall()
    return render_template('board/view.html', board_id=id, todo=todo, doing=doing, done=done, board_row=board_row, company_rows=company_rows)

@mod.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST' and request.form.has_key('title') and request.form['title']:
        res = g.db.execute(boards.insert().values(title=request.form['title'], 
                                            user_id=g.user.id, 
                                            week=int(date.today().strftime('%W')),
                                            year=int(date.today().strftime('%Y')),
                                            type=2,
                                            created_at=datetime.now()
                                           )) 
        if res.inserted_primary_key: 
            return jsonify(error=0, id=res.inserted_primary_key, title=request.form['title'])

    return jsonify(error=1, msg="没有提交数据")

@mod.route('/update', methods=['GET', 'POST'])
def update():
    id = request.args.get('id',0)
    if id:
        row = g.db.execute(text("SELECT id, title FROM boards WHERE id=:id"),id=id).fetchone()
        if request.method == 'POST' and row:
            g.db.execute(boards.update().where(boards.c.id==id).values(title=request.form['title'])) 
            flash('修改成功')
        return render_template('board/update.html', row=row)

@mod.route('/update_share', methods=['GET', 'POST'])
def update_share():
    id = request.args.get('id',0)
    sharename = request.form.getlist('sharename')
    if id and sharename:
        row = g.db.execute(text("SELECT id, title FROM boards WHERE id=:id"),id=id).fetchone()
        if request.method == 'POST' and row:
            to_user_id = ','.join(sharename)
            g.db.execute(boards.update().where(boards.c.id==id).values(to_user_id=to_user_id)) 
            return jsonify(error=0)
    return jsonify(error=1)


@mod.route('/delete', methods=['POST'])
def delete():
    if request.method == 'POST' and request.form.has_key('id') and request.form['id']:
        g.db.execute(boards.update().where(boards.c.id==request.form['id']).values(is_del=1))
        return jsonify(error=0)
    return jsonify(error=1)

@mod.route('/get/<int:id>')
def get(id):
    if id:
        row = g.db.execute(text("SELECT id, user_id, title, created_at FROM boards WHERE id=:id"),id=id).fetchone()
        data = dict(zip(row.keys(), row))
        data['created_at'] = data['created_at'].strftime("%Y-%m-%d %H:%M")
        return jsonify(error=0, data=data)
