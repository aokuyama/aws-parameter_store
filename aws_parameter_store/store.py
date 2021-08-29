import unittest
import boto3


class Store:
    def __init__(self, region_name='ap-northeast-1'):
        self.client = boto3.client('ssm', region_name=region_name)

    def get_param(self, name):
        values = self.get_params(names=[name])
        return values[name]

    def get_params(self, names):
        response = self.client.get_parameters(
            Names=names,
            WithDecryption=True
        )
        values = {}
        for param in response['Parameters']:
            values[param['Name']] = param['Value']
        return values


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
        self.store = Store()
        self.store.client = self.TestSsmClient()

    def testパラメータストアから値を単体取得(self):
        self.assertEqual('/test/value', self.store.get_param('/test/value'))
        self.assertEqual('/test/abc', self.store.get_param('/test/abc'))

    def testパラメータストアから値をリスト取得(self):
        self.assertEqual({'/abc': '/abc'}, self.store.get_params(['/abc']))
        self.assertEqual({'/test/value': '/test/value', '/test/value2': '/test/value2'},
                         self.store.get_params(['/test/value', '/test/value2']))


if __name__ == '__main__':
    unittest.main()
