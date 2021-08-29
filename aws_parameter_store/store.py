import unittest
import os
import boto3


class Store:
    SSM_HEADER = '#SSM#'

    def __init__(self, client=None, region_name='ap-northeast-1'):
        if not client:
            client = boto3.client('ssm', region_name=region_name)
        self.client = client

    def get_param(self, name):
        values = self.get_params(names=[name])
        return values[name]

    def get_params(self, names):
        if not names:
            return names
        response = self.client.get_parameters(
            Names=names,
            WithDecryption=True
        )
        values = {}
        for param in response['Parameters']:
            values[param['Name']] = param['Value']
        return values

    def get_ssm_header(self):
        return self.SSM_HEADER

    def replace_params(self, params):
        ssm_header = self.get_ssm_header()
        ssm_names = []
        for key, value in params.items():
            if type(value) == str:
                if value.startswith(ssm_header):
                    ssm_names.append(value.lstrip(ssm_header))
            elif type(value) == dict:
                ssm_names.extend(self.replace_params(value))

        ssm_params = self.get_params(ssm_names)
        return self.replace_got_params(params, ssm_params)

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
    class TestSsmClient():
        def get_parameters(self, Names=[], WithDecryption=False):
            # 与えられたキーと同じvalueを返すダミー
            params = []
            for name in Names:
                params.append({'Name': name, 'Type': 'SecureString', 'Value': name, 'Version': 1,
                              'LastModifiedDate': "2021/08/29 00:00:00", 'ARN': 'arn:aws:ssm:xx:xx:parameter/var', 'DataType': 'text'})
            return {'Parameters': params, 'InvalidParameters': [], 'ResponseMetadata': {'RequestId': 'xxx', 'HTTPStatusCode': 200, 'HTTPHeaders': {'server': 'Server', 'date': 'Sun, 29 Aug 2021 02:51:53 GMT', 'content-type': 'application/x-amz-json-1.1', 'content-length': '452', 'connection': 'keep-alive', 'x-amzn-requestid': 'xxx'}, 'RetryAttempts': 0}}

    def setUp(self):
        client = self.TestSsmClient()
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


if __name__ == '__main__':
    unittest.main()
