from models import db, Notification
import json

def send_notification(user_id, notification_type, data):
    content = ""
    notification_data = {}
    
    if notification_type == 'order_placed':
        content = f"Your order #{data.get('order_id')} has been placed successfully."
        notification_data = {
            'subject': 'Order Confirmation',
            'order_id': data.get('order_id'),
            'items': data.get('items', [])
        }
    
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