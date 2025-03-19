import boto3
import json
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
SQS_QUEUE_NAME = "PendingBookingQueue"
LAMBDA_FUNCTION_NAME = "SendBookingConfirmation"
EVENT_RULE_NAME = "CheckSubscriptionEveryMinute"

class SQSHelper:
    def __init__(self):
        self.sqs_client = boto3.client("sqs", region_name=AWS_REGION)
        self.lambda_client = boto3.client("lambda", region_name=AWS_REGION)
        self.events_client = boto3.client("events", region_name=AWS_REGION)
        self.queue_url = self.get_or_create_sqs_queue()

        # Ensure the EventBridge rule is configured
        self.setup_eventbridge_rule()

    def get_or_create_sqs_queue(self):
        """Ensures the SQS queue exists and returns its URL, associating it with the Lambda function."""
        try:
            response = self.sqs_client.get_queue_url(QueueName=SQS_QUEUE_NAME)
            queue_url = response["QueueUrl"]
        except self.sqs_client.exceptions.QueueDoesNotExist:
            print("Creating new SQS queue...")
            response = self.sqs_client.create_queue(
                QueueName=SQS_QUEUE_NAME,
                Attributes={"MessageRetentionPeriod": "600"}  # Messages retained for 10 minutes
            )
            queue_url = response["QueueUrl"]

        # Ensure the queue is associated with the Lambda function
        self.associate_sqs_with_lambda(queue_url)

        return queue_url

    def associate_sqs_with_lambda(self, queue_url):
        """Associates the SQS queue with the Lambda function to trigger it."""
        try:
            queue_arn = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["QueueArn"]
            )["Attributes"]["QueueArn"]

            print(f"Associating SQS {SQS_QUEUE_NAME} with Lambda {LAMBDA_FUNCTION_NAME}...")

            # Give SQS permission to invoke Lambda
            self.lambda_client.create_event_source_mapping(
                EventSourceArn=queue_arn,
                FunctionName=LAMBDA_FUNCTION_NAME,
                Enabled=True,
                BatchSize=1
            )

            print("SQS successfully associated with Lambda.")
        except ClientError as e:
            print(f"Error associating SQS with Lambda: {str(e)}")

    def setup_eventbridge_rule(self):
        """Creates an EventBridge rule to invoke Lambda every minute for 10 minutes if message is in SQS."""
        try:
            print(f"Setting up EventBridge rule: {EVENT_RULE_NAME}")

            # Check if rule exists
            rules = self.events_client.list_rules(NamePrefix=EVENT_RULE_NAME)
            rule_exists = any(rule["Name"] == EVENT_RULE_NAME for rule in rules.get("Rules", []))

            if not rule_exists:
                self.events_client.put_rule(
                    Name=EVENT_RULE_NAME,
                    ScheduleExpression="rate(1 minute)",
                    State="ENABLED"
                )

                # Allow EventBridge to invoke the Lambda function
                self.lambda_client.add_permission(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    StatementId="EventBridgeInvoke",
                    Action="lambda:InvokeFunction",
                    Principal="events.amazonaws.com",
                    SourceArn=f"arn:aws:events:{AWS_REGION}:537364842544:rule/{EVENT_RULE_NAME}"
                )

                # Attach Lambda function to EventBridge rule
                self.events_client.put_targets(
                    Rule=EVENT_RULE_NAME,
                    Targets=[{
                        "Id": "1",
                        "Arn": f"arn:aws:lambda:{AWS_REGION}:537364842544:function:{LAMBDA_FUNCTION_NAME}"
                    }]
                )
                print("EventBridge rule successfully created.")

        except ClientError as e:
            print(f"Error setting up EventBridge rule: {str(e)}")

    def send_message(self, message_body):
        """Sends a message to the SQS queue."""
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )
            return response
        except ClientError as e:
            print(f"SQS Send Error: {str(e)}")
            return None

    def delete_message(self, receipt_handle):
        """Deletes a processed message from the SQS queue."""
        try:
            self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except ClientError as e:
            print(f"SQS Delete Error: {str(e)}")
