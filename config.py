import os

_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True 

SECRET_KEY = '232323sljf209302nadnoasfo2031012'

DATABASE_URI = 'mysql+mysqldb://root:data@localhost:3306/yamler_development?charset=utf8'
DATABASE_CONNECT_OPTIONS = {'pool_recycle':7200}

#ADMINS = frozenset(['http://admin.yamler.com/']
UPLOAD_FOLDER =_basedir + '/yamler/static/uploads/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

del os
