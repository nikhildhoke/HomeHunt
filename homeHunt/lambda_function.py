import json
import boto3
from sns_sqs_helper import BookingNotification

def lambda_handler(event, context):
    
    data = event
    owner_email = data['owner_email']
    viewer_email = data['viewer_email']

    sns_message = f"""Your Booking is Confirmed!
    Property Address: {data['property_address']}
    Date: {data['booking_date']}
    Time Slot: {data['time_slot']}
    Owner Details:
        - Name: {data['owner_name']}
        - Email: {data['owner_email']}
        - Phone: {data['owner_phone']}
    Viewer Details:
        - Name: {data['viewer_name']}
        - Email: {data['viewer_email']}
        - Phone: {data['viewer_phone']}"""

    # Instantiate the Booking Notification class
    book_notification = BookingNotification()

    # Check subscriptions for owner and viewer
    owner_subscribed    = book_notification.check_subscription(owner_email)
    viewer_subscribed   = book_notification.check_subscription(viewer_email)

    # Handle notification logic
    if owner_subscribed and viewer_subscribed:
        # Both are subscribed, send booking confirmation
        book_notification.publish( sns_message )
    else:
        # At least one party is not subscribed, enqueue the information
        message_body = {
            'owner_email': owner_email,
            'viewer_email': viewer_email,
            'booking_details': data,
            'message': 'Please subscribe to receive booking confirmation.'
        }
        
        book_notification.sqs_client.send_message(
            QueueUrl    = book_notification.queue_url, 
            MessageBody = json.dumps( message_body ) 
        )

        book_notification.subscribe_email( owner_email )
        book_notification.subscribe_email( viewer_email )

    return {
        'statusCode': 200,
        'body': json.dumps('Processing completed.')
    }
