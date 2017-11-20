import base64
import codecs
import json
import logging
import os
import requests
import urllib


try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

import boto3
import botocore
from boto3.exceptions import Boto3Error
from botocore.client import Config
from flask import request, Response

from . import services

config = {}
for key, value in os.environ.items():
    config[key.upper()] = value


def get_s3_client():
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")
    s3_client = boto3.client('s3',
                             # region_name='us-east-1',
                             aws_access_key_id=config['STORAGE_ACCESS_KEY_ID'],
                             config=Config(signature_version='s3v4'),
                             aws_secret_access_key=config['STORAGE_SECRET_ACCESS_KEY'],
                             endpoint_url=endpoint_url
                             )
    if endpoint_url:
        try:
            s3 = boto3.resource('s3',
                                 aws_access_key_id=config['STORAGE_ACCESS_KEY_ID'],
                                 config=Config(signature_version='s3v4'),
                                 aws_secret_access_key=config['STORAGE_SECRET_ACCESS_KEY'],
                                 endpoint_url=endpoint_url)
            s3.create_bucket(Bucket=config['STORAGE_BUCKET_NAME'])
            bucket = s3.Bucket(config['STORAGE_BUCKET_NAME'])
            bucket.Acl().put(ACL='public-read')
        except: # noqa
            logging.exception('Failed to create the bucket')
            pass
    return s3_client


def format_s3_path(file, owner, dataset_name, path):
    format_params = dict(file)
    format_params.update({
        'owner': owner,
        'dataset': dataset_name,
        'path': path,
        'basename': os.path.basename(path),
        'dirname': os.path.dirname(path),
        'extension': os.path.splitext(path)[1],
    })
    if 'md5' in format_params:
        try:
            md5 = base64.b64decode(format_params['md5'])
            format_params['md5_hex'] = codecs.encode(md5, 'hex').decode('ascii')
        except Exception:
            pass

    try:
        s3path = config['STORAGE_PATH_PATTERN'].format(**format_params)
    except KeyError as e:
        msg = ('STORAGE_PATH_PATTERN contains variable not found in file info: %s' % e)
        raise ValueError(msg)

    return s3path


def authorize(auth_token, req_payload):
    """Authorize a client for the file uploading.
    """
    s3 = get_s3_client()
    try:
        # Get request payload
        metadata = req_payload.get('metadata', {})
        owner = metadata.get('owner')
        dataset_name = metadata.get('dataset')
        findability = metadata.get('findability')
        acl = 'private' if findability == 'private' else 'public-read',

        # Verify client, deny access if not verified
        if owner is None:
            return Response(status=400)
        if not services.verify(auth_token, owner):
            return Response(status=401)

        # Make response payload
        res_payload = {'filedata': {}}
        for path, file in req_payload['filedata'].items():
            s3path = format_s3_path(file, owner, dataset_name, path)

            s3headers = {
                'acl': acl,
                'Content-MD5': file['md5'],
                'Content-Type': file.get('type', 'text/plain')
            }

            conditions = [
                {'acl': acl},
                {'Content-Type': s3headers['Content-Type']},
                {'Content-MD5': s3headers['Content-MD5']}
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
        logging.exception('Bad request (authorize)')
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
        logging.exception('Bad request (info)')
        return Response(status=400)


def presign(auth_token, url, ownerid=None):
    """Generates S3 presigned URLs if necessary
    :param auth_token: authentication token from auth
    :param ownerid: ownerid for dataset
    :param url: url to check for sigend URL
    """
    s3 = get_s3_client()
    try:
        needs_signed_url = requests.head(url)
        if needs_signed_url.status_code != 403:
            return json.dumps({'url': url})
        # Verify client, deny access if not verified
        if ownerid is None:
            return Response(status=401)
        if not services.verify(auth_token, ownerid):
            return Response(status=403)
        parsed_url = urllib.parse.urlparse(url)
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip('/')

        # Make sure file belongs to user (only in case of pkgstore)
        if config['STORAGE_BUCKET_NAME'] != bucket and (ownerid not in url):
            return Response(status=403)

        signed_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=3600*24)
        return json.dumps({'url': signed_url})
    except Exception as exception:
        logging.exception('Bad request')
        return Response(status=400)
