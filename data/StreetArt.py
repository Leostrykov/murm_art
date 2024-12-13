import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class StreetArt(SqlAlchemyBase):
    __tablename__ = 'street_art'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True)
    longitude = sqlalchemy.Column(sqlalchemy.Float)
    latitude = sqlalchemy.Column(sqlalchemy.Float)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    district_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('districts.id'))
    address = sqlalchemy.Column(sqlalchemy.String)
    photo = sqlalchemy.Column(sqlalchemy.String)

    district = orm.relationship('Districts', back_populates='street_art')
    street_art_authors = orm.relationship('StreetArtAuthors', back_populates='street_art')
