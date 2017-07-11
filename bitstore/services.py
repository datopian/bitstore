import os
import requests
import jwt
import logging

_public_key = None


def public_key():
    global _public_key
    if _public_key is None:
        auth_server = os.environ.get('AUTH_SERVER')
        _public_key = requests.get(f'{auth_server}/auth/public-key').content
    return _public_key


def verify(auth_token, owner):
    """Verify Auth Token.
    :param auth_token: Authentication token to verify
    :param owner: dataset owner
    """
    if not auth_token:
        return False
    if auth_token == 'testing-token' and owner == '__tests':
        return True
    try:
        token = jwt.decode(auth_token.encode('ascii'),
                           public_key(),
                           algorithm='RS256')
        has_permission = owner == token.get('userid')
        # TODO: Check service in the future
        # service = token.get('service')
        # has_permission = has_permission and service == 'world'
        # has_permission = has_permission and owner == token.get('userid')
        return has_permission
    except jwt.InvalidTokenError:
        return False


def get_user_id(auth_token):
    """Returns the user id from an Auth Token.
    :param auth_token: Authentication token to verify
    :returns user id
    """
    if not auth_token:
        return None
    try:
        token = jwt.decode(auth_token.encode('ascii'),
                           public_key(),
                           algorithm='RS256')
        # TODO: Check service in the future
        # service = token.get('service')
        # if service == 'world':
        return token.get('userid')
    except jwt.InvalidTokenError:
        pass
    return None
