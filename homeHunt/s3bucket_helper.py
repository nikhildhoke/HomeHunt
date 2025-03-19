import boto3
import json
import botocore
from django.conf import settings

class S3BucketHelper:
    def __init__(self):
        self.s3 = boto3.client( 's3', region_name = settings.AWS_REGION )
        self.bucket = settings.S3_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            print(f"Bucket '{self.bucket}' already exists.")
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"Bucket '{self.bucket}' does not exist. Creating...")
                self._create_bucket()
            else:
                raise Exception(f"S3 Bucket Error: {str(e)}")

    def _create_bucket(self):
        region = self.s3.meta.region_name
        create_bucket_config = {}

        # Add region constraint if the region is not us-east-1
        if region != 'us-east-1':
            create_bucket_config['CreateBucketConfiguration'] = {
                'LocationConstraint': region
            }

        try:
            # Create the bucket without ACLs
            self.s3.create_bucket( Bucket = self.bucket, **create_bucket_config )
            print(f"Created bucket '{self.bucket}'.")

            # Set Object Ownership to 'BucketOwnerEnforced'
            self.s3.put_bucket_ownership_controls(
                Bucket=self.bucket,
                OwnershipControls={'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]}
            )
            print("Object Ownership set to 'BucketOwnerEnforced'.")

            # Disable Block Public Access settings to allow public policies
            self.s3.put_public_access_block(
                Bucket=self.bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": False,
                    "IgnorePublicAcls": False,
                    "BlockPublicPolicy": False,
                    "RestrictPublicBuckets": False
                }
            )
            print("Public access settings updated.")

            # Set a public read policy
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{self.bucket}/*"
                }]
            }
            self.s3.put_bucket_policy(Bucket=self.bucket, Policy=json.dumps(policy))
            print("Public read policy applied.")

            # Wait for the bucket to be fully created
            waiter = self.s3.get_waiter('bucket_exists')
            waiter.wait(Bucket=self.bucket)
            print(f"Bucket '{self.bucket}' is now ready.")

        except self.s3.exceptions.BucketAlreadyOwnedByYou:
            print(f"Bucket '{self.bucket}' is already owned by you.")
        except Exception as e:
            raise Exception(f"Failed to create bucket: {str(e)}")

    def upload_file(self, file, filename):
        try:
            self.s3.upload_fileobj(
                file,
                self.bucket,
                filename,
                ExtraArgs={'ContentType': file.content_type} 
            )
            file_url = f"https://{self.bucket}.s3.{self.s3.meta.region_name}.amazonaws.com/{filename}"
            print(f"File uploaded successfully: {file_url}")
            return file_url
        except Exception as e:
            print(f"S3 Upload Error: {str(e)}")
            raise Exception(f"S3 upload failed: {str(e)}")
