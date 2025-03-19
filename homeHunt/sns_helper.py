import boto3
import json
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
SNS_TOPIC_NAME = "BookingNotifications"

class SNSHelper:
    def __init__(self):
        self.sns_client = boto3.client("sns", region_name=AWS_REGION)
        self.topic_arn = self.get_or_create_sns_topic()

    def get_or_create_sns_topic(self):
        """Ensures the SNS topic exists and returns its ARN."""
        try:
            topics = self.sns_client.list_topics().get("Topics", [])
            for topic in topics:
                if SNS_TOPIC_NAME in topic["TopicArn"]:
                    return topic["TopicArn"]
            response = self.sns_client.create_topic(Name=SNS_TOPIC_NAME)
            return response["TopicArn"]
        except ClientError as e:
            print(f"SNS Topic Error: {str(e)}")
            return None

    def subscribe_email(self, email):
        """Subscribes an email to the SNS topic."""
        try:
            response = self.sns_client.subscribe(
                TopicArn=self.topic_arn,
                Protocol="email",
                Endpoint=email,
                ReturnSubscriptionArn=True
            )
            return response
        except ClientError as e:
            print(f"SNS Subscription Error for {email}: {str(e)}")
            return None

    def check_subscription_status(self, email):
        """Checks if an email is subscribed to the SNS topic."""
        try:
            subscriptions = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
            for sub in subscriptions.get("Subscriptions", []):
                if sub["Endpoint"] == email and sub["SubscriptionArn"] != "PendingConfirmation":
                    return True
            return False
        except ClientError as e:
            print(f"SNS Subscription Check Error: {str(e)}")
            return False

    def send_booking_confirmation(self, owner_email, viewer_email, booking_data):
        """Sends booking confirmation emails to owner and viewer."""
        booking_message = f"Booking confirmed for {booking_data['property_address']} on {booking_data['booking_date']}."

        try:
            self.sns_client.publish(
                TopicArn=self.topic_arn,
                Message=booking_message,
                Subject="Booking Confirmation"
            )
        except ClientError as e:
            print(f"SNS Publish Error: {str(e)}")
