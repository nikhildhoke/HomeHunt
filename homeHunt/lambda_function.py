import json
import boto3
from botocore.exceptions import ClientError
from sns_helper import SNSHelper
from sqs_helper import SQSHelper

AWS_REGION = "us-east-1"
SQS_QUEUE_NAME = "PendingBookingQueue"

def lambda_handler(event, context):
    """Lambda function to check SNS topic, handle subscriptions, and store messages in SQS."""
    try:
        # Parse input payload
        data = json.loads(event["body"]) if "body" in event else event
        owner_email = data.get("owner_email")
        viewer_email = data.get("viewer_email")

        # Validate input
        if not owner_email or not viewer_email:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing email addresses"})}

        sns_helper = SNSHelper()
        sqs_helper = SQSHelper()

        # Ensure SNS topic exists
        topic_arn = sns_helper.get_or_create_sns_topic()

        # Check subscription status
        owner_subscribed = sns_helper.check_subscription_status(owner_email)
        viewer_subscribed = sns_helper.check_subscription_status(viewer_email)

        if not owner_subscribed or not viewer_subscribed:
            print(f"Subscription pending. Sending subscription email to {owner_email} and {viewer_email}")

            # Subscribe both emails to SNS topic
            if not owner_subscribed:
                sns_helper.subscribe_email(owner_email)
            if not viewer_subscribed:
                sns_helper.subscribe_email(viewer_email)

            # Ensure SQS queue exists
            queue_url = sqs_helper.get_or_create_sqs_queue()

            # Store booking confirmation message in SQS
            sqs_message = {
                "owner_email": owner_email,
                "viewer_email": viewer_email,
                "property_id": data.get("property_id"),
                "property_address": data.get("property_address"),
                "booking_date": data.get("booking_date"),
                "time_slot": data.get("time_slot")
            }
            sqs_helper.send_message(sqs_message)

            return {"statusCode": 202, "body": json.dumps({"message": "Subscription pending, message stored in SQS."})}

        # If both are subscribed, send booking confirmation email
        sns_helper.send_booking_confirmation(owner_email, viewer_email, data)

        return {"statusCode": 200, "body": json.dumps({"message": "Booking confirmed, email sent."})}

    except Exception as e:
        print(f"Error in lambda_function: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
