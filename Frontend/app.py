from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import os
import json
from functools import wraps
from db import db, get_user_by_email, create_user, User

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

@app.route('/request_verification_code', methods=['POST'])
def request_verification_code():
    # Get email from request
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    # Verify user exists in database
    user = get_user_by_email(email)
    if not user:
        return jsonify({'success': False, 'message': 'No account found with this email'})
    
    try:
        # Generate a 6-digit verification code
        verification_code = str(random.randint(100000, 999999))
        
        # Store the code with expiration time (10 minutes from now)
        expiration_time = datetime.now() + timedelta(minutes=10)
        VERIFICATION_CODES[email] = {
            'code': verification_code,
            'expires': expiration_time
        }
        
        # In a production app, send email with SendGrid
        # send_verification_email(email, verification_code)
        
        # For testing purposes, print the code to console
        print(f"Verification code for {email}: {verification_code}")
        
        return jsonify({'success': True, 'message': 'Verification code sent successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/verify_code', methods=['POST'])
def verify_code():
    email = request.form.get('email')
    verification_code = request.form.get('verification_code')
    
    if not email or not verification_code:
        flash('Email and verification code are required', 'error')
        return redirect(url_for('login'))
    
    # Check if the code exists and is valid
    stored_data = VERIFICATION_CODES.get(email)
    if not stored_data:
        flash('No verification code found for this email', 'error')
        return redirect(url_for('login'))
    
    # Check if code is expired
    if datetime.now() > stored_data['expires']:
        # Remove expired code
        del VERIFICATION_CODES[email]
        flash('Verification code has expired. Please request a new one', 'error')
        return redirect(url_for('login'))
    
    # Check if code matches
    if verification_code != stored_data['code']:
        flash('Invalid verification code', 'error')
        return redirect(url_for('login'))
    
    # Code is valid, log the user in
    user = get_user_by_email(email)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # Set session variables
    session['user_id'] = user.id
    session['user_email'] = user.email
    
    # Remove the used code
    del VERIFICATION_CODES[email]
    
    flash('Logged in successfully', 'success')
    return redirect(url_for('index'))

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
    # This would interact with your Order & Payment Service
    # For now, just clear the cart and show success
    session['cart'] = []
    flash('Order placed successfully!', 'success')
    return redirect(url_for('index'))

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        address = request.form.get('address', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        zip_code = request.form.get('zip_code', '')
        
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
                last_name=last_name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code
            )
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

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

# Setup database tables
with app.app_context():
    db.create_all()  # Create database tables if they don't exist

if __name__ == '__main__':
    app.run(debug=True)
