import boto3

class BookingNotification:
    def __init__(self):
        self.sns_client = boto3.client('sns')
        self.sqs_client = boto3.client('sqs')
        self.topic_name = 'BookingConfirmation'
        self.queue_name = 'UnsubscribedBooking'
        self.topic_arn = self.get_or_create_topic()
        # self.queue_url = self.get_or_create_queue()
        self.queue_url, self.queue_arn = self.get_or_create_queue()
        # self.setup_lambda_trigger()

    def get_or_create_topic(self):
        """Create an SNS topic if it does not exist and return its ARN."""
        topics = self.sns_client.list_topics()
        for topic in topics['Topics']:
            if self.topic_name in topic['TopicArn']:
                return topic['TopicArn']
        
        response = self.sns_client.create_topic(Name=self.topic_name)
        return response['TopicArn']

    def check_subscription(self, email):
        """Check if the email is subscribed to the SNS topic."""
        response = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
        for subscription in response['Subscriptions']:
            if subscription['Endpoint'] == email and subscription['SubscriptionArn'] != 'PendingConfirmation':
                return True
        return False

    def get_or_create_queue(self):
        """Create an SQS queue if it does not exist and return its URL."""
        queues = self.sqs_client.list_queues()
        if 'QueueUrls' in queues:
            for queue_url in queues['QueueUrls']:
                if self.queue_name in queue_url:
                    return queue_url, queues['QueueArn']
        
        response = self.sqs_client.create_queue(QueueName=self.queue_name)
        return response['QueueUrl'],self.sqs_client.get_queue_attributes(
            QueueUrl=response['QueueUrl'],
            AttributeNames=['QueueArn']
        )['Attributes']['QueueArn']
        
    def subscribe_email(self, email):
        """Subscribe an email to the SNS topic and send a subscription confirmation."""
        response = self.sns_client.subscribe(
            TopicArn=self.topic_arn,
            Protocol='email',
            Endpoint=email
        )
        return response['SubscriptionArn']
        
    def publish(self, message):
        response = self.sns_client.publish(
                TopicArn    = self.topic_arn, 
                Message     = message
        )
        return response