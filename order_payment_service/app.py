from flask import Flask, request, jsonify
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
import datetime
import requests
import jwt
from functools import wraps
import json
from confluent_kafka import Producer
from nats.aio.client import NATS
import asyncio

app = Flask(__name__)

# Get individual database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

# Construct the database URL from individual components
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
print(f"Connecting to database at {DATABASE_URL.replace(db_password, '******')}")  # Log the URL without exposing password

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET')

# Microservice URLs
PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-inventory-service.ecommerce.svc.cluster.local')
NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service.ecommerce.svc.cluster.local')

db = SQLAlchemy(app)

# NATS publisher configuration
nats_client = NATS()

async def publish_order_created_event(order_event):
    await nats_client.connect(servers=["nats://nats:4222"])
    await nats_client.publish("order_created", json.dumps(order_event).encode('utf-8'))
    await nats_client.close()

# Middleware to log all incoming requests
@app.before_request
def log_request():
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}")

# Models
class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, processing, shipped, delivered, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    billing_address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'total_amount': self.total_amount,
            'shipping_address': self.shipping_address,
            'billing_address': self.billing_address,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'items': [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.String(36), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'price': self.price,
            'subtotal': self.quantity * self.price
        }

class Payment(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, failed
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    order = db.relationship('Order', backref=db.backref('payment', uselist=False))
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'amount': self.amount,
            'status': self.status,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.isoformat()
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

# Helper function to send notification
def send_notification(user_id, notification_type, data):
    try:
        response = requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/notifications",
            json={
                'user_id': user_id,
                'type': notification_type,
                'data': data
            }
        )
        return response.status_code == 201
    except:
        return False

# Routes
@app.route('/api/orders', methods=['POST'])
@token_required
def create_order(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('items') or not data.get('shipping_address') or not data.get('payment_method'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Validate inventory
    items_to_check = [{'product_id': item['product_id'], 'quantity': item['quantity']} for item in data['items']]
    try:
        inventory_response = requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/inventory/check",
            json={'items': items_to_check}
        )
        inventory_data = inventory_response.json()
        
        # Check if all items are available
        for item in inventory_data:
            if not item['available']:
                return jsonify({'message': item['message']}), 400
    except:
        return jsonify({'message': 'Error checking inventory'}), 500
    
    # Calculate total amount
    total_amount = sum(item['price'] * item['quantity'] for item in data['items'])
    
    # Create new order
    new_order = Order(
        user_id=current_user_id,
        total_amount=total_amount,
        shipping_address=data['shipping_address'],
        billing_address=data.get('billing_address', data['shipping_address']),
        payment_method=data['payment_method']
    )
    
    # Add order items
    for item in data['items']:
        new_order.items.append(OrderItem(
            product_id=item['product_id'],
            product_name=item['product_name'],
            quantity=item['quantity'],
            price=item['price']
        ))
    
    db.session.add(new_order)
    
    # Create payment record
    payment = Payment(
        order_id=new_order.id,
        amount=total_amount,
        payment_method=data['payment_method']
    )
    
    db.session.add(payment)
    db.session.commit()
    
    # Process payment
    # In a real application, this would integrate with a payment gateway like Stripe
    payment_successful = True
    
    if payment_successful:
        payment.status = 'completed'
        payment.transaction_id = str(uuid.uuid4())  # This would be the transaction ID from the payment gateway
        new_order.status = 'processing'
        
        # Update inventory
        try:
            requests.post(
                f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/inventory/update",
                headers={'Authorization': request.headers.get('Authorization')},
                json={'items': [{'product_id': item['product_id'], 'quantity': item['quantity'], 'operation': 'decrease'} for item in data['items']]}
            )
        except:
            # Log error, but don't fail the order
            pass
        
        # Send notification
        send_notification(
            current_user_id,
            'order_placed',
            {
                'order_id': new_order.id,
                'total_amount': total_amount,
                'status': new_order.status
            }
        )
        # Publish order_created event to NATS
        order_event = {
            'event_type': 'order_created',
            'order_id': new_order.id,
            'user_id': current_user_id,
            'items': [{'product_id': item.product_id, 'quantity': item.quantity} for item in new_order.items]
        }
        asyncio.run(publish_order_created_event(order_event))
    else:
        payment.status = 'failed'
        new_order.status = 'cancelled'
    
    db.session.commit()
    
    return jsonify({
        'order': new_order.to_dict(),
        'payment': payment.to_dict()
    }), 201

@app.route('/api/orders', methods=['GET'])
@token_required
def get_user_orders(current_user_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    orders = Order.query.filter_by(user_id=current_user_id).order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'page': page
    }
    
    return jsonify(result), 200

@app.route('/api/orders/<order_id>', methods=['GET'])
@token_required
def get_order(current_user_id, order_id):
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    # Ensure the user can only access their own orders
    if order.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify(order.to_dict()), 200

@app.route('/api/orders/<order_id>/cancel', methods=['POST'])
@token_required
def cancel_order(current_user_id, order_id):
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    # Ensure the user can only cancel their own orders
    if order.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Can only cancel orders in pending or processing status
    if order.status not in ['pending', 'processing']:
        return jsonify({'message': 'Cannot cancel order in current status'}), 400
    
    # Update order status
    order.status = 'cancelled'
    
    # Restore inventory
    try:
        requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/inventory/update",
            headers={'Authorization': request.headers.get('Authorization')},
            json={'items': [{'product_id': item.product_id, 'quantity': item.quantity, 'operation': 'increase'} for item in order.items]}
        )
    except:
        # Log error, but don't fail the cancellation
        pass
    
    db.session.commit()
    
    # Send notification
    send_notification(
        current_user_id,
        'order_cancelled',
        {
            'order_id': order.id,
            'total_amount': order.total_amount,
            'status': order.status
        }
    )
    
    return jsonify(order.to_dict()), 200

@app.route('/api/admin/orders', methods=['GET'])
@token_required
def get_all_orders(current_user_id):
    # In a real app, check if user is admin
    
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'page': page
    }
    
    return jsonify(result), 200

@app.route('/api/admin/orders/<order_id>/status', methods=['PUT'])
@token_required
def update_order_status(current_user_id, order_id):
    # In a real app, check if user is admin
    
    data = request.get_json()
    
    if not data or not data.get('status'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    # Validate status transition
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({'message': 'Invalid status'}), 400
    
    # Update order status
    old_status = order.status
    order.status = data['status']
    db.session.commit()
    
    # Send notification
    send_notification(
        order.user_id,
        'order_status_changed',
        {
            'order_id': order.id,
            'old_status': old_status,
            'new_status': order.status
        }
    )
    
    return jsonify(order.to_dict()), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True)