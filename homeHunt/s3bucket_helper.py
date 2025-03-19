import boto3
import json
from django.conf import settings
import botocore

class S3BucketHelper:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            region_name = 'us-east-1',
        )
        self.bucket = 'cpp-home-hunt-properties'
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Check if bucket exists, create if not"""
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self._create_bucket()
            else:
                raise Exception(f"S3 Bucket Error: {str(e)}")

    def _create_bucket(self):
        """Create S3 bucket with proper configuration"""
        region = self.s3.meta.region_name
        create_bucket_config = {}
        
        # Add region constraint if not us-east-1
        if region != 'us-east-1':
            create_bucket_config['CreateBucketConfiguration'] = {
                'LocationConstraint': region
            }

        try:
            # Create the bucket
            self.s3.create_bucket(
                Bucket=self.bucket,
                ACL='public-read',
                **create_bucket_config
            )

            # Enable ACLs for objects
            self.s3.put_bucket_ownership_controls(
                Bucket=self.bucket,
                OwnershipControls={
                    'Rules': [{
                        'ObjectOwnership': 'ObjectWriter'
                    }]
                }
            )

            # Set public read policy for objects
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{self.bucket}/*"
                }]
            }
            self.s3.put_bucket_policy(
                Bucket=self.bucket,
                Policy=json.dumps(policy)
            )

            # Wait for bucket to be ready
            waiter = self.s3.get_waiter('bucket_exists')
            waiter.wait(Bucket=self.bucket)

        except self.s3.exceptions.BucketAlreadyOwnedByYou:
            pass
        except Exception as e:
            raise Exception(f"Failed to create bucket: {str(e)}")

    def upload_file(self, file, filename):
        """Upload file to S3 bucket"""
        try:
            self.s3.upload_fileobj(
                file,
                self.bucket,
                filename,
                ExtraArgs={
                    'ContentType': file.content_type,
                    'ACL': 'public-read'
                }
            )
            return f"https://{self.bucket}.s3.{self.s3.meta.region_name}.amazonaws.com/{filename}"
        except Exception as e:
            print(f"S3 Upload Error: {str(e)}")
            raise Exception(f"S3 upload failed: {str(e)}")