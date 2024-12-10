import sqlalchemy
from sqlalchemy import orm
from db_session import SqlAlchemyBase


class StreetArt(SqlAlchemyBase):
    __tablename__ = 'street_art'

    id = sqlalchemy.Column(sqlalchemy.Integer, primery_key=true)
    name = sqlalchemy.Column(sqlalchemy.String)
    longitude = sqlalchemy.Column(sqlalchemy.Float)
    latitude = sqlalchemy.Column(sqlalchemy.Float)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    district = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('districts.id'))
    address = sqlalchemy.Column(sqlalchemy.String)
    photo = sqlalchemy.Column(sqlalchemy.BLOB)

    street_art_authors = orm.relationship('StreetArtAuthors', back_populates='street_art')
    visited = orm.relationship('Visited', back_populates='street_art')
