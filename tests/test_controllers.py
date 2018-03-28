import copy
import datetime
import json
import jwt
import unittest

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch
from moto import mock_s3
import boto3
import requests_mock

import auth
from filemanager.models import FileManager
from importlib import import_module
module = import_module('bitstore.controllers')

now = datetime.datetime.now()

PAYLOAD = {
    'metadata': {
        'owner': 'owner',
        'dataset': 'name',
    },
    'filedata': {
        'data/file1.xls': {
            'name': 'file1.xls',
            'length': 100,
            'md5': 'BE4Y8L87GawEKKdchUNhlA==',
        },
    },
}

private_key = open('tests/private.pem').read()
public_key = open('tests/public.pem').read()

def generate_token(owner='owner', max_datasets=10, max_storage=1, max_private_storage=1):
    ret = {
        'userid': owner,
        'permissions': {
            'max_dataset_num': max_datasets,
            'max_private_storage_mb': max_private_storage,
            'max_public_storage_mb': max_storage
        },
        'service': 'source'
    }
    token = jwt.encode(ret, private_key, algorithm='RS256').decode('ascii')
    return token


def full_registry(pb_size=999901, pr_size=999901):
    r = FileManager('sqlite://')
    r.init_db()
    r.add_file(
        'testing.bucket', 'owner/file1.xls', 'unlisted',
        'owner', 'owner', 'id', 'me/id/1', pb_size, now
    )
    r.add_file(
        'testing.bucket', 'owner/file1.xls', 'private',
        'owner', 'owner', 'id', 'me/id/1', pr_size, now
    )
    return r


