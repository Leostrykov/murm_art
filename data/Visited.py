import sqlalchemy
from sqlalchemy import orm
from db_session import SqlAlchemyBase


class Visited(SqlAlchemyBase):
    __tablename__ = 'visited'

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    art_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('street_atr.id'))