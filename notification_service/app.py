from flask import Flask, request, jsonify, render_template
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
import datetime
import json
import threading
import time
import jinja2
import jwt
from functools import wraps
import resend
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///notifications.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev_secret_key')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key')

db = SQLAlchemy(app)

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

def render_email_template(template_name, context):
    """
    Renders an email template with the given context.
    
    Args:
        template_name (str): The name of the template file (e.g., 'order_confirmation.html')
        context (dict): The context data to use when rendering the template
        
    Returns:
        str: The rendered HTML content
    """
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir)
    )
    template = environment.get_template(template_name)
    return template.render(**context)

def send_email_sendgrid(to_email, subject, html_content):
    """
    Sends an email using SendGrid API.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        message = Mail(
            from_email=os.environ.get('SENDER_EMAIL', 'noreply@electrocart.webstream258.online'),
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        # Get API key from environment
        if not sendgrid_api_key:
            print("SendGrid API key not found in environment variables")
            return False
            
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        print(f"SendGrid API response status code: {response.status_code}")
        
        # Check if the email was sent successfully
        if response.status_code >= 200 and response.status_code < 300:
            return True
        else:
            print(f"SendGrid error: Status code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error sending email via SendGrid: {str(e)}")
        return False

def send_email_resend(to_email, subject, html_content):
    """
    Sends an email using Resend API.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        response = resend.Emails.send({
            "from": "ElectroCart <noreply@electrocart.webstream258.online>",  # Use a verified domain
            "to": to_email,
            "subject": subject,
            "html": html_content,
        })
        print(f"Resend response: {response}")
        return True
    except Exception as e:
        print(f"Error sending email via Resend: {str(e)}")
        return False

def send_email(to_email, subject, content):
    """
    Send email using SendGrid with Resend as fallback.
    
    Args:
        to_email (str): Recipient email
        subject (str): Email subject
        content (str): HTML content
        
    Returns:
        bool: True if email was sent successfully
    """
    print(f"Attempting to send email to {to_email} with subject: {subject}")
    
    # Try SendGrid first
    if send_email_sendgrid(to_email, subject, content):
        print(f"Email sent successfully via SendGrid to {to_email}")
        return True
    
    # Fallback to Resend if SendGrid fails
    print(f"SendGrid failed, trying Resend...")
    if send_email_resend(to_email, subject, content):
        print(f"Email sent successfully via Resend to {to_email}")
        return True
    
    # Both methods failed
    print(f"Failed to send email to {to_email}")
    return False

