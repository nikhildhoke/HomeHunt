import json
import boto3
import time
from sns_sqs_helper import BookingNotification

def lambda_handler(event, context):
    book_notification = BookingNotification()
    
    # Instantiate the Booking Notification class
    book_notification = BookingNotification()
    
    for record in event['Records']:
        message_body    = json.loads(record['body'])
        owner_email     = message_body['owner_email']
        viewer_email    = message_body['viewer_email']
        booking_details = message_body['booking_details']
    
        # Check subscriptions for owner and viewer
        owner_subscribed    = book_notification.check_subscription(owner_email)
        viewer_subscribed   = book_notification.check_subscription(viewer_email)
        
        if owner_subscribed and viewer_subscribed:
            # Both are subscribed, send booking confirmation
            sns_message = f"Booking confirmed for {booking_details['date']} at {booking_details['time_slot']} at {booking_details['property_address']}."
            book_notification.publish( sns_message )
        
        else:
            book_notification.subscribe_email( owner_email )
            book_notification.subscribe_email( viewer_email )
            
            time.sleep(120)  # Wait for 2 minutes
            
            # Check again after 2 minutes
            owner_subscribed    = book_notification.check_subscription( owner_email )
            viewer_subscribed   = book_notification.check_subscription( viewer_email )
            
            if owner_subscribed and viewer_subscribed:
                # Both are subscribed, send booking confirmation
                sns_message = f"Booking confirmed for {booking_details['date']} at {booking_details['time_slot']} at {booking_details['property_address']}."
                book_notification.publish( sns_message )
                book_notification.delete_queue_message( record['receiptHandle'] )