class DataStoreTest(unittest.TestCase):

    # Actions
    @mock_s3
    def setUp(self):

        # Cleanup
        self.addCleanup(patch.stopall)

        # Request patch
        self.request = patch.object(module, 'request').start()
        # Various patches
        self.original_config = dict(module.config)
        module.config['STORAGE_BUCKET_NAME'] = self.bucket = 'buckbuck'
        module.config['STORAGE_ACCESS_KEY_ID'] = ''
        module.config['STORAGE_SECRET_ACCESS_KEY'] = ''
        module.config['ACCESS_KEY_EXPIRES_IN'] = ''
        module.config['STORAGE_PATH_PATTERN'] = '{owner}/{dataset}/{path}'
        self.s3 = boto3.client('s3')

    def tearDown(self):
        module.config = self.original_config

    # Tests

    def test___call___not_authorized(self):
        authorize = module.authorize
        out = authorize(generate_token('not_owner'),
                        PAYLOAD, auth.lib.Verifyer(public_key=public_key),
                        full_registry())
        self.assertEqual(out.status, '401 UNAUTHORIZED')

    def test___call___not_enough_public_space(self):
        authorize = module.authorize
        out = authorize(generate_token(),
                        PAYLOAD, auth.lib.Verifyer(public_key=public_key),
                        full_registry())
        self.assertEqual(out.status, '403 FORBIDDEN')
        self.assertEqual(out.response, [b'Max storage for user exceeded plan limit (1MB)'])

    def test___call___not_enough_private_space(self):
        authorize = module.authorize
        private_payload = copy.deepcopy(PAYLOAD)
        private_payload['metadata']['findability'] = 'private'
        out = authorize(generate_token(),private_payload,
                        auth.lib.Verifyer(public_key=public_key),
                        full_registry())
        self.assertEqual(out.status, '403 FORBIDDEN')
        self.assertEqual(out.response, [b'Max private storage for user exceeded plan limit (1MB)'])

    def test___call___bad_request(self):
        authorize = module.authorize
        self.assertEqual(
            authorize(generate_token(), {'bad': 'data'}, auth.lib.Verifyer(public_key=public_key), full_registry()
        ).status, '400 BAD REQUEST')

    @mock_s3
    def test___call___good_request(self):
        self.s3.create_bucket(Bucket=self.bucket)
        ret = module.authorize(generate_token(), PAYLOAD,
                                auth.lib.Verifyer(public_key=public_key),
                                full_registry(10, 10))
        self.assertIs(type(ret),str)
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], 'owner/name/data/file1.xls')
        # this the s3 specific and is changing so we can't easily diff
        del output['filedata']['data/file1.xls']['upload_query']
        self.maxDiff = 20000
        self.assertEqual(output, {
            'filedata': {
                'data/file1.xls': {
                    'upload_url': 'https://s3.amazonaws.com/' + module.config['STORAGE_BUCKET_NAME'],
                    'exists': False
                }
            }
        })

        # now do it with md5 path ...
        module.config['STORAGE_PATH_PATTERN'] = '{md5_hex}{extension}'
        ret = module.authorize(generate_token(), PAYLOAD,
                                auth.lib.Verifyer(public_key=public_key),
                                full_registry(10, 10))
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], '044e18f0bf3b19ac0428a75c85436194.xls')

    @mock_s3
    def test___call___good_request_and_key_exists(self):
        self.s3.create_bucket(Bucket=self.bucket)
        self.s3.put_object(
            ACL='public-read',
            Bucket=self.bucket,
            Key='owner/name/data/file1.xls')
        ret = module.authorize(generate_token(), PAYLOAD,
                                auth.lib.Verifyer(public_key=public_key),
                                full_registry(10, 10))
        self.assertIs(type(ret),str)
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], 'owner/name/data/file1.xls')
        # this the s3 specific and is changing so we can't easily diff
        del output['filedata']['data/file1.xls']['upload_query']
        self.maxDiff = 20000
        self.assertEqual(output, {
            'filedata': {
                'data/file1.xls': {
                    'upload_url': 'https://s3.amazonaws.com/' + module.config['STORAGE_BUCKET_NAME'],
                    'exists': True
                }
            }
        })

        # now do it with md5 path ...
        module.config['STORAGE_PATH_PATTERN'] = '{md5_hex}{extension}'
        ret = module.authorize(generate_token(), PAYLOAD,
                                auth.lib.Verifyer(public_key=public_key),
                                full_registry(10, 10))
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], '044e18f0bf3b19ac0428a75c85436194.xls')

    @mock_s3
    def test___call___good_request_with_private_acl(self):
        self.s3.create_bucket(Bucket=self.bucket)
        payload = copy.deepcopy(PAYLOAD)
        payload['metadata']['findability'] = 'private'
        ret = module.authorize(generate_token(), payload,
                                auth.lib.Verifyer(public_key=public_key),
                                full_registry(10, 10))
        self.assertIs(type(ret),str)
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], 'owner/name/data/file1.xls')
        self.assertEqual(query['acl'], 'private')

    def test___info___not_authorized(self):
        info = module.info
        self.assertEqual(
            info('not_owner', auth.lib.Verifyer(public_key=public_key)
        ).status, '401 UNAUTHORIZED')

    def test___info___good_request(self):
        info = module.info
        ret = json.loads(info(generate_token('12345678'), auth.lib.Verifyer(public_key=public_key)))
        self.assertListEqual(ret['prefixes'],
                             ['http://buckbuck:80/12345678',
                              'http://buckbuck/12345678',
                              'https://buckbuck:443/12345678',
                              'https://buckbuck/12345678'])

    @requests_mock.mock()
    def test__checkurl__returns_url_as_is_if_not_forbidden(self, m):
        presign = module.presign
        url = 'http://test.com'
        m.head(url, status_code=200)
        out = json.loads(presign(generate_token(), url, auth.lib.Verifyer(public_key=public_key), 'owner'))
        self.assertEqual(out['url'], 'http://test.com')

    @requests_mock.mock()
    def test__checkurl__not_authorized(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format(module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        out = presign(generate_token(), url, auth.lib.Verifyer(public_key=public_key), 'not-owner')
        self.assertEqual(out.status, '403 FORBIDDEN')

    @requests_mock.mock()
    def test__checkurl__no_user(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format(module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        out = presign(generate_token(), url, auth.lib.Verifyer(public_key=public_key))
        self.assertEqual(out.status, '401 UNAUTHORIZED')

    @requests_mock.mock()
    def test__checkurl__returns_forbidden_if_url_does_not_owned_by_owner(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format('pkgstore', 'owner', 'name')
        m.head(url, status_code=403)
        out = presign(generate_token(), url, auth.lib.Verifyer(public_key=public_key), 'notowner')
        self.assertEqual(out.status, '403 FORBIDDEN')

    @requests_mock.mock()
    def test__checkurl__signes_url(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format(module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        out = json.loads(presign(generate_token(), url, auth.lib.Verifyer(public_key=public_key), 'owner'))
        self.assertTrue(out['url'].startswith('https://s3.amazonaws.com/buckbuck/owner/name'))
        self.assertTrue('Expires=86400' in out['url'])

    @requests_mock.mock()
    def test__checkurl__handles_path_style_urls(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}/{}'.format(
            's3.amazonaws.com', module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        out = json.loads(presign(generate_token(), url, auth.lib.Verifyer(public_key=public_key), 'owner'))
        self.assertTrue(out['url'].startswith('https://s3.amazonaws.com/buckbuck/owner/name'))
        self.assertTrue('Expires=86400' in out['url'])
