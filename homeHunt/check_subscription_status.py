import json
import boto3
import time
from sns_sqs_helper import BookingNotification

def lambda_handler(event, context):
    
    # Instantiate the Booking Notification class
    book_notification = BookingNotification()
    
    for record in event['Records']:
        message_body    = json.loads(record['body'])
        owner_email     = message_body['owner_email']
        viewer_email    = message_body['viewer_email']
        booking_details = message_body['booking_details']

        sns_message = f"""Your Booking is Confirmed!\n\n
                    Property Address: {booking_details['property_address']}\n
                    Date: {booking_details['booking_date']}\n
                    Time Slot: {booking_details['time_slot']}\n\n
                    Owner Details:\n
                        - Name: {booking_details['owner_name']}\n
                        - Email: {booking_details['owner_email']}\n
                        - Phone: {booking_details['owner_phone']}\n
                    f"Viewer Details:\n
                        - Name: {booking_details['viewer_name']}\n
                        - Email: {booking_details['viewer_email']}\n
                        - Phone: {booking_details['viewer_phone']}\n"""

    
        # Check subscriptions for owner and viewer
        owner_subscribed    = book_notification.check_subscription(owner_email)
        viewer_subscribed   = book_notification.check_subscription(viewer_email)
        
        if owner_subscribed and viewer_subscribed:
            # Both are subscribed, send booking confirmation
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
                book_notification.publish( sns_message )
                book_notification.delete_queue_message( record['receiptHandle'] )
