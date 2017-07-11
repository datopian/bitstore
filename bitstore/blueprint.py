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
        except json.JSONDecodeError:
            return Response(status=400)

    def info():
        auth_token = request.headers.get('Auth-Token')
        if auth_token is None:
            auth_token = request.values.get('jwt')
        return controllers.info(auth_token)

    # Register routes
    blueprint.add_url_rule(
            'info', 'info', info, methods=['GET'])
    blueprint.add_url_rule(
            'authorize', 'authorize', authorize, methods=['POST'])
    blueprint.add_url_rule(
            '/', 'authorize', authorize, methods=['POST'])

    # Return blueprint
    return blueprint
