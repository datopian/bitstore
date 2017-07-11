import os
import logging

from flask import Flask
from flask_cors import CORS
import flask

from bitstore import make_blueprint


SERVICE_NAME = os.environ.get('DATAHUB_SERVICE_NAME', 'rawstore')

# Create application
app = Flask(__name__, static_folder=None)

# CORS support
CORS(app, supports_credentials=True)

@app.errorhandler(404)
def page_not_found(error):
    ascii_message  = '''
    '''

    info = "%s service - part of the DataHub platform" % SERVICE_NAME
    docs = "http://docs.datahub.io"

    return flask.jsonify(info=info, docs=docs), 404
# Register blueprints
app.register_blueprint(make_blueprint(),
                        url_prefix='/%s/' % SERVICE_NAME)


logging.getLogger().setLevel(logging.INFO)

if __name__=='__main__':
    app.run()
