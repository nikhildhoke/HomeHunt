import json
import boto3
from sns_sqs_helper import BookingNotification

def lambda_handler(event, context):
    # Parse the incoming JSON payload
    # data = json.loads(event['body'])
    data = event
    owner_email = data['owner_email']
    viewer_email = data['viewer_email']
    
    # Instantiate the Booking Notification class
    book_notification = BookingNotification()

    # Check subscriptions for owner and viewer
    owner_subscribed    = book_notification.check_subscription(owner_email)
    viewer_subscribed   = book_notification.check_subscription(viewer_email)

    # Handle notification logic
    if owner_subscribed and viewer_subscribed:
        # Both are subscribed, send booking confirmation
        sns_message = f"Booking confirmed for {data['date']} at {data['time_slot']} at {data['property_address']}."
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
