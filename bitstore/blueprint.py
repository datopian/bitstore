import json

from flask import Blueprint, request, Response
from . import controllers


def make_blueprint():
    """Create blueprint.
    """

    # Create instance
    blueprint = Blueprint('bitstore', 'bitstore')

    # Controller proxies
    def authorize():
        auth_token = request.headers.get('auth-token') or request.values.get('jwt')
        try:
            req_payload = json.loads(request.data.decode())
            return controllers.authorize(auth_token, req_payload)
        except (json.JSONDecodeError, ValueError) as e:
            return Response(str(e), status=400)

    def info():
        auth_token = request.headers.get('Auth-Token')
        if auth_token is None:
            auth_token = request.values.get('jwt')
        return controllers.info(auth_token)

    def presign():
        auth_token = request.headers.get('Auth-Token') or request.values.get('jwt')
        url = request.values.get('url')
        ownerid = request.values.get('ownerid')
        controllers.presign(auth_token, url, ownerid)

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
