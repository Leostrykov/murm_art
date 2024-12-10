import sqlalchemy
from sqlalchemy import orm
from db_session import SqlAlchemyBase


class AtreetArtAuthors(SqlAlchemyBase):
    __tablename__ = 'street_art_authors'

    art_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("street_art.id"))
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("authors.id"))
