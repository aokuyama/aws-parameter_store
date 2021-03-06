import unittest
import os
from ssm_client import SsmClient


class Store:
    SSM_HEADER = '#SSM#'

    def __init__(self, client=None, region_name='ap-northeast-1'):
        if not client:
            client = SsmClient(region_name=region_name)
        self.client = client

    def get_param(self, name):
        values = self.get_params(names=[name])
        return values[name]

    def get_params(self, names):
        if not names:
            return names
        return self.client.get_parameters(names=names)

    def get_ssm_header(self):
        return self.SSM_HEADER

    def replace_params(self, params):
        ssm_names = self.collect_ssm_names(params)
        ssm_params = self.get_params(ssm_names)
        return self.replace_got_params(params, ssm_params)
    
    def collect_ssm_names(self, params):
        ssm_header = self.get_ssm_header()
        ssm_names = []
        for key, value in params.items():
            if type(value) == str:
                if value.startswith(ssm_header):
                    ssm_names.append(value.lstrip(ssm_header))
            elif type(value) == dict:
                ssm_names.extend(self.collect_ssm_names(value))
        return ssm_names

    def replace_got_params(self, params, ssm_params):
        ssm_header = self.get_ssm_header()
        for key, value in params.items():
            if type(value) == str:
                if value.startswith(ssm_header):
                    params[key] = ssm_params[value.lstrip(ssm_header)]
            elif type(value) == dict:
                params[key] = self.replace_got_params(value, ssm_params)
        return params

    def replace_os_env(self):
        envs = self.replace_params(dict(os.environ))
        for key, value in envs.items():
            os.environ[key] = value
        return self


class TestStore(unittest.TestCase):
    class FakeBotoClient():
        def __init__(self):
            self.count = 0
        def get_parameters(self, Names=[], WithDecryption=False):
            self.count += 1
            # 与えられたキーと同じvalueを返すダミー
            params = []
            for name in Names:
                params.append({'Name': name, 'Type': 'SecureString', 'Value': name, 'Version': 1,
                              'LastModifiedDate': "2021/08/29 00:00:00", 'ARN': 'arn:aws:ssm:xx:xx:parameter/var', 'DataType': 'text'})
            return {'Parameters': params, 'InvalidParameters': [], 'ResponseMetadata': {'RequestId': 'xxx', 'HTTPStatusCode': 200, 'HTTPHeaders': {'server': 'Server', 'date': 'Sun, 29 Aug 2021 02:51:53 GMT', 'content-type': 'application/x-amz-json-1.1', 'content-length': '452', 'connection': 'keep-alive', 'x-amzn-requestid': 'xxx'}, 'RetryAttempts': 0}}

    def setUp(self):
        self.fake = self.FakeBotoClient()
        client = SsmClient(boto_client=self.fake)
        self.store = Store(client=client)

    def testパラメータストアから値を単体取得(self):
        self.assertEqual('/test/value', self.store.get_param('/test/value'))
        self.assertEqual('/test/abc', self.store.get_param('/test/abc'))

    def testパラメータストアから値をリスト取得(self):
        self.assertEqual({'/abc': '/abc'}, self.store.get_params(['/abc']))
        self.assertEqual({'/test/value': '/test/value', '/test/value2': '/test/value2'},
                         self.store.get_params(['/test/value', '/test/value2']))

    def test特定の値をパラメータストア内の値と置き換える(self):
        self.assertEqual({'aaa': 'bbb', 'abc': '/abc'},
                         self.store.replace_params({'aaa': 'bbb', 'abc': '#SSM#/abc'}))
        self.assertEqual({'aaa': '/abc', 'abc': {'ccc': 'ddd', 'abc': '/abcd'}},
                         self.store.replace_params({'aaa': '#SSM#/abc', 'abc': {'ccc': 'ddd', 'abc': '#SSM#/abcd'}}))

    def test環境変数を置き換える(self):
        os.environ['PARAMSTORETEST1'] = '#SSM#/ok'
        os.environ['PARAMSTORETEST2'] = '#aaa#aaa'
        os.environ['PARAMSTORETEST3'] = '#SSM#/ok'
        self.store.replace_os_env()
        self.assertEqual('/ok', os.getenv('PARAMSTORETEST1'))
        self.assertEqual('#aaa#aaa', os.getenv('PARAMSTORETEST2'))
        self.assertEqual('/ok', os.getenv('PARAMSTORETEST3'))

    def test既存の環境変数は起き変わらない(self):
        equal = dict(os.environ)
        self.store.replace_os_env()
        self.assertEqual(equal, dict(os.environ))

    def testローカルで値を取得できるストア(self):
        from local_client import LocalClient
        client = LocalClient({'/abc': 'ok', '/def': 'aaa'})
        store = Store(client=client)
        self.assertEqual({'/abc': 'ok'}, store.get_params(['/abc']))
        self.assertEqual({'/abc': 'ok', '/def': 'aaa'},
                         store.get_params(['/abc', '/def']))

    def testローカルで値を取得できるストアは値が登録されてないとエラーになる(self):
        from local_client import LocalClient
        client = LocalClient({})
        store = Store(client=client)
        with self.assertRaises(KeyError):
            store.get_params(['/abc'])

    def test問い合わせはまとめて一回だけ行われる(self):
        self.store.replace_params({'aaa': '#SSM#/abc', 'abc': {'ccc': {'ddd':'#SSM#/aaaa'}, 'abc': '#SSM#/abcd'}})
        self.assertEqual(1, self.fake.count)

if __name__ == '__main__':
    unittest.main()
