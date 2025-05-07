# Frontend/db.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
import json
from flask import session

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name or '',
            'last_name': self.last_name or '',
            'address': self.address or '',
            'city': self.city or '',
            'state': self.state or '',
            'zip_code': self.zip_code or ''
        }

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def create_user(email, password, first_name='', last_name='', address='', city='', state='', zip_code=''):
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def get_user_orders(user_id):
    """Get all orders for a user from the Order Payment Service"""
    try:
        # Get API endpoint from environment variables
        order_service_url = os.environ.get('ORDER_PAYMENT_SERVICE_URL', 'http://localhost:5002/api/orders')
        
        # Get the auth token from the session
        token = session.get('auth_token', '')
        
        # Make API request to the Order service
        response = requests.get(
            f"{order_service_url}/user/{user_id}",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get orders: {response.text}")
            # Return mock data as fallback for development
            return _get_mock_orders(user_id)
            
    except Exception as e:
        print(f"Error getting orders: {str(e)}")
        # Return mock data for development or if service is down
        return _get_mock_orders(user_id)

def get_order_details(user_id, order_id):
    """Get details of a specific order from the Order Payment Service"""
    try:
        # Get API endpoint from environment variables
        order_service_url = os.environ.get('ORDER_PAYMENT_SERVICE_URL', 'http://localhost:5002/api/orders')
        
        # Get the auth token from the session
        token = session.get('auth_token', '')
        
        # Make API request to the Order service
        response = requests.get(
            f"{order_service_url}/{order_id}",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            order_data = response.json()
            # Verify that the order belongs to the user
            if str(order_data.get('user_id')) == str(user_id):
                return order_data
            return None
        else:
            print(f"Failed to get order details: {response.text}")
            # Return mock data as fallback for development
            orders = _get_mock_orders(user_id)
            for order in orders:
                if order['id'] == order_id:
                    return order
            return None
            
    except Exception as e:
        print(f"Error getting order details: {str(e)}")
        # Return mock data for development or if service is down
        orders = _get_mock_orders(user_id)
        for order in orders:
            if order['id'] == order_id:
                return order
        return None

def get_tracking_info(order_id, user_id):
    """Get tracking information for an order from the Order Payment Service"""
    try:
        # Get API endpoint from environment variables
        order_service_url = os.environ.get('ORDER_PAYMENT_SERVICE_URL', 'http://localhost:5002/api/orders')
        
        # Get the auth token from the session
        token = session.get('auth_token', '')
        
        # Make API request to the Order service
        response = requests.get(
            f"{order_service_url}/{order_id}/tracking",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get tracking info: {response.text}")
            # Return mock data as fallback for development
            return _get_mock_tracking_info(order_id)
            
    except Exception as e:
        print(f"Error getting tracking info: {str(e)}")
        # Return mock data for development or if service is down
        return _get_mock_tracking_info(order_id)

# Helper function to provide mock order data for development
def _get_mock_orders(user_id):
    """Mock order data for development"""
    return [
        {
            'id': 'ORD-1650123789-1',
            'date': '2025-04-01',
            'total': 129.99,
            'status': 'Delivered',
            'items': [
                {'product_id': 1, 'name': 'Wireless Headphones', 'quantity': 1, 'price': 129.99, 'image': 'wireless head.avif'}
            ],
            'shipping_address': '123 Main St, Anytown, AN 12345',
            'tracking_number': 'TRK123456789'
        },
        {
            'id': 'ORD-1647359189-1',
            'date': '2025-03-15',
            'total': 349.99,
            'status': 'Processing',
            'items': [
                {'product_id': 6, 'name': 'Tablet', 'quantity': 1, 'price': 349.99, 'image': 'Tablet.jpg'}
            ],
            'shipping_address': '123 Main St, Anytown, AN 12345',
            'tracking_number': 'TRK987654321'
        },
        {
            'id': 'ORD-1645458289-1',
            'date': '2025-02-21',
            'total': 899.97,
            'status': 'Delivered',
            'items': [
                {'product_id': 2, 'name': 'Smartphone', 'quantity': 1, 'price': 699.99, 'image': 'smart phone.webp'},
                {'product_id': 4, 'name': 'Smartwatch', 'quantity': 1, 'price': 199.98, 'image': 'smartwatch.jpg'}
            ],
            'shipping_address': '123 Main St, Anytown, AN 12345',
            'tracking_number': 'TRK567891234'
        }
    ]

def _get_mock_tracking_info(order_id):
    """Mock tracking data for development"""
    return {
        'order_id': order_id,
        'tracking_number': f'TRK{order_id[-6:]}',
        'status': 'In Transit',
        'estimated_delivery': '2025-05-10',
        'updates': [
            {'date': '2025-05-01', 'time': '09:30 AM', 'status': 'Order Processed', 'location': 'Warehouse'},
            {'date': '2025-05-02', 'time': '14:15 PM', 'status': 'Package Shipped', 'location': 'Distribution Center'},
            {'date': '2025-05-03', 'time': '10:45 AM', 'status': 'In Transit', 'location': 'Shipping Facility'}
        ]
    }