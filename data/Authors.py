import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Authors(SqlAlchemyBase):
    __tablename__ = 'authors'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    street_art_authors = orm.relationship('StreetArtAuthors', back_populates='authors')

