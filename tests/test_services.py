import unittest
import os

import jwt


# this corresponds to the default name set in the services.py
# (it is configurable but setting to a different value here using os.environ is
# problematic due to when os.environ gets imported in the main services.py)
SERVICE_NAME = 'world'

# this corresponds to the default testing public key in the services.py
PRIVATE_KEY = b'''-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAzSrV/SxRNKufc6f0GQIuYMASgBCOiJW5fvCnGtVMIrWvBQoC
FAp9QwRHrbQrQJiPg6YqqnTvGhWssL5LMMvR8jXXOpFUKzYaSgYaQt1LNMCwtqMB
0FGSDjBrbmEmnDSo6g0Naxhi+SJX3BMcce1WTgKRybv3N3F+gJ9d8wPkyx9xhd3H
4200lHk4T5XK5+LyAPSnP7FNUYTdJRRxKFWgZFuII+Ex6mtUKU9LZsg9xeAC6033
dmSYe5yWfdrFehmQvPBUVH4HLtL1fXTNyXuzZwtO1v61Qc1u/j7gMsrHXW+4csjS
3lDwiiPIg6q1hTA7QJdB1M+rja2MG+owL0U9owIDAQABAoIBAHgA7ytniZQSMnDW
szsRgIkMr4WCqawQT3CFWGikjCTdOiLraK3KONxDG53pfUcKNR9eySPsw5HxTZIP
rDE9dm6CuYJDUQT5X0Ue7qtffsa7UmFxVPVBUPnFroDgiFHjp01HFysmF3X7dYJ/
Fys4FDwK2rUxoXcnhkO7c5taErAPhpmv+QncVBkouQ3bB78av6cHdQfo+7PcvYRP
x6iDPAjMpz1wF1Fkd9mSHadjuqlC3FubbwEK5nTuSl4nPULK7KaCv9NjxyzTUi23
DWk9QCv+peIK/1h75cbB9eVvZayHlFlVNtD7Mrx5rediWABSqvNLRv/aZ0/o5+FM
1cxiYPECgYEA9AEr60CPlW9vBOacCImnWHWEH/UEwi4aNTBxpZEWRuN0HnmB+4Rt
1b+7LoX6olVBN1y8YIwzkDOCVblFaT+THBNiE7ABwB87c0jYd2ULQszqrebjXPoz
8q7MqghD+4iDfvP2QmivpadfeGGzYFI49b7W5c/Iv4w0oWgutib+hDsCgYEA10Dk
hMwg61q6YVAeTIqnV7zujfzTIif9AkePAfNLolLdn0Bx5LS6oPxeRUxyy4mImwrf
p6yZGOX/7ocy7rQ3X/F6fuxwuGa74PNZPwlLuD7UUPr//OPuQihoDKvL+52XWA5U
Q09sXK+KlvuH4DJ5UsHC9kgATyuGNUOeXYBHHbkCgYEA78Zq8x2ZOz6quQUolZc3
dEzezkyHJY4KQPRe6VUesAB5riy3F4M2L5LejMQp2/WtRYsCrll3nh+P109dryRD
GpbNjQ0rWzEVyZ7u4LzRiQ43GzbFfCt+et9czUWcEIRAu7Ne7jlTSZSk03Ymv+Ns
h8jGAkTiP6C2Y1oudN7ywtsCgYBAWIa3Z+oDUQjcJD4adWxW3wSU71oSINASSV/n
nloiuRDFFVe2nYwYqbhokNTUIVXzuwlmr0LI3aBnJoVENB1FkgMjQ/ziMtvBAB3S
qS24cxe26YFykJRdtIR+HTEKE271hLsNsAVdo6ATSDey/oOkCIYGZzmocQNaks8Z
dkpMCQKBgQCfZ75r1l/Hzphb78Ygf9tOz1YUFqw/xY9jfufW4C/5SgV2q2t/AZok
LixyPP8SzJcH20iKdc9kS7weiQA0ldT2SYv6VT7IqgQ3i/qYdOmaggjBGaIuIB/B
QZOJBnaSMVJFf/ZO1/1ilGVGfZZ3TMOA1TJlcTZisk56tRTbkivL9Q==
-----END RSA PRIVATE KEY-----'''

PUBLIC_KEY = b'''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzSrV/SxRNKufc6f0GQIu
YMASgBCOiJW5fvCnGtVMIrWvBQoCFAp9QwRHrbQrQJiPg6YqqnTvGhWssL5LMMvR
8jXXOpFUKzYaSgYaQt1LNMCwtqMB0FGSDjBrbmEmnDSo6g0Naxhi+SJX3BMcce1W
TgKRybv3N3F+gJ9d8wPkyx9xhd3H4200lHk4T5XK5+LyAPSnP7FNUYTdJRRxKFWg
ZFuII+Ex6mtUKU9LZsg9xeAC6033dmSYe5yWfdrFehmQvPBUVH4HLtL1fXTNyXuz
ZwtO1v61Qc1u/j7gMsrHXW+4csjS3lDwiiPIg6q1hTA7QJdB1M+rja2MG+owL0U9
owIDAQAB
-----END PUBLIC KEY-----'''

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch
from importlib import import_module
module = import_module('bitstore.services')
module._public_key = PUBLIC_KEY

token = {
    'userid': 'bla',
    'permissions': {},
    'service': SERVICE_NAME
}
token = jwt.encode(token, PRIVATE_KEY, algorithm='RS256') \
    .decode('ascii')


class VerifyTest(unittest.TestCase):

    # Actions

    def setUp(self):
        self.addCleanup(patch.stopall)

    # Tests

    def test_verified(self):
        self.assertTrue(module.verify(token, 'bla'))
        self.assertTrue(module.verify('testing-token', '__tests'))

    def test_not_verified(self):
        self.assertFalse(module.verify('key3', 'bla'))
        self.assertFalse(module.verify('testing-token', 'bla'))
        self.assertFalse(module.verify('bla', '__tests'))
