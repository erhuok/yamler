#-*- encoding:utf-8 -*-
from sqlalchemy import Column, Integer, DateTime, String, Table
from yamler.database import Model, metadata, db_session
from datetime import datetime, date

class Board(Model):
    __tablename__ = 'boards'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    to_user_id = Column(String(200))
    year = Column(Integer)
    week = Column(Integer)
    type = Column(Integer)
    is_del = Column(Integer)
    title = Column(String(45))
    created_at = Column(DateTime, default=datetime.now())

    def __ini__(self, title=None):
        self.title = title

    def __repr__(self):
        return "<Board Title %s>" % (self.title)
          
boards = Table('boards', metadata, autoload=True)
