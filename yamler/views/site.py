#-*- encoding:utf-8 -*-
from flask import Blueprint, request, render_template, redirect, url_for, g, redirect
from yamler.utils import iphone_notify

mod = Blueprint('site',__name__)

@mod.route('/')
def index():
    return redirect(url_for('user.login'))
    return render_template('site/index.html')

@mod.route('/i/<string:key>')
def invite(key):
    return redirect(url_for('user.register', key=key))

@mod.route('/test/iphone')
def test_iphone():
    iphone_notify([1,2,4], 'share')
    return 'ok'
