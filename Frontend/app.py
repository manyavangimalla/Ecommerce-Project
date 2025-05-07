import string
import random
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
import jwt
import time
import uuid
from functools import wraps
from datetime import datetime
from db import db, get_user_by_email, create_user, User

# Import for SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load dotenv for environment variables
from dotenv import load_dotenv
load_dotenv()

# Disable SSL verification globally for development
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

# Also disable for requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the db with the app
db.init_app(app)

# Add this import at the top with your other imports
import random
from datetime import datetime, timedelta

# Add this global variable to temporarily store verification codes
# In a real application, you would use a database
VERIFICATION_CODES = {}  # Format: {email: {'code': '123456', 'expires': datetime}}

# Global list to store orders temporarily (would be a database in production)
ORDERS = []

# Add the new function here
def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Mock data - In production this would come from your microservices
PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 129.99, "description": "High-quality wireless headphones with noise cancellation", "stock": 50, "category": "Electronics", "image": "wireless head.avif", "related_ids": [7]},
    {"id": 2, "name": "Smartphone", "price": 699.99, "description": "Latest model with advanced camera and long battery life", "stock": 30, "category": "Electronics", "image": "smart phone.webp", "related_ids": [8]},
    {"id": 3, "name": "Laptop", "price": 999.99, "description": "Lightweight laptop with powerful processor and ample storage", "stock": 20, "category": "Electronics", "image": "laptop.jpg", "related_ids": [9]},
    {"id": 4, "name": "Smartwatch", "price": 249.99, "description": "Track your fitness and stay connected with this smartwatch", "stock": 40, "category": "Wearables", "image": "smartwatch.jpg", "related_ids": [10]},
    {"id": 5, "name": "Bluetooth Speaker", "price": 79.99, "description": "Portable speaker with amazing sound quality", "stock": 60, "category": "Audio", "image": "bluetoothSpeaker.jpg", "related_ids": [11]},
    {"id": 6, "name": "Tablet", "price": 349.99, "description": "Perfect for work and entertainment on the go", "stock": 25, "category": "Electronics", "image": "Tablet.jpg", "related_ids": [12]},
    {"id": 7, "name": "Wireless Headphones Pro", "price": 139.99, "description": "Upgraded wireless headphones with enhanced bass", "stock": 35, "category": "Electronics", "image": "wireless head.avif", "related_ids": [1]},
    {"id": 8, "name": "Smartphone XL", "price": 749.99, "description": "Larger display smartphone with extended battery life", "stock": 28, "category": "Electronics", "image": "smart phone.webp", "related_ids": [2]},
    {"id": 9, "name": "Laptop Plus", "price": 1049.99, "description": "Powerful laptop for professionals and gamers", "stock": 15, "category": "Electronics", "image": "laptop.jpg", "related_ids": [3]},
    {"id": 10, "name": "Smartwatch Lite", "price": 199.99, "description": "Affordable smartwatch with essential fitness tracking", "stock": 50, "category": "Wearables", "image": "smartwatch.jpg", "related_ids": [4]},
    {"id": 11, "name": "Bluetooth Speaker Mini", "price": 59.99, "description": "Compact speaker with impressive sound for its size", "stock": 70, "category": "Audio", "image": "bluetoothSpeaker.jpg", "related_ids": [5]},
    {"id": 12, "name": "Tablet Pro", "price": 399.99, "description": "High-performance tablet with stylus support", "stock": 18, "category": "Electronics", "image": "Tablet.jpg", "related_ids": [6]},
]

# Wishlist model
class WishlistItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    product_id = db.Column(db.String(36), nullable=False) 
    product_name = db.Column(db.String(200), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    product_image = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_price': self.product_price,
            'product_image': self.product_image,
            'created_at': self.created_at.isoformat()
        }

  
# Helper function to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/wishlist')
@login_required
def wishlist_page():
    return render_template('wishlist.html')

