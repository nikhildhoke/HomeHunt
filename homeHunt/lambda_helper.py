import boto3
import json
import os
from django.conf import settings
from botocore.exceptions import ClientError

AWS_REGION = settings.AWS_REGION
LAMBDA_FUNCTION_NAME = settings.LAMBDA_FUNCTION_NAME
LAMBDA_ROLE_ARN = settings.LAMBDA_ROLE_ARN

class LambdaHelper:
    def __init__(self):
        self.lambda_client = boto3.client("lambda", region_name = AWS_REGION)

    def check_lambda_function(self):
        try:
            response = self.lambda_client.get_function( FunctionName = LAMBDA_FUNCTION_NAME )
            return response["Configuration"]["FunctionArn"]
        except self.lambda_client.exceptions.ResourceNotFoundException:
            return None
        except ClientError as e:
            print(f"Lambda Check Error: {str(e)}")
            return None

    def deploy_lambda_function(self):
        lambda_arn = self.check_lambda_function()
        if lambda_arn:
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} already exists.")
            return lambda_arn

        try:
            # Zip and deploy Lambda function
            os.system("zip -r lambda_function.zip lambda_function.py")
            
            with open("lambda_function.zip", "rb") as f:
                zip_content = f.read()

            response = self.lambda_client.create_function(
                FunctionName=LAMBDA_FUNCTION_NAME,
                Runtime="python3.9",
                Role=LAMBDA_ROLE_ARN,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zip_content},
                Timeout=30,
                MemorySize=128,
            )
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} created successfully.")
            return response["FunctionArn"]
        except ClientError as e:
            print(f"Lambda Deployment Error: {str(e)}")
            return None

    def invoke_notification(self, payload):
        """Invokes the Lambda function to send notifications."""
        try:
            response = self.lambda_client.invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            return response["Payload"].read().decode("utf-8")
        except ClientError as e:
            print(f"Lambda Invocation Error: {str(e)}")
            return None
