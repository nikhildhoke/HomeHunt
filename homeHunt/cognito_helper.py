import boto3
import hmac
import hashlib
import base64
from django.conf import settings

class SimpleCognito:
    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO['AWS_REGION'])
        self.client_id = settings.AWS_COGNITO['CLIENT_ID']
        self.client_secret = settings.AWS_COGNITO['CLIENT_SECRET']

    def _secret_hash(self, username):
        key = self.client_secret.encode()
        message = f"{username}{self.client_id}".encode()
        return base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()

    def sign_up(self, username, password, email, phone):
        return self.client.sign_up(
            ClientId=self.client_id,
            SecretHash=self._secret_hash(username),
            Username=username,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'phone_number', 'Value': phone}
            ]
    )

    def login(self, username, password):
        return self.client.initiate_auth(
            ClientId=self.client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': self._secret_hash(username)
            }
        )
        
    def confirm_sign_up(self, username, code):
        return self.client.confirm_sign_up(
            ClientId=self.client_id,
            SecretHash=self._secret_hash(username),
            Username=username,
            ConfirmationCode=code
        )