def send_order_email(notification_type, to_email, data):
    """
    Sends an order-related email based on notification type.
    
    Args:
        notification_type (str): The type of notification ('order_placed', 'order_shipped', etc.)
        to_email (str): The recipient's email address
        data (dict): The data to include in the email
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    template_name = None
    subject = None
    
    # Determine which template to use based on notification type
    if notification_type == 'order_placed':
        template_name = 'order_confirmation.html'
        subject = f"Your Order Confirmation #{data.get('order_id')}"
    elif notification_type == 'order_shipped':
        template_name = 'order_shipped.html'
        subject = f"Your Order #{data.get('order_id')} Has Shipped!"
    elif notification_type == 'order_cancelled':
        template_name = 'order_cancelled.html'
        subject = f"Your Order #{data.get('order_id')} Has Been Cancelled"
    else:
        # Unknown notification type
        return False
    
    # Render the template with the provided data
    try:
        html_content = render_email_template(template_name, data)
        return send_email(to_email, subject, html_content)
    except Exception as e:
        print(f"Error rendering email template: {str(e)}")
        return False

@app.route('/api/sendgrid/order-confirmation', methods=['POST'])
def send_order_confirmation_sendgrid():
    """
    Send order confirmation email via SendGrid.
    This endpoint is designed to be called from your main application
    when an order is placed.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['customer_email', 'order_id', 'total_amount']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Extract data from request
        customer_email = data.get('customer_email')
        customer_name = data.get('customer_name', 'Valued Customer')
        order_id = data.get('order_id')
        total_amount = data.get('total_amount')
        
        # Calculate additional values if not provided
        subtotal = data.get('subtotal', total_amount - 5.99 - (total_amount * 0.08))
        shipping = data.get('shipping_cost', 5.99)
        tax = data.get('tax', total_amount * 0.08)
        
        # Prepare template context
        template_context = {
            'customer_name': customer_name,
            'customer_email': customer_email,
            'order_id': order_id,
            'order_date': data.get('order_date', datetime.datetime.now().strftime('%B %d, %Y')),
            'total_amount': total_amount,
            'subtotal': subtotal,
            'shipping_cost': shipping,
            'tax': tax,
            'payment_method': data.get('payment_method', 'Credit Card'),
            'shipping_address': data.get('shipping_address', ''),
            'items': data.get('items', []),
            'account_url': data.get('account_url', 'https://electrocart.webstream258.online/account'),
            'unsubscribe_url': data.get('unsubscribe_url', 'https://electrocart.webstream258.online/unsubscribe'),
            'shop_url': data.get('shop_url', 'https://electrocart.webstream258.online/shop')
        }
        
        # Render the template
        html_content = render_template('order_confirmation.html', **template_context)
        subject = f"Your Order Confirmation #{order_id}"
        
        # Send email using SendGrid
        email_sent = send_email_sendgrid(customer_email, subject, html_content)
        
        if email_sent:
            # Store notification in database for record-keeping
            notification_data = {
                'type': 'order_placed',
                'subject': 'Order Confirmation',
                'order_id': order_id,
                'total_amount': total_amount,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'items': data.get('items', []),
                'shipping_address': data.get('shipping_address', '')
            }
            
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=data.get('user_id', 'guest'),
                type='email',
                content=f"Your order #{order_id} has been placed successfully. Total amount: ${total_amount:.2f}",
                data=json.dumps(notification_data),
                sent=True
            )
            db.session.add(notification)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Order confirmation email sent via SendGrid.",
                "notification_id": notification.id
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Failed to send email via SendGrid."
            }), 500
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/send-test-sendgrid', methods=['GET'])
def send_test_sendgrid():
    """Test endpoint for SendGrid email sending"""
    customer_email = request.args.get('email', 'manyashreevangimalla@gmail.com')

    order_data = {
        'customer_name': 'John Doe',
        'customer_email': customer_email,
        'order_id': f"ORD-{uuid.uuid4().hex[:8].upper()}",
        'order_date': datetime.datetime.now().strftime('%B %d, %Y'),
        'total_amount': 99.99,
        'subtotal': 89.00,
        'shipping_cost': 5.00,
        'tax': 5.99,
        'payment_method': 'Credit Card',
        'shipping_address': '123 Main St, Anytown, USA',
        'account_url': 'https://electrocart.webstream258.online/account',
        'unsubscribe_url': 'https://electrocart.webstream258.online/unsubscribe',
        'shop_url': 'https://electrocart.webstream258.online/shop',
        'items': [
            {'product_name': 'Wireless Headphones', 'quantity': 1, 'price': 89.00, 'subtotal': 89.00}
        ]
    }

    html_content = render_template('order_confirmation.html', **order_data)
    subject = f"Your Order Confirmation #{order_data['order_id']}"

    # Test sending via SendGrid specifically
    email_sent = send_email_sendgrid(customer_email, subject, html_content)

    if email_sent:
        return jsonify({
            "success": True, 
            "message": "Order confirmation email sent via SendGrid.",
            "order_id": order_data['order_id']
        }), 200
    else:
        return jsonify({
            "success": False, 
            "message": "Failed to send email via SendGrid."
        }), 500

@app.route('/send-order-confirmation', methods=['GET'])
def send_order_confirmation():
    customer_email = request.args.get('email', 'manyashreevangimalla@gmail.com')

    order_data = {
        'customer_name': 'John Doe',
        'customer_email': 'manyashreevangimalla@gmail.com',
        'order_id': 'ORD-123456',
        'order_date': 'May 07, 2025',
        'total_amount': 99.99,
        'subtotal': 89.00,
        'shipping_cost': 5.00,
        'tax': 5.99,
        'payment_method': 'Credit Card',
        'shipping_address': '123 Main St, Anytown, USA',
        'account_url': 'https://electrocart.webstream258.online/account',
        'unsubscribe_url': 'https://electrocart.webstream258.online/unsubscribe',
        'shop_url': 'https://electrocart.webstream258.online/shop',
        'items': [
            {'product_name': 'Wireless Headphones', 'quantity': 1, 'price': 89.00, 'subtotal': 89.00}
        ]
    }

    html_content = render_template('order_confirmation.html', **order_data)
    subject = f"Your Order Confirmation #{order_data['order_id']}"

    email_sent = send_email(customer_email, subject, html_content)

    if email_sent:
        return jsonify({"success": True, "message": "Order confirmation email sent."}), 200
    else:
        return jsonify({"success": False, "message": "Failed to send email."}), 500

