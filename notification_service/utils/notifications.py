from models import db, Notification, UserNotificationPreference
import json
from utils.email import send_email_sendgrid

def send_notification(user_id, notification_type, data):
    content = ""
    notification_data = {}

    print("\n\n Shubham sending notification \n\n", flush=True)
    
    if notification_type == 'order_placed':
        content = f"Your order #{data.get('order_id')} has been placed successfully."
        notification_data = {
            'subject': 'Order Confirmation',
            'order_id': data.get('order_id'),
            'items': data.get('items', [])
        }
        # Send email via SendGrid if user has email notifications enabled
        preferences = UserNotificationPreference.query.filter_by(user_id=user_id).first()
        if preferences and preferences.email_notifications and preferences.email:
            print("\n\n Shubham sending sendgrid email \n\n", flush=True)
            send_email_sendgrid(
                preferences.email,
                notification_data['subject'],
                content
            )
    
    # Create email notification
    email_notification = Notification(
        user_id=user_id,
        type='email',
        content=content,
        data=json.dumps(notification_data)
    )
    db.session.add(email_notification)
    
    # Create in-app notification
    app_notification = Notification(
        user_id=user_id,
        type='in-app',
        content=content,
        data=json.dumps(notification_data)
    )
    db.session.add(app_notification)
    
    db.session.commit() 