@app.route('/api/wishlist', methods=['GET'])
@login_required
def get_wishlist():
    user_id = session.get('user_id')
    print(f"Getting wishlist for user: {user_id}")
    wishlist_items = WishlistItem.query.filter_by(user_id=user_id).order_by(WishlistItem.created_at.desc()).all()
    return jsonify([item.to_dict() for item in wishlist_items]), 200

@app.route('/api/wishlist/check/<product_id>', methods=['GET'])
@login_required
def check_wishlist_status(product_id):
    user_id = session.get('user_id')
    # Convert product_id to string for consistency
    product_id = str(product_id)
    
    item = WishlistItem.query.filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    return jsonify({'in_wishlist': item is not None}), 200

@app.route('/api/wishlist', methods=['POST'])
@login_required
def add_to_wishlist():
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data or not all(k in data for k in ('product_id', 'product_name', 'product_price')):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Convert product_id to string for storage
    product_id = str(data['product_id'])
    print(f"Adding to wishlist: Product ID: {product_id}, User ID: {user_id}")
    
    # Check if item already exists in wishlist
    existing_item = WishlistItem.query.filter_by(
        user_id=user_id, 
        product_id=product_id
    ).first()
    
    if existing_item:
        return jsonify({'message': 'Item already in wishlist'}), 409
    
    # Create new wishlist item
    wishlist_item = WishlistItem(
        id=str(uuid.uuid4()),
        user_id=user_id,
        product_id=product_id,
        product_name=data['product_name'],
        product_price=data['product_price'],
        product_image=data.get('product_image', '')
    )
    
    db.session.add(wishlist_item)
    db.session.commit()
    
    return jsonify(wishlist_item.to_dict()), 201

@app.route('/')
def index():
    featured_products = PRODUCTS[:4]  # Just get first 4 for featured section
    return render_template('index.html', featured_products=featured_products)

@app.route('/order-history')
@login_required
def order_history():
    """Display order history for the current user"""
    user_id = session.get('user_id')
    
    # Get orders from the Order Payment Service
    orders = get_user_orders(user_id)
    
    return render_template('order_history.html', orders=orders)

@app.route('/order-details/<order_id>')
@login_required
def order_details(order_id):
    """Display details of a specific order"""
    user_id = session.get('user_id')
    
    # Get order details from the Order Payment Service
    order = get_order_details(user_id, order_id)
    
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('order_history'))
    
    return render_template('order_details.html', order=order)

@app.route('/track-order/<order_id>')
@login_required
def track_order(order_id):
    """Track an order's shipping status"""
    user_id = session.get('user_id')
    
    # Get order details first to verify ownership
    order = get_order_details(user_id, order_id)
    
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('order_history'))
    
    # Get tracking information from the Order Payment Service
    tracking_info = get_tracking_info(order_id, user_id)
    
    return render_template('track_order.html', order=order, tracking_info=tracking_info)

@app.route('/products')
def products():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    filtered_products = PRODUCTS
    if category:
        filtered_products = [p for p in filtered_products if p['category'].lower() == category.lower()]
    if search:
        filtered_products = [p for p in filtered_products if search.lower() in p['name'].lower() or search.lower() in p['description'].lower()]
    
    categories = list(set(p['category'] for p in PRODUCTS))
    return render_template('products.html', products=filtered_products, categories=categories)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    related_products = [p for p in PRODUCTS if p['id'] in product.get('related_ids', [])]
    return render_template("product_detail.html", product=product, related_products=related_products)
    #return render_template('product_detail.html', product=product)

