import boto3


class SsmClient:
    def __init__(self, boto_client=None, region_name='ap-northeast-1'):
        if not boto_client:
            boto_client = boto3.client('ssm', region_name=region_name)
        self.boto_client = boto_client

    def get_parameters(self, names):
        response = self.boto_client.get_parameters(
            Names=names,
            WithDecryption=True
        )
        values = {}
        for param in response['Parameters']:
            values[param['Name']] = param['Value']
        return values