# Routes
@app.route('/api/notifications', methods=['POST'])
def create_notification():
    data = request.get_json()
    
    print("========== NOTIFICATION REQUEST ==========")
    print(f"Received data: {json.dumps(data, indent=2)}")
    
    if not data or not data.get('user_id'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Get notification type
    notification_type = data.get('type', '')
    
    # Generate notification content based on type
    content = ""
    notification_data = {}
    
    if notification_type == 'order_placed':
        order_data = data.get('data', {})
        order_id = order_data.get('order_id', 'Unknown')
        total_amount = order_data.get('total_amount', 0)
        content = f"Your order #{order_id} has been placed successfully. Total amount: ${total_amount:.2f}"
        
        notification_data = {
            'type': 'order_placed',
            'subject': 'Order Confirmation',
            'order_id': order_id,
            'total_amount': total_amount,
            'customer_name': data.get('customer_name', 'Valued Customer'),
            'customer_email': data.get('customer_email', ''),
            'shipping_address': order_data.get('shipping_address', ''),
            'payment_method': order_data.get('payment_method', 'Credit Card'),
            'items': order_data.get('items', []),
            'subtotal': total_amount - 5.99 - (total_amount * 0.08),
            'shipping_cost': 5.99,
            'tax': total_amount * 0.08
        }
    
    elif notification_type == 'order_shipped':
        order_data = data.get('data', {})
        order_id = order_data.get('order_id', 'Unknown')
        tracking_number = order_data.get('tracking_number', 'N/A')
        carrier = order_data.get('carrier', 'Our Shipping Partner')
        content = f"Your order #{order_id} has been shipped via {carrier}. Tracking number: {tracking_number}"
        
        notification_data = {
            'type': 'order_shipped',
            'subject': 'Your Order Has Shipped',
            'order_id': order_id,
            'customer_name': data.get('customer_name', 'Valued Customer'),
            'customer_email': data.get('customer_email', ''),
            'carrier': carrier,
            'tracking_number': tracking_number,
            'estimated_delivery': order_data.get('estimated_delivery', 'Within 3-5 business days'),
            'items': order_data.get('items', []),
            'shipping_address': order_data.get('shipping_address', '')
        }
    
    elif notification_type == 'order_cancelled':
        order_data = data.get('data', {})
        order_id = order_data.get('order_id', 'Unknown')
        reason = order_data.get('cancellation_reason', 'Customer request')
        content = f"Your order #{order_id} has been cancelled. Reason: {reason}"
        
        notification_data = {
            'type': 'order_cancelled',
            'subject': 'Order Cancellation',
            'order_id': order_id,
            'customer_name': data.get('customer_name', 'Valued Customer'),
            'customer_email': data.get('customer_email', ''),
            'cancellation_reason': reason,
            'refund_amount': order_data.get('refund_amount', None),
            'items': order_data.get('items', [])
        }
    
    elif notification_type == 'registration':
        content = data.get('content', 'Welcome to Electrocart! Your account has been successfully created.')
        notification_data = {
            'subject': 'Welcome to ElectroCart',
            'user_name': data.get('user_name', 'Valued Customer')
        }
    
    else:
        # For custom notifications
        content = data.get('content', 'You have a new notification')
        notification_data = data.get('data', {})
    
    # Get customer email
    customer_email = data.get('customer_email', '')
    if not customer_email and 'data' in data:
        customer_email = data['data'].get('customer_email', '')
    
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
    
    # Send email immediately if customer_email is provided
    if customer_email and notification_type == 'order_placed':
        # Send via SendGrid for order confirmations
        template_context = {
            'customer_name': notification_data.get('customer_name', 'Valued Customer'),
            'customer_email': customer_email,
            'order_id': notification_data.get('order_id', ''),
            'order_date': datetime.datetime.now().strftime("%B %d, %Y"),
            'total_amount': notification_data.get('total_amount', 0),
            'subtotal': notification_data.get('subtotal', 0),
            'shipping_cost': notification_data.get('shipping_cost', 5.99),
            'tax': notification_data.get('tax', 0),
            'items': notification_data.get('items', []),
            'shipping_address': notification_data.get('shipping_address', ''),
            'payment_method': notification_data.get('payment_method', 'Credit Card'),
            'account_url': data.get('account_url', 'https://electrocart.webstream258.online/account'),
            'unsubscribe_url': data.get('unsubscribe_url', 'https://electrocart.webstream258.online/unsubscribe'),
            'shop_url': data.get('shop_url', 'https://electrocart.webstream258.online/shop')
        }
        
        html_content = render_template('order_confirmation.html', **template_context)
        subject = f"Your Order Confirmation #{notification_data.get('order_id', '')}"
        
        email_sent = send_email_sendgrid(customer_email, subject, html_content)
        if email_sent:
            email_notification.sent = True
    
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
    
    notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page)
    
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

