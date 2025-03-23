import boto3
import hmac
import hashlib
import base64
from django.conf import settings
from botocore.exceptions import ClientError

CLIENT_NAME = "CognitoClient"

class SimpleCognito:
    def __init__(self):
        self.client                         = boto3.client("cognito-idp",region_name=settings.AWS_REGION)
        self.user_pool_id                   = self.get_or_create_user_pool()
        self.client_id, self.client_secret  = self.get_or_create_user_pool_client()

    def _secret_hash(self, username):
        key     = self.client_secret.encode()
        message = f"{username}{self.client_id}".encode()
        return base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()

    def sign_up(self, username, password, email, phone):
        return self.client.sign_up(
            ClientId    = self.client_id,
            SecretHash  = self._secret_hash(username),
            Username    = username,
            Password    = password,
            UserAttributes = [
                                {'Name': 'email', 'Value': email},
                                {'Name': 'phone_number', 'Value': phone}
            ]
    )
    
    def _secret_hash(self, username):
        key = self.client_secret.encode()
        message = f"{username}{self.client_id}".encode()
        return base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()

    def get_or_create_user_pool(self):
        try:
            # List existing user pools
            response = self.client.list_user_pools(MaxResults=60)
            for pool in response.get("UserPools", []):
                if pool["Name"] == settings.AWS_USER_POOL_NAME:
                    return pool["Id"]

            # If no matching user pool found, create a new one
            print("Creating new Cognito User Pool...")
            response = self.client.create_user_pool(
                PoolName    = settings.AWS_USER_POOL_NAME,
                Policies    = {
                                "PasswordPolicy": {
                                                    "MinimumLength": 8,
                                                    "RequireUppercase": True,
                                                    "RequireLowercase": True,
                                                    "RequireNumbers": True,
                                                    "RequireSymbols": True,
                                                    "TemporaryPasswordValidityDays": 7,
                                }
                },
                AutoVerifiedAttributes = ["email"],
                Schema  = [
                                { "Name": "email", "AttributeDataType": "String", "Mutable": True, "Required": True},
                                { "Name": "phone_number", "AttributeDataType": "String", "Mutable": True, "Required": False},
                ],
            )
            user_pool_id = response["UserPool"]["Id"]
            return user_pool_id

        except ClientError as e:
            raise

    def get_or_create_user_pool_client(self):
        try:
            # List existing user pool clients
            response = self.client.list_user_pool_clients( UserPoolId = self.user_pool_id, MaxResults = 60 )
            for client in response.get( "UserPoolClients", [] ):
                if client["ClientName"] == CLIENT_NAME:
                    return client["ClientId"], self.get_client_secret( client["ClientId"] )

            # If no client found, create a new one
            response = self.client.create_user_pool_client(
                UserPoolId          = self.user_pool_id,
                ClientName          = CLIENT_NAME,
                GenerateSecret      = True,
                ExplicitAuthFlows   = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_CUSTOM_AUTH", "ALLOW_ADMIN_USER_PASSWORD_AUTH"],
            )
            
            client_id       = response["UserPoolClient"]["ClientId"]
            client_secret   = response["UserPoolClient"].get("ClientSecret")
            
            return client_id, client_secret

        except ClientError as e:
            raise

    def get_client_secret(self, client_id):
        try:
            response = self.client.describe_user_pool_client( UserPoolId = self.user_pool_id, ClientId = client_id )
            return response["UserPoolClient"].get("ClientSecret")
        except ClientError as e:
            raise

    def login(self, username, password):
        return self.client.initiate_auth(
            ClientId        = self.client_id,
            AuthFlow        = 'USER_PASSWORD_AUTH',
            AuthParameters  = {
                                'USERNAME': username,
                                'PASSWORD': password,
                                'SECRET_HASH': self._secret_hash(username)
            }
        )
        
    def confirm_sign_up(self, username, code):
        return self.client.confirm_sign_up(
            ClientId            = self.client_id,
            SecretHash          = self._secret_hash(username),
            Username            = username,
            ConfirmationCode    = code
        )