@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    cart_products = []
    total = 0
    
    for item_id in cart_items:
        product = next((p for p in PRODUCTS if p['id'] == item_id), None)
        if product:
            cart_products.append(product)
            total += product['price']
    
    return render_template('cart.html', cart_products=cart_products, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    
    session['cart'].append(product_id)
    session.modified = True
    
    flash('Item added to cart!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' in session and product_id in session['cart']:
        session['cart'].remove(product_id)
        session.modified = True
        flash('Item removed from cart', 'success')
    return redirect(url_for('cart'))
@app.route('/api/wishlist/<item_id>', methods=['DELETE'])
@login_required
def remove_from_wishlist(item_id):
    try:
        user_id = session.get('user_id')
        print(f"Attempting to remove wishlist item: {item_id} for user: {user_id}")
        
        # Fetch the wishlist item
        wishlist_item = WishlistItem.query.get(item_id)
        
        # Debug information
        if wishlist_item:
            print(f"Found wishlist item - ID: {wishlist_item.id}, User ID: {wishlist_item.user_id}")
        else:
            print(f"No wishlist item found with ID: {item_id}")
            return jsonify({'message': 'Item not found'}), 404
        
        # Ensure user can only delete their own wishlist items
        if str(wishlist_item.user_id) != str(user_id):
            print(f"Unauthorized: Item belongs to user {wishlist_item.user_id}, not {user_id}")
            return jsonify({'message': 'Unauthorized - you can only remove your own wishlist items'}), 403
        
        # Delete the item
        db.session.delete(wishlist_item)
        db.session.commit()
        
        print(f"Successfully removed wishlist item {item_id}")
        return jsonify({'message': 'Item removed from wishlist'}), 200
        
    except Exception as e:
        # Log the full error
        print(f"Error removing wishlist item: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f'Error removing item: {str(e)}'}), 500

@app.route('/checkout')
@login_required
def checkout():
    cart_items = session.get('cart', [])
    cart_products = []
    total = 0
    
    for item_id in cart_items:
        product = next((p for p in PRODUCTS if p['id'] == item_id), None)
        if product:
            cart_products.append(product)
            total += product['price']
    
    return render_template('checkout.html', cart_products=cart_products, total=total)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    cart_items = session.get('cart', [])
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    # Get cart products and calculate total
    cart_products = []
    total = 0
    
    for item_id in cart_items:
        product = next((p for p in PRODUCTS if p['id'] == item_id), None)
        if product:
            cart_products.append(product)
            total += product['price']
    
    # Get shipping and payment info from form
    shipping_address = f"{request.form.get('address')}, {request.form.get('city')}, {request.form.get('state')} {request.form.get('zip')}"
    payment_method = request.form.get('payment_method')
    
    # Generate a mock order ID
    order_id = f"ORD-{int(time.time())}-{user_id}"
    
    # Create order items list for storage and notification
    order_items = []
    product_names = []
    
    for product in cart_products:
        order_items.append({
            "id": product['id'],
            "name": product['name'],
            "price": product['price'],
            "quantity": 1  # Assuming quantity is 1 for simplicity
        })
        product_names.append(product['name'])
    
    # Format items for notification service
    notification_items = []
    for product in cart_products:
        notification_items.append({
            "product_name": product['name'],
            "quantity": 1,
            "price": product['price'],
            "subtotal": product['price']
        })
    
    # Calculate subtotal, tax, shipping cost
    subtotal = total - 5.99 - (total * 0.08)
    shipping_cost = 5.99
    tax = total * 0.08
    
    # Create new order
    new_order = {
        "id": order_id,
        "user_id": user_id,
        "date": datetime.now().strftime('%B %d, %Y'),
        "total": total,
        "status": "Processing",
        "items": order_items,
        "shipping_address": shipping_address,
        "payment_method": payment_method
    }
    
    # Add to our temporary orders list
    ORDERS.append(new_order)
    
    # Prepare notification data
    notification_data = {
        'type': 'order_placed',
        'subject': f'Order Confirmation #{order_id}',
        'order_id': order_id,
        'total_amount': total,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'status': 'pending',
        'customer_name': session.get('user_name', 'Valued Customer'),
        'customer_email': user_email,
        'shipping_address': shipping_address,
        'payment_method': payment_method,
        'items': notification_items,
        'account_url': request.host_url + 'profile',
        'unsubscribe_url': request.host_url + 'preferences',
        'shop_url': request.host_url + 'products'
    }
    
    # Send notification via microservice
    notification_sent = send_notification(
        user_id=user_id,
        email=user_email,
        notification_type='order_placed',
        data=notification_data
    )
    
    if notification_sent:
        print("Notification sent successfully")
    else:
        print("Failed to send notification")
    
    # Clear the cart
    session['cart'] = []
    
    flash('Order placed successfully! Check your email for confirmation.', 'success')
    return redirect(url_for('order_history'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        login_type = request.form.get('login_type', 'password')
        
        if login_type == 'password':
            # Get user from database
            user = get_user_by_email(email)
            
            # Print debug info
            print(f"Login attempt for email: {email}")
            print(f"User found: {user is not None}")
            
            # Check if user exists and password matches
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['user_email'] = user.email
                flash('Logged in successfully', 'success')
                return redirect(url_for('index'))
            else:
                if user:
                    print("Password check failed")
                flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

# Order-related functions

def get_user_orders(user_id):
    """
    Fetch all orders for a specific user.
    In a real application, this would call your Order Service API.
    """
    try:
        # Filter orders for this user
        user_orders = [order for order in ORDERS if str(order.get("user_id")) == str(user_id)]
        
        # For now, add mock data
        mock_orders = [
            {
                "id": "ORD-1682506789-1",
                "user_id": user_id,
                "date": "May 1, 2025",
                "total": 299.97,
                "status": "Delivered",
                "items": [
                    {"id": 1, "name": "Wireless Headphones", "price": 129.99, "quantity": 1},
                    {"id": 5, "name": "Bluetooth Speaker", "price": 79.99, "quantity": 1},
                    {"id": 11, "name": "Bluetooth Speaker Mini", "price": 59.99, "quantity": 1}
                ],
                "shipping_address": "123 Main St, Anytown, AN 12345"
            },
            {
                "id": "ORD-1679828389-1",
                "user_id": user_id,
                "date": "April 15, 2025",
                "total": 1349.98,
                "status": "Processing",
                "items": [
                    {"id": 2, "name": "Smartphone", "price": 699.99, "quantity": 1},
                    {"id": 3, "name": "Laptop", "price": 999.99, "quantity": 1},
                    {"id": 12, "name": "Tablet Pro", "price": 399.99, "quantity": 1}
                ],
                "shipping_address": "123 Main St, Anytown, AN 12345"
            },
            {
                "id": "ORD-1677236388-1",
                "user_id": user_id,
                "date": "March 10, 2025",
                "total": 499.98,
                "status": "Shipped",
                "items": [
                    {"id": 4, "name": "Smartwatch", "price": 249.99, "quantity": 1},
                    {"id": 6, "name": "Tablet", "price": 349.99, "quantity": 1}
                ],
                "shipping_address": "123 Main St, Anytown, AN 12345"
            }
        ]
        
        # Return both real orders and mock data
        return user_orders + mock_orders
    except Exception as e:
        print(f"Error getting user orders: {str(e)}")
        return []

def get_order_details(user_id, order_id):
    """
    Fetch details for a specific order.
    In a real application, this would call your Order Service API.
    """
    try:
        # Get all orders and find the specific one
        orders = get_user_orders(user_id)
        return next((order for order in orders if str(order["id"]) == str(order_id)), None)
    except Exception as e:
        print(f"Error getting order details: {str(e)}")
        return None

def get_tracking_info(order_id, user_id):
    """
    Fetch tracking information for a specific order.
    In a real application, this would call your Shipping/Order Service API.
    """
    try:
        # In production, replace with actual API call
        # Example: response = requests.get(f"{SHIPPING_SERVICE_URL}/api/tracking/{order_id}")
        
        # For now, generate mock tracking data based on the order status
        order = get_order_details(user_id, order_id)
        if not order:
            return None
        
        status = order["status"]
        tracking_number = f"TRK{order_id.replace('ORD-', '')}"
        
        # Generate tracking updates based on status
        if status == "Delivered":
            updates = [
                {"status": "Order Placed", "date": "May 1, 2025", "time": "9:30 AM", "location": "Online"},
                {"status": "Processing", "date": "May 1, 2025", "time": "2:15 PM", "location": "Distribution Center"},
                {"status": "Shipped", "date": "May 2, 2025", "time": "10:45 AM", "location": "Shipping Facility"},
                {"status": "In Transit", "date": "May 3, 2025", "time": "8:20 AM", "location": "Transit Hub"},
                {"status": "Out for Delivery", "date": "May 4, 2025", "time": "7:30 AM", "location": "Local Delivery"},
                {"status": "Delivered", "date": "May 4, 2025", "time": "3:45 PM", "location": "Your Address"}
            ]
            estimated_delivery = "Delivered on May 4, 2025"
        elif status == "Shipped":
            updates = [
                {"status": "Order Placed", "date": "May 1, 2025", "time": "9:30 AM", "location": "Online"},
                {"status": "Processing", "date": "May 1, 2025", "time": "2:15 PM", "location": "Distribution Center"},
                {"status": "Shipped", "date": "May 2, 2025", "time": "10:45 AM", "location": "Shipping Facility"},
                {"status": "In Transit", "date": "May 3, 2025", "time": "8:20 AM", "location": "Transit Hub"}
            ]
            estimated_delivery = "May 5, 2025"
        else:  # Processing or other statuses
            updates = [
                {"status": "Order Placed", "date": "May 1, 2025", "time": "9:30 AM", "location": "Online"},
                {"status": "Processing", "date": "May 1, 2025", "time": "2:15 PM", "location": "Distribution Center"}
            ]
            estimated_delivery = "May 6, 2025"
        
        return {
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": "ElectroCart Express",
            "status": status,
            "estimated_delivery": estimated_delivery,
            "updates": updates,
            "shipping_address": order.get("shipping_address", "123 Main St, Anytown, AN 12345")
        }
    except Exception as e:
        print(f"Error getting tracking info: {str(e)}")
        return None
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        
        # Password validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        try:
            user = create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Send registration notification
            notification_data = {
                'subject': 'Welcome to ShopEasy',
                'user_name': first_name,
                'email': email
            }
            
            # Send through notification service
            send_notification(
                user_id=str(user.id),
                email=email,
                notification_type='registration',
                data=notification_data
            )
            
            # Update notification preferences
            update_notification_preferences(str(user.id), email, first_name)
            
            flash('Registration successful! Please check your email for confirmation.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
    
    return render_template('register.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

def update_notification_preferences(user_id, email, name):
    """
    Set user notification preferences in the notification service
    """
    try:
        notification_service_url = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://localhost:5004/api/notifications/preferences')
        
        # Create the preferences payload
        payload = {
            'user_id': user_id,
            'email_notifications': True,
            'app_notifications': True,
            'email': email,
            'name': name
        }
        
        # Create a JWT token for the new user
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, app.secret_key, algorithm="HS256")
        
        response = requests.put(
            notification_service_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            },
            data=json.dumps(payload),
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"Notification preferences set for user {user_id}")
            return True
        else:
            print(f"Failed to set notification preferences: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error setting notification preferences: {str(e)}")
        return False
    
def send_notification(user_id, email, notification_type, data):
    """
    Send notification via the notification microservice
    """
    try:
        # Check if we're running inside Docker or locally
        if os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true':
            # Use Docker service name when running inside Docker
            notification_service_url = 'http://notification_service:5004/api/notifications'
        else:
            # Use localhost when running outside Docker
            notification_service_url = 'http://localhost:5004/api/notifications'
        
        print(f"Sending notification to: {notification_service_url}")
        
        # Create the notification payload
        payload = {
            'user_id': user_id,
            'type': notification_type,
            'data': data,
            'customer_email': email
        }
        
        # For debugging
        print(f"Notification payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            notification_service_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload),
            timeout=10,
            verify=False  # Only for development
        )
        
        print(f"Notification response: {response.status_code} - {response.text}")
        
        if response.status_code == 201:
            print(f"Notification sent successfully to {email}")
            return True
        else:
            print(f"Failed to send notification: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return False

def get_notification_service_url():
    """
    Determine the notification service URL based on environment
    Try different possibilities and use the first one that works
    """
    possible_urls = [
        "http://notification_service:5004/api/notifications",
        "http://localhost:5004/api/notifications",
        "http://127.0.0.1:5004/api/notifications"
    ]
    
    for url in possible_urls:
        try:
            # Try to connect with a short timeout
            response = requests.get(url.replace("/api/notifications", "/health"), timeout=0.5)
            if response.status_code == 200:
                print(f"Successfully connected to notification service at {url}")
                return url
        except:
            # If connection fails, try the next URL
            continue
    
    # Default to localhost if none of the URLs work
    print("Could not verify notification service URL, defaulting to localhost")
    return "http://localhost:5004/api/notifications"

@app.route('/test-notification')
def test_notification():
    try:
        user_id = "123"
        email = "manyashreevangimalla@gmail.com"
        
        notification_data = {
            'type': 'order_placed',
            'subject': 'Test Order Confirmation',
            'order_id': 'TEST-123',
            'total_amount': 99.99,
            'subtotal': 89.99,
            'shipping_cost': 5.99,
            'tax': 4.01,
            'status': 'pending',
            'customer_name': 'Test User',
            'customer_email': email,
            'shipping_address': '123 Test St, Test City, TS 12345',
            'payment_method': 'Credit Card',
            'items': [
                {
                    "product_name": "Test Product",
                    "quantity": 1,
                    "price": 89.99,
                    "subtotal": 89.99
                }
            ],
            'account_url': 'http://localhost:8080/profile',
            'unsubscribe_url': 'http://localhost:8080/preferences',
            'shop_url': 'http://localhost:8080/products'
        }
        
        result = send_notification(
            user_id=user_id,
            email=email,
            notification_type='order_placed',
            data=notification_data
        )
        
        if result:
            return "Test notification sent successfully! Check your email."
        else:
            return "Failed to send test notification. Check server logs."
    
    except Exception as e:
        return f"Error: {str(e)}"
@app.route('/profile')
@login_required
def profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # This would interact with your Order & Payment Service
    orders = [
        {'id': 1, 'date': '2025-04-01', 'total': 129.99, 'status': 'Delivered'},
        {'id': 2, 'date': '2025-03-15', 'total': 349.99, 'status': 'Processing'}
    ]
    
    return render_template('profile.html', user=user.to_dict(), orders=orders)

@app.route('/send_verification_code', methods=['POST'])
def send_verification_code():
    email = request.form.get('email')
    
    if not email:
        flash('Email address is required', 'danger')
        return redirect(url_for('login'))
    
    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        # Clear message and show a specific "not registered" message
        flash('This email is not registered. Please create an account first.', 'danger')
        # Add JavaScript to show a confirmation dialog after page loads
        return """
        <script>
            if (confirm('This email is not registered. Would you like to create an account?')) {
                window.location.href = '""" + url_for('register') + """';
            } else {
                window.location.href = '""" + url_for('login') + """';
            }
        </script>
        """
    
    # Generate verification code
    code = generate_verification_code()
    print(f"Generated verification code: {code} for {email}")
    
    # Store code in session or database (with expiration)
    session['verification_code'] = code
    session['verification_email'] = email
    session['code_expiration'] = (datetime.now() + timedelta(minutes=10)).timestamp()
    
    # Your verified sender email
    from_email = "your-verified-sender@yourdomain.com"  # REPLACE with your verified email
    
    message = Mail(
        from_email=from_email,
        to_emails=email,
        subject='ElectroCart Verification Code',
        html_content=f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>ElectroCart Verification Code</h2>
            <p>Your verification code is:</p>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold;">
                {code}
            </div>
            <p>This code will expire in 10 minutes.</p>
            <p>If you did not request this code, please ignore this email.</p>
        </div>
        '''
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        # Disable SSL verification for this session
        sg.client.session.verify = False
        
        print("Sending email via SendGrid...")
        response = sg.send(message)
        
        print(f"SendGrid response status code: {response.status_code}")
        
        if response.status_code >= 200 and response.status_code < 300:
            flash('Verification code sent to your email. Please check your inbox and spam folder.', 'success')
        else:
            flash(f'Error from SendGrid: Status code {response.status_code}', 'danger')
            
        return redirect(url_for('login', tab='verification'))
        
    except Exception as e:
        error_message = str(e)
        print(f"Error sending email via SendGrid: {error_message}")
        flash(f'Error sending verification code: {error_message}', 'danger')
        return redirect(url_for('login'))

@app.route('/resend_verification_code', methods=['POST'])
def resend_verification_code():
    email = request.form.get('email') or session.get('verification_email')
    
    if not email:
        flash('Email address not found. Please start the login process again.', 'danger')
        return redirect(url_for('login'))
    
    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        flash('Email not registered. Please create an account first.', 'danger')
        return redirect(url_for('register'))
    
    # Generate new verification code
    code = generate_verification_code()
    print(f"Generated new verification code: {code} for {email}")
    
    # Update session with new code
    session['verification_code'] = code
    session['verification_email'] = email
    session['code_expiration'] = (datetime.now() + timedelta(minutes=10)).timestamp()
    
    # Your verified sender email
    from_email = "your-verified-sender@yourdomain.com"  # REPLACE with your verified email
    
    message = Mail(
        from_email=from_email,
        to_emails=email,
        subject='ElectroCart New Verification Code',
        html_content=f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>ElectroCart Verification Code</h2>
            <p>Your new verification code is:</p>
            <div style="background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold;">
                {code}
            </div>
            <p>This code will expire in 10 minutes.</p>
            <p>If you did not request this code, please ignore this email.</p>
        </div>
        '''
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        # Disable SSL verification for this session
        sg.client.session.verify = False
        
        print("Resending email via SendGrid...")
        response = sg.send(message)
        
        print(f"SendGrid response status code: {response.status_code}")
        
        if response.status_code >= 200 and response.status_code < 300:
            flash('New verification code sent to your email. Please check your inbox and spam folder.', 'success')
        else:
            flash(f'Error from SendGrid: Status code {response.status_code}', 'danger')
            
        return redirect(url_for('login', tab='verification'))
        
    except Exception as e:
        error_message = str(e)
        print(f"Error sending email via SendGrid: {error_message}")
        flash(f'Error sending verification code: {error_message}', 'danger')
        return redirect(url_for('login'))
    
@app.route('/verify_code', methods=['POST'])
def verify_code():
    # Get the verification code from the form
    entered_code = request.form.get('code')
    email = session.get('verification_email')
    
    stored_code = session.get('verification_code')
    expiration = session.get('code_expiration')
    
    # Check if code is valid and not expired
    if not stored_code or not email or not expiration:
        flash('Session expired, please try again', 'danger')
        return redirect(url_for('login'))
    
    if datetime.now().timestamp() > expiration:
        flash('Verification code expired, please request a new one', 'danger')
        return redirect(url_for('login', tab='verification'))
    
    if entered_code != stored_code:
        flash('Invalid verification code', 'danger')
        return redirect(url_for('login', tab='verification'))
    
    # Code is valid, log in the user
    user = get_user_by_email(email)
    if user:
        session['user_id'] = user.id
        session['user_email'] = user.email
        
        # Clean up session variables
        session.pop('verification_code', None)
        session.pop('verification_email', None)
        session.pop('code_expiration', None)
        
        flash('Logged in successfully', 'success')
        return redirect(url_for('index'))
    else:
        flash('User not found', 'danger')
        return redirect(url_for('login'))
@app.route('/clear_verification_session', methods=['POST'])
def clear_verification_session():
    """Clear verification related session data"""
    session.pop('verification_code', None)
    session.pop('verification_email', None)
    session.pop('code_expiration', None)
    return jsonify({'success': True})
# Setup database tables
with app.app_context():
    db.create_all()  # Create database tables if they don't exist

if __name__ == '__main__':
    app.run(debug=True)