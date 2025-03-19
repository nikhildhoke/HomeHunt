import json
import boto3
from sns_helper import SNSHelper
from sqs_helper import SQSHelper

def lambda_handler(event, context):
    """
    AWS Lambda function to process booking notifications.
    
    - Subscribes owner & viewer to SNS for email confirmation
    - Reads booking requests from SQS
    - Sends booking confirmation emails after subscription confirmation
    """
    sns_helper = SNSHelper()
    sqs_helper = SQSHelper()

    # Retrieve messages from SQS
    messages = sqs_helper.receive_messages()

    for message in messages:
        booking_data = json.loads(message['Body'])

        owner_email = booking_data['owner_email']
        viewer_email = booking_data['viewer_email']

        # Subscribe owner and viewer if not already subscribed
        if not sns_helper.check_subscription_status(owner_email):
            sns_helper.subscribe_email(owner_email)

        if not sns_helper.check_subscription_status(viewer_email):
            sns_helper.subscribe_email(viewer_email)

        # Ensure both owner and viewer have subscribed before sending confirmation email
        if sns_helper.check_subscription_status(owner_email) and sns_helper.check_subscription_status(viewer_email):

            # Prepare confirmation emails
            owner_message = (
                f"📅 Booking Confirmed - Property Viewing\n\n"
                f"🏠 Property Address: {booking_data['property_address']}\n"
                f"📆 Date: {booking_data['booking_date']}\n"
                f"⏰ Time Slot: {booking_data['time_slot']}\n\n"
                f"👤 Viewer Details:\n"
                f"   - Name: {booking_data['viewer_name']}\n"
                f"   - Email: {booking_data['viewer_email']}\n"
                f"   - Phone: {booking_data['viewer_phone']}\n\n"
                f"Please be ready for the property viewing."
            )

            viewer_message = (
                f"🎉 Your Booking is Confirmed!\n\n"
                f"🏠 Property Address: {booking_data['property_address']}\n"
                f"📆 Date: {booking_data['booking_date']}\n"
                f"⏰ Time Slot: {booking_data['time_slot']}\n\n"
                f"👤 Property Owner Details:\n"
                f"   - Name: {booking_data['owner_name']}\n"
                f"   - Email: {booking_data['owner_email']}\n"
                f"   - Phone: {booking_data['owner_phone']}\n\n"
                f"Thank you for booking a property viewing! 🚀"
            )

            # Send booking confirmation emails to both owner and viewer
            sns_helper.send_booking_confirmation(owner_email, owner_message, viewer_email, viewer_message)

    return {"status": "Booking confirmation emails sent if subscription was confirmed"}
