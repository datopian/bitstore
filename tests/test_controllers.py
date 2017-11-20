import copy
import json
import server
import unittest

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch
from moto import mock_s3
import boto3
import requests_mock

from importlib import import_module
module = import_module('bitstore.controllers')

AUTH_TOKEN = "token"
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


class DataStoreTest(unittest.TestCase):

    # Actions
    @mock_s3
    def setUp(self):

        # Cleanup
        self.addCleanup(patch.stopall)

        # Request patch
        self.request = patch.object(module, 'request').start()
        # Various patches
        self.services = patch.object(module, 'services').start()

        self.original_config = dict(module.config)
        module.config['STORAGE_BUCKET_NAME'] = 'buckbuck'
        module.config['STORAGE_ACCESS_KEY_ID'] = ''
        module.config['STORAGE_SECRET_ACCESS_KEY'] = ''
        module.config['ACCESS_KEY_EXPIRES_IN'] = ''
        module.config['STORAGE_PATH_PATTERN'] = '{owner}/{dataset}/{path}'
        self.s3 = boto3.client('s3')
        bucket_name = module.config['STORAGE_BUCKET_NAME']
        self.s3.create_bucket(Bucket=bucket_name)

    def tearDown(self):
        module.config = self.original_config

    # Tests

    def test___call___not_authorized(self):
        authorize = module.authorize
        self.services.verify = Mock(return_value=False)
        out = authorize(AUTH_TOKEN, PAYLOAD)
        self.assertEqual(out.status, '401 UNAUTHORIZED')

    def test___call___bad_request(self):
        authorize = module.authorize
        self.assertEqual(authorize(AUTH_TOKEN, {
            'bad': 'data',
        }).status, '400 BAD REQUEST')

    @mock_s3
    def test___call___good_request(self):
        ret = module.authorize(AUTH_TOKEN, PAYLOAD)
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
                }
            }
        })

        # now do it with md5 path ...
        module.config['STORAGE_PATH_PATTERN'] = '{md5_hex}{extension}'
        ret = module.authorize(AUTH_TOKEN, PAYLOAD)
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], '044e18f0bf3b19ac0428a75c85436194.xls')

    @mock_s3
    def test___call___good_request_with_private_acl(self):
        payload = copy.deepcopy(PAYLOAD)
        payload['metadata']['findability'] = 'private'
        ret = module.authorize(AUTH_TOKEN, payload)
        self.assertIs(type(ret),str)
        output = json.loads(ret)
        query = output['filedata']['data/file1.xls']['upload_query']
        self.assertEqual(query['key'], 'owner/name/data/file1.xls')
        self.assertEqual(query['acl'], 'private')

    def test___info___not_authorized(self):
        info = module.info
        self.services.get_user_id = Mock(return_value=None)
        self.assertEqual(info(AUTH_TOKEN).status, '401 UNAUTHORIZED')

    def test___info___good_request(self):
        info = module.info
        self.services.get_user_id = Mock(return_value='12345678')
        ret = json.loads(info(AUTH_TOKEN))
        self.assertListEqual(ret['prefixes'],
                             ['http://buckbuck:80/12345678',
                              'http://buckbuck/12345678',
                              'https://buckbuck:443/12345678',
                              'https://buckbuck/12345678'])

    def test___404_rendered(self):
        self.app = server.app.test_client()
        response = self.app.get('/')
        data = json.loads(response.data)
        self.assertEqual(data.get('docs'), 'http://docs.datahub.io')
        self.assertEqual(data.get('info'),
            'rawstore service - part of the DataHub platform')

    @requests_mock.mock()
    def test__checkurl__returns_url_as_is_if_not_forbidden(self, m):
        presign = module.presign
        url = 'http://test.com'
        m.head(url, status_code=200)
        out = json.loads(presign(AUTH_TOKEN, url, 'owner'))
        self.assertEqual(out['url'], 'http://test.com')


    @requests_mock.mock()
    def test__checkurl__not_authorized(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format(module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        self.services.verify = Mock(return_value=False)
        out = presign(AUTH_TOKEN, url, 'owner')
        self.assertEqual(out.status, '403 FORBIDDEN')

    @requests_mock.mock()
    def test__checkurl__no_user(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format(module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        self.services.verify = Mock(return_value=False)
        out = presign(AUTH_TOKEN, url)
        self.assertEqual(out.status, '401 UNAUTHORIZED')

    @requests_mock.mock()
    def test__checkurl__returns_forbidden_if_url_does_not_owned_by_owner(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format('pkgstore', 'owner', 'name')
        m.head(url, status_code=403)
        self.services.verify = Mock(return_value=True)
        out = presign(AUTH_TOKEN, url, 'notowner')
        self.assertEqual(out.status, '403 FORBIDDEN')

    @requests_mock.mock()
    def test__checkurl__signes_url(self, m):
        presign = module.presign
        url = 'http://{}/{}/{}'.format(module.config['STORAGE_BUCKET_NAME'], 'owner', 'name')
        m.head(url, status_code=403)
        self.services.verify = Mock(return_value=True)
        out = json.loads(presign(AUTH_TOKEN, url, 'owner'))
        self.assertTrue(out['url'].startswith('https://s3.amazonaws.com/buckbuck/owner/name'))
        self.assertTrue('Expires=86400' in out['url'])
