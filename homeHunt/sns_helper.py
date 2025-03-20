import boto3

class SNSHelper:
    def __init__(self):
        self.sns_client = boto3.client("sns", region_name="us-east-1")
        self.topic_name = "BookingNotifications"
        self.topic_arn = self.get_or_create_sns_topic()

    def get_or_create_sns_topic(self):
        topics = self.sns_client.list_topics().get("Topics", [])
        for topic in topics:
            if self.topic_name in topic["TopicArn"]:
                return topic["TopicArn"]

        response = self.sns_client.create_topic(Name=self.topic_name)
        return response["TopicArn"]

    def subscribe_email(self, email):
        response = self.sns_client.subscribe(
            TopicArn=self.topic_arn,
            Protocol="email",
            Endpoint=email
        )
        print(f"Subscription request sent to: {email}")
        return response

    def check_subscription_status(self, email):
        subscriptions = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
        for sub in subscriptions.get("Subscriptions", []):
            if sub["Endpoint"] == email:
                if sub["SubscriptionArn"] != "PendingConfirmation":
                    return True  # Email is subscribed
        return False  # Email is not subscribed or pending

    def send_booking_confirmation(self, owner_email, viewer_email):
        subject = "Booking Confirmation"
        message_owner = f"Your house viewing is confirmed!\n\nViewer: {viewer_email}"
        message_viewer = f"Your house viewing is confirmed!\n\nOwner: {owner_email}"

        self.sns_client.publish(
            TopicArn=self.topic_arn,
            Message=message_owner,
            Subject=subject
        )
        self.sns_client.publish(
            TopicArn=self.topic_arn,
            Message=message_viewer,
            Subject=subject
        )
        print(f"Booking confirmation emails sent to {owner_email} and {viewer_email}")
