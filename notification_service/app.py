from flask import Flask, request, jsonify
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
import datetime
import json
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jwt
from functools import wraps
from confluent_kafka import Consumer

app = Flask(__name__)

# Get individual database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

# Construct the database URL from individual components
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}.{db_name}.svc.cluster.local:{db_port}/{db_name}"
print(f"Connecting to database at {DATABASE_URL.replace(db_password, '******')}")  # Log the URL without exposing password

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET')

# Email configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-password')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@shopeasy.com')

db = SQLAlchemy(app)

# Kafka consumer configuration
kafka_consumer = Consumer({
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'notification-service',
    'auto.offset.reset': 'earliest'
})
kafka_consumer.subscribe(['order_created'])

def consume_events():
    while True:
        msg = kafka_consumer.poll(1.0)  # Poll for messages
        if msg is None:
            continue
        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue

        # Process the event
        event = json.loads(msg.value().decode('utf-8'))
        print(f"Received event: {event}")

        if event['event_type'] == 'order_created':
            # Send notification for order creation
            user_id = event['user_id']
            order_id = event['order_id']
            send_notification(user_id, 'order_placed', {
                'order_id': order_id,
                'items': event['items']
            })

# Start Kafka consumer in a separate thread
threading.Thread(target=consume_events, daemon=True).start()

# Middleware to log all incoming requests
@app.before_request
def log_request():
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}")

# Models
class Notification(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # email, sms, in-app
    content = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text, nullable=True)  # JSON string
    is_read = db.Column(db.Boolean, default=False)
    sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'content': self.content,
            'data': json.loads(self.data) if self.data else None,
            'is_read': self.is_read,
            'sent': self.sent,
            'created_at': self.created_at.isoformat()
        }

class UserNotificationPreference(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False, unique=True)
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    app_notifications = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_notifications': self.email_notifications,
            'sms_notifications': self.sms_notifications,
            'app_notifications': self.app_notifications,
            'email': self.email,
            'phone': self.phone
        }

# JWT token middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user_id, *args, **kwargs)
    
    return decorated

# Helper function to send email
def send_email(to_email, subject, content):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"Would send email to {to_email} with subject '{subject}': {content}")
        return True
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Helper function to send notification
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

# Background worker to process notifications
def notification_worker():
    with app.app_context():
        while True:
            try:
                # Get unsent notifications
                notifications = Notification.query.filter_by(sent=False).limit(10).all()
                
                for notification in notifications:
                    # Get user preferences
                    preferences = UserNotificationPreference.query.filter_by(user_id=notification.user_id).first()
                    
                    if not preferences:
                        # Create default preferences if not set
                        preferences = UserNotificationPreference(user_id=notification.user_id)
                        db.session.add(preferences)
                        db.session.commit()
                    
                    # Process notification based on type and preferences
                    if notification.type == 'email' and preferences.email_notifications and preferences.email:
                        data = json.loads(notification.data) if notification.data else {}
                        subject = data.get('subject', 'Notification from ShopEasy')
                        
                        if send_email(preferences.email, subject, notification.content):
                            notification.sent = True
                    
                    elif notification.type == 'in-app':
                        # In-app notifications are marked as sent immediately
                        notification.sent = True
                    
                    db.session.commit()
            
            except Exception as e:
                print(f"Error in notification worker: {str(e)}")
            
            # Sleep before next batch
            time.sleep(5)

# Start notification worker in a separate thread
notification_thread = threading.Thread(target=notification_worker, daemon=True)
notification_thread.start()

# Routes
@app.route('/api/notifications', methods=['POST'])
def create_notification():
    data = request.get_json()
    
    if not data or not data.get('user_id') or not data.get('type'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Generate notification content based on type
    content = ""
    notification_data = {}
    
    if data.get('type') == 'order_placed':
        order_data = data.get('data', {})
        content = f"Your order #{order_data.get('order_id')} has been placed successfully. Total amount: ${order_data.get('total_amount', 0):.2f}"
        notification_data = {
            'subject': 'Order Confirmation',
            'order_id': order_data.get('order_id'),
            'total_amount': order_data.get('total_amount', 0)
        }
    
    elif data.get('type') == 'order_status_changed':
        order_data = data.get('data', {})
        content = f"Your order #{order_data.get('order_id')} status has been updated from {order_data.get('old_status')} to {order_data.get('new_status')}."
        notification_data = {
            'subject': 'Order Status Update',
            'order_id': order_data.get('order_id'),
            'new_status': order_data.get('new_status')
        }
    
    elif data.get('type') == 'order_cancelled':
        order_data = data.get('data', {})
        content = f"Your order #{order_data.get('order_id')} has been cancelled."
        notification_data = {
            'subject': 'Order Cancellation',
            'order_id': order_data.get('order_id')
        }
    
    else:
        # For custom notifications
        content = data.get('content', 'You have a new notification')
        notification_data = data.get('data', {})
    
    # Create email notification
    email_notification = Notification(
        user_id=data['user_id'],
        type='email',
        content=content,
        data=json.dumps(notification_data)
    )
    db.session.add(email_notification)
    
    # Create in-app notification
    app_notification = Notification(
        user_id=data['user_id'],
        type='in-app',
        content=content,
        data=json.dumps(notification_data)
    )
    db.session.add(app_notification)
    
    db.session.commit()
    
    return jsonify({'message': 'Notification created successfully'}), 201

@app.route('/api/notifications', methods=['GET'])
@token_required
def get_user_notifications(current_user_id):
    notification_type = request.args.get('type', 'in-app')
    read_status = request.args.get('read')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = Notification.query.filter_by(user_id=current_user_id, type=notification_type)
    
    if read_status is not None:
        is_read = read_status.lower() == 'true'
        query = query.filter_by(is_read=is_read)
    
    notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [notification.to_dict() for notification in notifications.items],
        'total': notifications.total,
        'pages': notifications.pages,
        'page': page,
        'unread_count': Notification.query.filter_by(user_id=current_user_id, type=notification_type, is_read=False).count()
    }
    
    return jsonify(result), 200

@app.route('/api/notifications/<notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_user_id, notification_id):
    notification = Notification.query.get(notification_id)
    
    if not notification:
        return jsonify({'message': 'Notification not found'}), 404
    
    # Ensure the user can only mark their own notifications
    if notification.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify(notification.to_dict()), 200

@app.route('/api/notifications/preferences', methods=['GET'])
@token_required
def get_notification_preferences(current_user_id):
    preferences = UserNotificationPreference.query.filter_by(user_id=current_user_id).first()
    
    if not preferences:
        preferences = UserNotificationPreference(user_id=current_user_id)
        db.session.add(preferences)
        db.session.commit()
    
    return jsonify(preferences.to_dict()), 200

@app.route('/api/notifications/preferences', methods=['PUT'])
@token_required
def update_notification_preferences(current_user_id):
    data = request.get_json()
    
    preferences = UserNotificationPreference.query.filter_by(user_id=current_user_id).first()
    
    if not preferences:
        preferences = UserNotificationPreference(user_id=current_user_id)
        db.session.add(preferences)
    
    if 'email_notifications' in data:
        preferences.email_notifications = bool(data['email_notifications'])
    if 'sms_notifications' in data:
        preferences.sms_notifications = bool(data['sms_notifications'])
    if 'app_notifications' in data:
        preferences.app_notifications = bool(data['app_notifications'])
    if 'email' in data:
        preferences.email = data['email']
    if 'phone' in data:
        preferences.phone = data['phone']
    
    db.session.commit()
    
    return jsonify(preferences.to_dict()), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5004, debug=True)