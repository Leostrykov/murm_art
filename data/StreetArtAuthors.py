import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class StreetArtAuthors(SqlAlchemyBase):
    __tablename__ = 'street_art_authors'

    art_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("street_art.id"), primary_key=True)
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("authors.id"), primary_key=True)

    street_art = orm.relationship('StreetArt', back_populates='street_art_authors')
    authors = orm.relationship('Authors', back_populates='street_art_authors')
