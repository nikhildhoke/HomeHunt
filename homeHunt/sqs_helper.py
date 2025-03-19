import boto3
import json

class SQSHelper:
    def __init__(self):
        """
        Initializes the AWS SQS client and sets up the queue URL.
        """
        self.sqs_client = boto3.client( 'sqs', 'us-east-1' )
        self.queue_name = "BookingNotificationsQueue"
        self.queue_url = self.get_or_create_sqs_queue()

    def get_or_create_sqs_queue(self):
        """
        Checks if the SQS queue exists, and if not, creates it.
        Returns the queue URL.
        """
        response = self.sqs_client.list_queues()
        if 'QueueUrls' in response:
            for url in response['QueueUrls']:
                if self.queue_name in url:
                    return url
        
        # Create queue if it does not exist
        response = self.sqs_client.create_queue( QueueName = self.queue_name )
        return response['QueueUrl']

    def send_message(self, message_body):
        """
        Sends a booking confirmation request to the SQS queue.
        The message is stored in JSON format.
        """
        self.sqs_client.send_message(
            QueueUrl    = self.queue_url,
            MessageBody = json.dumps(message_body)
        )

    def receive_messages(self):
        """
        Retrieves messages from the SQS queue.
        Deletes messages after processing to prevent duplication.
        Returns a list of messages.
        """
        response = self.sqs_client.receive_message(
            QueueUrl            = self.queue_url,
            MaxNumberOfMessages = 5,
            WaitTimeSeconds     = 10
        )

        messages = response.get('Messages', [])
        for message in messages:
            receipt_handle = message['ReceiptHandle']
            # Delete the message after processing
            self.sqs_client.delete_message(
                QueueUrl        = self.queue_url,
                ReceiptHandle   = receipt_handle
            )
        
        return messages
