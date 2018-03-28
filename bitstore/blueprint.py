import json
import os

from flask import Blueprint, request, Response

from auth.lib import Verifyer
from filemanager.models import FileManager
from . import controllers

db_connection_string = os.environ.get('DATABASE_URL')
auth_server = os.environ.get('AUTH_SERVER')


def make_blueprint():
    """Create blueprint.
    """

    verifyer = Verifyer(auth_endpoint=f'http://{auth_server}/auth/public-key')

    # Create FileManager tables if not exists
    file_manager = FileManager(db_connection_string)
    file_manager.init_db()

    # Create instance
    blueprint = Blueprint('bitstore', 'bitstore')

    # Controller proxies
    def authorize():
        auth_token = request.headers.get('auth-token') or request.values.get('jwt')
        try:
            req_payload = json.loads(request.data.decode())
            return controllers.authorize(auth_token, req_payload, verifyer, file_manager)
        except (json.JSONDecodeError, ValueError) as e:
            return Response(str(e), status=400)

    def info():
        auth_token = request.headers.get('Auth-Token')
        if auth_token is None:
            auth_token = request.values.get('jwt')
        return controllers.info(auth_token, verifyer)

    def presign():
        auth_token = request.headers.get('Auth-Token') or request.values.get('jwt')
        url = request.values.get('url')
        ownerid = request.values.get('ownerid')
        return controllers.presign(auth_token, url, verifyer, ownerid)

    # Register routes
    blueprint.add_url_rule(
            'info', 'info', info, methods=['GET'])
    blueprint.add_url_rule(
            'authorize', 'authorize', authorize, methods=['POST'])
    blueprint.add_url_rule(
            'presign', 'presign', presign, methods=['GET'])
    blueprint.add_url_rule(
            '/', 'authorize', authorize, methods=['POST'])

    # Return blueprint
    return blueprint
