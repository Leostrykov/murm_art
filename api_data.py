import flask
from flask import request, jsonify
from flask_cors import CORS
from data import db_session
from data.StreetArt import StreetArt


app = flask.Flask(__name__)
CORS(app)
blueprint = flask.Blueprint(
    'street_art_data',
    __name__,
)

db_session.global_init('data_base.sqlite')


@blueprint.route('/api/arts_data', methods=['GET'])
def get_data():
    db_session.global_init('data_base.sqlite')
    db_sess = db_session.create_session()
    arts = [{'id': i.id, 'longitude': i.longitude, 'latitude': i.latitude} for i in db_sess.query(StreetArt).all()]
    return jsonify(arts)


if __name__ == '__main__':
    app.register_blueprint(blueprint)
    app.run(host='0.0.0.0', port='5000', ssl_context=('cert.pem', 'key.pem'))
