import json
import boto3
from sns_helper import SNSHelper
from sqs_helper import SQSHelper

AWS_REGION = "us-east-1"
SQS_QUEUE_NAME = "PendingBookingQueue"

def lambda_handler(event, context):
    """Lambda function that checks SNS subscriptions and sends confirmation emails if subscribed."""
    sns_helper = SNSHelper()
    sqs_helper = SQSHelper()
    sqs_client = boto3.client("sqs", region_name=AWS_REGION)

    # Retrieve messages from SQS
    for record in event.get("Records", []):
        message_body = json.loads(record["body"])
        owner_email = message_body.get("owner_email")
        viewer_email = message_body.get("viewer_email")

        if not owner_email or not viewer_email:
            print("Invalid message format, skipping...")
            continue

        owner_subscribed = sns_helper.check_subscription_status(owner_email)
        viewer_subscribed = sns_helper.check_subscription_status(viewer_email)

        if owner_subscribed and viewer_subscribed:
            # Send booking confirmation email
            sns_helper.send_booking_confirmation(owner_email, viewer_email, message_body)
            
            # Delete message from SQS
            sqs_client.delete_message(
                QueueUrl=sqs_helper.queue_url,
                ReceiptHandle=record["receiptHandle"]
            )
            print("Booking confirmation sent, message deleted from SQS.")
        else:
            print("Subscription pending, EventBridge will retry in 1 minute.")

    return {"statusCode": 200, "body": json.dumps({"message": "Processed SQS messages."})}
