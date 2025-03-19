import boto3

class SNSHelper:
    def __init__(self):
        """
        Initializes the AWS SNS client and sets the topic ARN.
        """
        self.sns_client = boto3.client( 'sns', 'us-east-1' )
        self.topic_name = "BookingNotifications"
        self.topic_arn  = self.get_or_create_sns_topic()

    def get_or_create_sns_topic(self):
        """
        Checks if the SNS topic exists. If not, it creates one.
        Returns the Topic ARN.
        """
        topics = self.sns_client.list_topics()
        for topic in topics.get( 'Topics', [] ):
            if self.topic_name in topic['TopicArn']:
                return topic['TopicArn']

        response = self.sns_client.create_topic( Name = self.topic_name )
        return response['TopicArn']

    def subscribe_email(self, email):
        """
        Subscribes an email address to the SNS topic.
        AWS SNS will send a confirmation email asking the user to confirm.
        """
        response = self.sns_client.subscribe(
            TopicArn    = self.topic_arn,
            Protocol    = 'email',
            Endpoint    = email
        )
        return response

    def check_subscription_status(self, email):
        """
        Checks if an email has confirmed its SNS subscription.
        Returns True if confirmed, False if still pending.
        """
        subscriptions = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
        for sub in subscriptions.get('Subscriptions', []):
            if sub['Endpoint'] == email and sub['SubscriptionArn'] != "PendingConfirmation":
                return True  # Email has successfully subscribed
        return False  # Email is not subscribed yet

    def send_booking_confirmation(self, owner_email, owner_message, viewer_email, viewer_message):
        """
        Sends booking confirmation emails to both the owner and the viewer.
        """
        # Send confirmation email to the property owner
        self.sns_client.publish(
            TopicArn=self.topic_arn,
            Subject="📅 Booking Confirmed - Property Viewing",
            Message=owner_message
        )

        # Send confirmation email to the viewer
        self.sns_client.publish(
            TopicArn=self.topic_arn,
            Subject="🎉 Your Booking is Confirmed!",
            Message=viewer_message
        )
