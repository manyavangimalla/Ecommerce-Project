from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import os
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')

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
        
        # In production, validate against User & Auth Service
        if email == 'user@example.com' and password == 'password':
            session['user_id'] = 1
            session['user_email'] = email
            flash('Logged in successfully', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # This would interact with your User & Auth Service
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    # This would interact with your User & Auth Service
    user = {
        'id': session['user_id'],
        'email': session['user_email'],
        'name': 'Sample User',
        'address': '123 Main St, Anytown, USA'
    }
    
    # This would interact with your Order & Payment Service
    orders = [
        {'id': 1, 'date': '2025-04-01', 'total': 129.99, 'status': 'Delivered'},
        {'id': 2, 'date': '2025-03-15', 'total': 349.99, 'status': 'Processing'}
    ]
    
    return render_template('profile.html', user=user, orders=orders)

if __name__ == '__main__':
    app.run(debug=True)