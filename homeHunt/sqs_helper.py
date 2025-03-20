import boto3
import json

class SQSHelper:
    def __init__(self):
        self.sqs_client = boto3.client("sqs", region_name="us-east-1")
        self.queue_name = "PendingBookingQueue"
        self.queue_url = self.get_or_create_sqs_queue()

    def get_or_create_sqs_queue(self):
        response = self.sqs_client.create_queue(QueueName=self.queue_name)
        return response["QueueUrl"]

    def send_message(self, email_owner, email_viewer):
        message = {"email_owner": email_owner, "email_viewer": email_viewer}
        response = self.sqs_client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message)
        )
        print(f"Booking request added to SQS for {email_owner} and {email_viewer}")
        return response

    def receive_messages(self):
        response = self.sqs_client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10
        )
        return response.get("Messages", [])

    def delete_message(self, receipt_handle):
        self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
