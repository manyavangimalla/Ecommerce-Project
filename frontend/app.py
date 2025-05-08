from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import os
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')

# Middleware to log all incoming requests
@app.before_request
def log_request():
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}")

@app.context_processor
def inject_api_url():
    return {'API_URL': os.environ.get('API_URL', 'http://localhost:5000')}

# Mock data - In production this would come from your microservices
PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 129.99, "description": "High-quality wireless headphones with noise cancellation", "stock": 50, "category": "Electronics", "image": "/static/images/headphones.jpg"},
    {"id": 2, "name": "Smartphone", "price": 699.99, "description": "Latest model with advanced camera and long battery life", "stock": 30, "category": "Electronics", "image": "/static/images/smartphone.jpg"},
    {"id": 3, "name": "Laptop", "price": 999.99, "description": "Lightweight laptop with powerful processor and ample storage", "stock": 20, "category": "Electronics", "image": "/static/images/laptop.jpg"},
    {"id": 4, "name": "Smartwatch", "price": 249.99, "description": "Track your fitness and stay connected with this smartwatch", "stock": 40, "category": "Wearables", "image": "/static/images/smartwatch.jpg"},
    {"id": 5, "name": "Bluetooth Speaker", "price": 79.99, "description": "Portable speaker with amazing sound quality", "stock": 60, "category": "Audio", "image": "/static/images/speaker.jpg"},
    {"id": 6, "name": "Tablet", "price": 349.99, "description": "Perfect for work and entertainment on the go", "stock": 25, "category": "Electronics", "image": "/static/images/tablet.jpg"},
]

# Helper function to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    featured_products = PRODUCTS[:4]  # Just get first 4 for featured section
    return render_template('index.html', featured_products=featured_products)

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
    return render_template('product_detail.html', product=product)

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
    try:
        # Collect cart items from the session
        cart_items = session.get('cart', [])
        if not cart_items:
            flash('Your cart is empty. Please add items before placing an order.', 'warning')
            return redirect(url_for('cart'))

        # Prepare order data
        items = []
        for item_id in cart_items:
            product = next((p for p in PRODUCTS if p['id'] == item_id), None)
            if product:
                items.append({
                    'product_id': str(product['id']),  # Convert to string to match the expected format
                    'product_name': product['name'],
                    'price': product['price'],
                    'quantity': 1
                })

        order_data = {
            'items': items,
            'shipping_address': request.form.get('shipping_address'),
            'payment_method': request.form.get('payment_method')
        }

        # Send order data to the Order Payment Service via the API Gateway
        response = requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/orders",
            json=order_data,
            headers={'Authorization': f"Bearer {session.get('user_token')}"}
        )

        if response.status_code == 201:
            session['cart'] = []  # Clear the cart after successful order placement
            flash('Order placed successfully!', 'success')
            return redirect(url_for('index'))
        else:
            error_message = response.json().get('message', 'Failed to place order. Please try again.')
            flash(error_message, 'error')
    except requests.exceptions.RequestException as e:
        flash('An error occurred while connecting to the server. Please try again later.', 'error')

    return redirect(url_for('cart'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Collect form data
        login_data = {
            'email': request.form.get('email'),
            'password': request.form.get('password')
        }

        # Send data to the User Auth Service via the API Gateway
        try:
            response = requests.post(f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/auth/login", json=login_data)
            if response.status_code == 200:
                user_data = response.json()
                session['user_id'] = user_data['user']['id']
                session['user_email'] = user_data['user']['email']
                session['user_token'] = user_data['token']
                flash('Logged in successfully', 'success')
                return redirect(url_for('index'))
            else:
                error_message = response.json().get('message', 'Login failed. Please try again.')
                flash(error_message, 'error')
        except requests.exceptions.RequestException as e:
            flash('An error occurred while connecting to the server. Please try again later.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Collect form data
        user_data = {
            'first_name': request.form.get('firstName'),
            'last_name': request.form.get('lastName'),
            'email': request.form.get('email'),
            'password': request.form.get('password')
        }

        print("\n\n\nShubham Register endpoint hit 222")
        

        # Send data to the User Auth Service via the API Gateway
        try:
            print("\n\n\nShubham Register endpoint hit 333", flush=True)
            print(f'API_URL: {os.environ.get("API_URL")}', flush=True)
            api_url = os.environ.get("API_URL")
            response = requests.post(f"{api_url}/api/auth/register", json=user_data)
            print("\n\n\nShubham Register endpoint hit 444", flush=True)
            if response.status_code == 201:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                error_message = response.json().get('message', 'Registration failed. Please try again.')
                print(f"\n\nShubham Error during registration 1: {error_message}", flush=True)
                flash(error_message, 'error')
        except requests.exceptions.RequestException as e:
            print(f"\n\nShubham Error during registration 2: {str(e)}", flush=True)
            flash('An error occurred while connecting to the server. Please try again later.', 'error')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    try:
        # Fetch user profile from the User Auth Service
        user_response = requests.get(f"{os.environ.get('API_URL')}/api/users/me", headers={'Authorization': f"Bearer {session.get('user_token')}"})
        user_response.raise_for_status()
        user = user_response.json()

        # Fetch user orders from the Order Payment Service
        orders_response = requests.get(f"{os.environ.get('API_URL')}/api/orders", headers={'Authorization': f"Bearer {session.get('user_token')}"})
        orders_response.raise_for_status()
        orders = orders_response.json().get('items', [])

        # Fetch notification preferences
        try:
            pref_response = requests.get(f"{os.environ.get('API_URL')}/api/notifications/preferences", headers={'Authorization': f"Bearer {session.get('user_token')}"})
            pref_response.raise_for_status()
            preferences = pref_response.json() or {}
        except Exception:
            flash('Could not load notification preferences.', 'warning')
            preferences = {}

        # Ensure all expected keys exist
        preferences = {
            'email_notifications': preferences.get('email_notifications', False),
            'sms_notifications': preferences.get('sms_notifications', False),
            'app_notifications': preferences.get('app_notifications', True),
            'email': preferences.get('email', user.get('email', '')),
            'phone': preferences.get('phone', '')
        }

        return render_template('profile.html', user=user, orders=orders, preferences=preferences)
    except requests.exceptions.RequestException as e:
        flash('Failed to load profile. Please try again later.', 'error')
        return redirect(url_for('index'))

@app.route('/update_notification_preferences', methods=['POST'])
@login_required
def update_notification_preferences():
    data = {
        'email_notifications': bool(request.form.get('email_notifications')),
        'sms_notifications': bool(request.form.get('sms_notifications')),
        'app_notifications': bool(request.form.get('app_notifications')),
        'email': request.form.get('email'),
        'phone': request.form.get('phone')
    }
    try:
        response = requests.put(
            f"{os.environ.get('API_URL')}/api/notifications/preferences",
            headers={'Authorization': f"Bearer {session.get('user_token')}"},
            json=data
        )
        response.raise_for_status()
        flash('Notification preferences updated!', 'success')
    except requests.exceptions.RequestException:
        flash('Failed to update notification preferences.', 'error')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    print("\n\nShubham Starting frontend app...")
    app.run(host='0.0.0.0', port=8080, debug=True)