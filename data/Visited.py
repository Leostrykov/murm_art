import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Visited(SqlAlchemyBase):
    __tablename__ = 'visited'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    art_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('street_art.id'))

    user = orm.relationship('User', back_populates='visited')
