import json
import os

import boto
from boto.s3.connection import OrdinaryCallingFormat
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs
from flask import request, Response
from . import services

config = {}
for key, value in os.environ.items():
    config[key.upper()] = value


class S3Connection(object):

    def __init__(self):
        fake_s3 = '.' not in config.OS_S3_HOSTNAME
        self.__connection = boto.connect_s3(
                config.STORAGE_ACCESS_KEY_ID,
                config.STORAGE_SECRET_ACCESS_KEY,
                host=config.STORAGE_HOSTNAME,
                calling_format=OrdinaryCallingFormat(),
                is_secure=not fake_s3)
        if fake_s3:
            bucket_name = config.STORAGE_BUCKET_NAME
            self.__connection.create_bucket(bucket_name)
        self.bucket = self.__connection.get_bucket(
                config.OS_STORAGE_BUCKET_NAME)


def authorize(connection, auth_token, req_payload):
    """Authorize a client for the file uploading.
    """
    # Verify client, deny access if not verified

    try:
        # Get request payload
        owner = req_payload.get('metadata', {}).get('owner')
        dataset_name = req_payload.get('metadata', {}).get('name')
        if owner is None or dataset_name is None:
            return Response(status=400)
        if not services.verify(auth_token, owner):
            return Response(status=401)

        # Make response payload
        res_payload = {'filedata': {}}
        for path, file in req_payload['filedata'].items():
            s3path = '{0}/{1}/{2}'.format(owner, dataset_name, path)
            s3headers = {
                'Content-Length': file['length'],
                'Content-MD5': file['md5'],
            }
            if 'type' in file:
                s3headers['Content-Type'] = file['type']
            s3key = connection.bucket.new_key(s3path)
            s3url = s3key.generate_url(
                    config.ACCESS_KEY_EXPIRES_IN, 'PUT',
                    headers=s3headers)
            parsed = urlparse(s3url)
            upload_url = '{0}://{1}{2}'.format(
                    parsed.scheme, parsed.netloc, parsed.path)
            upload_query = parse_qs(parsed.query)
            filedata = {
                'md5': file['md5'],
                'name': file['name'],
                'length': file['length'],
                'upload_url': upload_url,
                'upload_query': upload_query,
            }
            if 'type' in file:
                filedata['type'] = file['type']
            res_payload['filedata'][path] = filedata

        # Return response payload
        return json.dumps(res_payload)

    except Exception as exception:

        raise
        # TODO: use logger
        # Log bad request exception
        print('Bad request: {0}'.format(exception))

        # Return request is bad
        return Response(status=400)


def info(auth_token):
    """Authorize a client for the file uploading.
    :param auth_token: authentication token to test
    """
    # Verify client, deny access if not verified

    try:
        # Get request payload
        userid = services.get_user_id(auth_token)
        if userid is None:
            return Response(status=401)

        # Make response payload
        urls = []
        for scheme, port in [('http', '80'), ('https', '443')]:
            for host, path in [(config.OS_S3_HOSTNAME,
                                config.OS_STORAGE_BUCKET_NAME),
                               (config.OS_STORAGE_BUCKET_NAME, '')]:
                urls.extend([
                    '%s://%s:%s/%s' % (scheme, host, port, path),
                    '%s://%s/%s' % (scheme, host, path),
                    ])
        urls = [os.path.join(url, userid) for url in urls]
        response_payload = {
            'prefixes': urls
        }

        # Return response payload
        return json.dumps(response_payload)

    except Exception as exception:

        raise
        # TODO: use logger
        # Log bad request exception
        print('Bad request: {0}'.format(exception))

        # Return request is bad
        return Response(status=400)
