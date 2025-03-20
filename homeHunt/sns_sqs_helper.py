import boto3

class BookingNotification:
    def __init__( self ):
        self.sns_client = boto3.client('sns')
        self.sqs_client = boto3.client('sqs')
        self.lambda_client = boto3.client('lambda')
        self.topic_name = 'BookingConfirmation'
        self.queue_name = 'UnsubscribedBooking'
        self.lambda_function_name = 'ProcessQueueMessages'
        self.topic_arn = self.get_or_create_topic()
        self.queue_url, self.queue_arn = self.get_or_create_queue()

    def get_or_create_topic( self ):
        topics = self.sns_client.list_topics()
        for topic in topics['Topics']:
            if self.topic_name in topic['TopicArn']:
                return topic['TopicArn']
        
        response = self.sns_client.create_topic( Name = self.topic_name )
        return response['TopicArn']

    def check_subscription( self, email ):
        response = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
        for subscription in response['Subscriptions']:
            if subscription['Endpoint'] == email and subscription['SubscriptionArn'] != 'PendingConfirmation':
                return True
        return False

    def get_or_create_queue( self ):
        queues = self.sqs_client.list_queues()
        if 'QueueUrls' in queues:
            for queue_url in queues['QueueUrls']:
                if self.queue_name in queue_url:
                    queue_arn = self.sqs_client.get_queue_attributes(
                        QueueUrl        = queue_url,
                        AttributeNames  = ['QueueArn']
                    )['Attributes']['QueueArn']
                    
                    self.setup_lambda_trigger( queue_url, queue_arn )            
                    return queue_url, queue_arn
        
        attributes = {
            'DelaySeconds': '60'  # Set delay for 2 minutes (120 seconds)
        }
        
        response = self.sqs_client.create_queue(
            QueueName  = self.queue_name,
            Attributes = attributes
        )
        
        queue_url = response['QueueUrl']
        queue_arn = self.sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['QueueArn']
        )['Attributes']['QueueArn']
        self.setup_lambda_trigger( queue_url, queue_arn )
        
        return queue_url, queue_arn
        
    def setup_lambda_trigger( self, queue_url, queue_arn ):
        lambda_arn = self.get_lambda_arn( self.lambda_function_name )
        existing_mappings = self.lambda_client.list_event_source_mappings(
            EventSourceArn  = queue_arn,
            FunctionName    = lambda_arn
        )
        
        if not self.is_mapping_already_exists( existing_mappings, queue_arn, lambda_arn ):        
            self.lambda_client.create_event_source_mapping(
                EventSourceArn  = queue_arn,
                FunctionName    = lambda_arn,
                Enabled         = True,
                BatchSize       = 1
            )

    def is_mapping_already_exists( self, mappings, queue_arn, lambda_arn ):
        for mapping in mappings['EventSourceMappings']:
            if mapping['EventSourceArn'] == queue_arn and mapping['FunctionArn'] == lambda_arn:
                return mapping['State'] == 'Enabled'
        return False

    def get_lambda_arn( self, lambda_function_name ):
        response = self.lambda_client.get_function( FunctionName = lambda_function_name )
        return response['Configuration']['FunctionArn']
        
    def subscribe_email( self, email ):
        response = self.sns_client.subscribe(
            TopicArn    = self.topic_arn,
            Protocol    = 'email',
            Endpoint    = email
        )
        return response['SubscriptionArn']
        
    def publish( self, message ):
        response = self.sns_client.publish(
            TopicArn    = self.topic_arn, 
            Message     = message
        )
        return response
        
    def delete_queue_message( self, receiptHandle ):
        self.sqs_client.delete_message(
            QueueUrl        = self.queue_url,
            ReceiptHandle   = receiptHandle
        )