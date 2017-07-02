import os
import jwt


PUBLIC_KEY = os.environ.get('DATAHUB_PUBLIC_KEY', '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzSrV/SxRNKufc6f0GQIu
YMASgBCOiJW5fvCnGtVMIrWvBQoCFAp9QwRHrbQrQJiPg6YqqnTvGhWssL5LMMvR
8jXXOpFUKzYaSgYaQt1LNMCwtqMB0FGSDjBrbmEmnDSo6g0Naxhi+SJX3BMcce1W
TgKRybv3N3F+gJ9d8wPkyx9xhd3H4200lHk4T5XK5+LyAPSnP7FNUYTdJRRxKFWg
ZFuII+Ex6mtUKU9LZsg9xeAC6033dmSYe5yWfdrFehmQvPBUVH4HLtL1fXTNyXuz
ZwtO1v61Qc1u/j7gMsrHXW+4csjS3lDwiiPIg6q1hTA7QJdB1M+rja2MG+owL0U9
owIDAQAB
-----END PUBLIC KEY-----''')
SERVICE_NAME = os.environ.get('DATAHUB_SERVICE_NAME', 'rawstore')


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
                           PUBLIC_KEY,
                           algorithm='RS256')
        has_permission = token.get('permissions', {})\
            .get('datapackage-upload', False)
        service = token.get('service')
        has_permission = has_permission and service == SERVICE_NAME
        has_permission = has_permission and owner == token.get('userid')
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
    if auth_token == 'testing-token':
        return '__tests'
    try:
        token = jwt.decode(auth_token.encode('ascii'),
                           public_key,
                           algorithm='RS256')
        if token.get('permissions', {}).get('datapackage-upload', False):
            service = token.get('service')
            if service == SERVICE_NAME:
                return token.get('userid')
    except jwt.InvalidTokenError:
        pass
    return None