@app.route('/api/internal/user-preferences', methods=['POST'])
def set_user_preferences_internal():
    # This endpoint doesn't require authentication since it's for internal service calls
    data = request.get_json()
    
    if not data or not data.get('user_id') or not data.get('email'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    preferences = UserNotificationPreference.query.filter_by(user_id=data['user_id']).first()
    
    if not preferences:
        preferences = UserNotificationPreference(user_id=data['user_id'])
        db.session.add(preferences)
    
    # Update preferences
    preferences.email = data.get('email')
    preferences.email_notifications = data.get('email_notifications', True)
    preferences.app_notifications = data.get('app_notifications', True)
    
    db.session.commit()
    
    return jsonify(preferences.to_dict()), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'notification-service'}), 200

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
                        
                        # Extract notification type
                        notification_type = data.get('type', '')
                        
                        # If customer email is provided in the data, use it instead of preferences
                        customer_email = data.get('customer_email', preferences.email)
                        
                        # Check if this is an order-related notification
                        if notification_type in ['order_placed', 'order_shipped', 'order_cancelled']:
                            # Prepare template context
                            template_context = {
                                'customer_name': data.get('customer_name', 'Valued Customer'),
                                'customer_email': customer_email,
                                'order_id': data.get('order_id', ''),
                                'order_date': datetime.datetime.now().strftime("%B %d, %Y"),
                                'total_amount': data.get('total_amount', 0),
                                'subtotal': data.get('subtotal', 0),
                                'shipping_cost': data.get('shipping_cost', 5.99),
                                'tax': data.get('tax', 0),
                                'items': data.get('items', []),
                                'shipping_address': data.get('shipping_address', ''),
                                'payment_method': data.get('payment_method', 'Credit Card'),
                                'account_url': data.get('account_url', 'https://electrocart.webstream258.online/account'),
                                'unsubscribe_url': data.get('unsubscribe_url', 'https://electrocart.webstream258.online/unsubscribe'),
                                'shop_url': data.get('shop_url', 'https://electrocart.webstream258.online/shop')
                            }
                            
                            # For shipped orders
                            if notification_type == 'order_shipped':
                                template_context.update({
                                    'carrier': data.get('carrier', 'Our Shipping Partner'),
                                    'tracking_number': data.get('tracking_number', 'N/A'),
                                    'estimated_delivery': data.get('estimated_delivery', 'Within 3-5 business days'),
                                    'tracking_url': data.get('tracking_url', '')
                                })
                            
                            # For cancelled orders
                            elif notification_type == 'order_cancelled':
                                template_context.update({
                                    'cancellation_date': datetime.datetime.now().strftime("%B %d, %Y"),
                                    'cancellation_reason': data.get('cancellation_reason', 'Customer request'),
                                    'refund_amount': data.get('refund_amount', None)
                                })
                            
                            # Send the email
                            if send_order_email(notification_type, customer_email, template_context):
                                notification.sent = True
                        else:
                            # For non-order notifications, use the old method
                            subject = data.get('subject', 'Notification from ElectroCart')
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

# And replace with this:
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Start notification worker in a separate thread
    notification_thread = threading.Thread(target=notification_worker, daemon=True)
    notification_thread.start()
    
    port = int(os.environ.get('PORT', 5004))
    app.run(debug=True, host='0.0.0.0', port=port)
