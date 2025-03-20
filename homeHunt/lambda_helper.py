import boto3
import json
import os
from django.conf import settings
from botocore.exceptions import ClientError

AWS_REGION = settings.AWS_REGION
LAMBDA_FUNCTION_NAME = settings.LAMBDA_FUNCTION_NAME

class LambdaHelper:
    def __init__(self):
        self.lambda_client = boto3.client("lambda", region_name = AWS_REGION)

    def invoke_notification(self, payload):
        # dd( json.dumps(payload) )
        response = self.lambda_client.invoke(
            FunctionName    = LAMBDA_FUNCTION_NAME,
            InvocationType  = 'RequestResponse',  
            Payload         = json.dumps(payload)
        )
    
        response_payload = response['Payload'].read().decode('utf-8')
        response_payload = json.loads(response_payload)
        
        print(response_payload)
        return response_payload