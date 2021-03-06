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

import auth
from filemanager.models import FileManager

config = {}
for key, value in os.environ.items():
    config[key.upper()] = value


def get_s3_client():
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")
    s3_client = boto3.client('s3',
                             # region_name='us-east-1',
                             aws_access_key_id=config['STORAGE_ACCESS_KEY_ID'],
                             config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
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


def authorize(auth_token, req_payload, verifyer: auth.lib.Verifyer, registry: FileManager):
    """Authorize a client for the file uploading.
    """
    s3 = get_s3_client()
    try:
        # Get request payload
        metadata = req_payload.get('metadata', {})
        owner = metadata.get('owner')
        dataset_name = metadata.get('dataset')
        findability = metadata.get('findability')
        is_private = findability == 'private'
        acl = 'private' if is_private else 'public-read'
        permissions = verifyer.extract_permissions(auth_token)

        # Verify client, deny access if not verified
        if owner is None:
            return Response(status=400)
        if not permissions or permissions.get('userid') != owner:
            return Response(status=401)

        limits = permissions.get('permissions')
        limit = limits.get(
            'max_private_storage_mb' if is_private else 'max_public_storage_mb', 0
        )
        current_storage = registry.get_total_size_for_owner(
            owner, 'private' if is_private else None
        )

        total_bytes = 0
        for file in req_payload['filedata'].values():
            total_bytes += file['length']

        if current_storage + total_bytes > limit * 1000000:
            return Response(status=403,
                response='Max %sstorage for user exceeded plan limit (%dMB)' % (
                    'private ' if is_private else '', limit))

        # Make response payload
        res_payload = {'filedata': {}}
        for path, file in req_payload['filedata'].items():
            s3path = format_s3_path(file, owner, dataset_name, path)
            bucket = config['STORAGE_BUCKET_NAME']

            objs = s3.list_objects_v2(Bucket=bucket, Prefix=s3path)
            exists = True if objs.get('KeyCount') else False

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
                    Bucket=bucket,
                    Key=s3path,
                    Fields=s3headers,
                    Conditions=conditions
                    )

            filedata = {
                'upload_url': post['url'],
                'upload_query': post['fields'],
                'exists': exists
            }
            if 'type' in file:
                filedata['type'] = file['type']
            res_payload['filedata'][path] = filedata

        # Return response payload
        return json.dumps(res_payload)

    except Exception as exception: # noqa
        logging.exception('Bad request (authorize)')
        return Response(status=400)


def info(auth_token, verifyer: auth.lib.Verifyer):
    """Authorize a client for the file uploading.
    :param auth_token: authentication token to test
    """
    # Verify client, deny access if not verified

    try:
        # Get request payload
        permissions = verifyer.extract_permissions(auth_token)
        if not permissions:
            return Response(status=401)
        userid = permissions.get('userid')

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

    except Exception as exception: # noqa
        logging.exception('Bad request (info)')
        return Response(status=400)


def presign(auth_token, url, verifyer: auth.lib.Verifyer, ownerid=None):
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
        permissions = verifyer.extract_permissions(auth_token)
        if not permissions or permissions.get('userid') != ownerid:
            return Response(status=403)
        parsed_url = urllib.parse.urlparse(url)
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip('/')
        # Handle s3 path-style URLs
        if bucket.endswith('amazonaws.com'):
            bucket, key = key.split('/', 1)

        # Make sure file belongs to user (only in case of pkgstore)
        if (config['STORAGE_BUCKET_NAME'] != bucket) and (ownerid not in url):
            return Response(status=403)

        signed_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=3600*24)
        return json.dumps({'url': signed_url})
    except Exception as exception: # noqa
        logging.exception('Bad request')
        return Response(status=400)
