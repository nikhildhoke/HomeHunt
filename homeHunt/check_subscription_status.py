import json
from sns_helper import SNSHelper
from sqs_helper import SQSHelper

class CheckSubscription:
    def __init__(self):
        self.sns_helper = SNSHelper()
        self.sqs_helper = SQSHelper()

    def process_pending_bookings(self):
        messages = self.sqs_helper.receive_messages()
        for message in messages:
            booking_data = json.loads(message["Body"])
            email_owner = booking_data["email_owner"]
            email_viewer = booking_data["email_viewer"]

            owner_subscribed = self.sns_helper.check_subscription_status(email_owner)
            viewer_subscribed = self.sns_helper.check_subscription_status(email_viewer)

            if owner_subscribed and viewer_subscribed:
                print(f"Both {email_owner} and {email_viewer} are now subscribed. Sending booking confirmation.")

                self.sns_helper.send_booking_confirmation(email_owner, email_viewer)
                self.sqs_helper.delete_message(message["ReceiptHandle"])
                print(f"Processed and removed booking from SQS for {email_owner} and {email_viewer}")
            else:
                print(f"Subscription still pending for {email_owner} or {email_viewer}. Retrying later.")

def lambda_handler(event, context):
    checker = CheckSubscription()
    checker.process_pending_bookings()
    return {"status": "Checked pending bookings"}
