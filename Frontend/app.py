import string
import random
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
from functools import wraps
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
