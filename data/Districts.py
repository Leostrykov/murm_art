import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Districts(SqlAlchemyBase):
    __tablename__ = 'districts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    street_art = orm.relationship('StreetArt', back_populates='district')
