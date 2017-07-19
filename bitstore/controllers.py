import json
import os
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

import boto3
from botocore.client import Config
from flask import request, Response

from . import services

config = {}
for key, value in os.environ.items():
    config[key.upper()] = value


def get_s3_client():
    s3 = boto3.client('s3',
                      # region_name='us-east-1',
                      aws_access_key_id=config['STORAGE_ACCESS_KEY_ID'],
                      config=Config(signature_version='s3v4'),
                      aws_secret_access_key=config['STORAGE_SECRET_ACCESS_KEY']
                      )
    return s3


def authorize(auth_token, req_payload):
    """Authorize a client for the file uploading.
    """
    s3 = get_s3_client()
    try:
        # Get request payload
        owner = req_payload.get('metadata', {}).get('owner')
        dataset_name = req_payload.get('metadata', {}).get('dataset')
        # Verify client, deny access if not verified
        if owner is None:
            return Response(status=400)
        if not services.verify(auth_token, owner):
            return Response(status=401)

        # Make response payload
        res_payload = {'filedata': {}}
        for path, file in req_payload['filedata'].items():
            format_params = dict(file)
            format_params.update({
                'owner': owner,
                'dataset': dataset_name,
                'path': path
            })
            try:
                s3path = config['STORAGE_PATH_PATTERN'].format(**format_params)
            except KeyError as e:
                msg = ('STORAGE_PATH_PATTERN contains variable not found in file info: %s' % e)
                raise Exception(msg)

            s3headers = {
                'acl': 'public-read',
                'Content-MD5': file['md5'],
                'Content-Type': file.get('type', 'text/plain')
            }

            conditions = [
                    {"acl": "public-read"},
                    {"Content-Type": s3headers['Content-Type']},
                    {"Content-MD5": s3headers['Content-MD5']}
                ]

            post = s3.generate_presigned_post(
                    Bucket=config['STORAGE_BUCKET_NAME'],
                    Key=s3path,
                    Fields=s3headers,
                    Conditions=conditions
                    )

            filedata = {
                'upload_url': post['url'],
                'upload_query': post['fields']
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
            for host, path in [(config['STORAGE_BUCKET_NAME'], '')]:
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
