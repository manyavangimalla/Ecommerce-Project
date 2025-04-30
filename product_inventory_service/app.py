from flask import Flask, request, jsonify
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
import datetime
import requests
import jwt
from functools import wraps
import redis

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
# Get JWT secret key from environment
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'dev_secret_key')

db = SQLAlchemy(app)

# Redis connection for caching
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# Models
class Category(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

class Product(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.String(36), db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    category = db.relationship('Category', backref=db.backref('products', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'category': self.category.name,
            'category_id': self.category_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
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

# Admin middleware
def admin_required(f):
    @wraps(f)
    def decorated(current_user_id, *args, **kwargs):
        # In a real app, you would check if the user is an admin
        # For now, we'll just pass it through
        return f(current_user_id, *args, **kwargs)
    
    return decorated

# Routes
@app.route('/api/products', methods=['GET'])
def get_products():
    # Get query parameters
    category = request.args.get('category')
    search = request.args.get('search')
    sort = request.args.get('sort', 'name')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Try to get from cache first
    cache_key = f"products:{category or ''}:{search or ''}:{sort}:{page}:{per_page}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return jsonify(eval(cached_result)), 200
    
    # If not in cache, query database
    query = Product.query
    
    if category:
        category_obj = Category.query.filter_by(name=category).first()
        if category_obj:
            query = query.filter_by(category_id=category_obj.id)
    
    if search:
        search = f"%{search}%"
        query = query.filter(Product.name.ilike(search) | Product.description.ilike(search))
    
    # Apply sorting
    if sort == 'price_low':
        query = query.order_by(Product.price)
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'newest':
        query = query.order_by(Product.created_at.desc())
    else:  # default to name
        query = query.order_by(Product.name)
    
    # Apply pagination
    products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [product.to_dict() for product in products.items],
        'total': products.total,
        'pages': products.pages,
        'page': page
    }
    
    # Cache the result for 5 minutes
    redis_client.setex(cache_key, 300, str(result))
    
    return jsonify(result), 200

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    # Try to get from cache first
    cache_key = f"product:{product_id}"
    cached_product = redis_client.get(cache_key)
    
    if cached_product:
        return jsonify(eval(cached_product)), 200
    
    # If not in cache, query database
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    result = product.to_dict()
    
    # Cache the result for 5 minutes
    redis_client.setex(cache_key, 300, str(result))
    
    return jsonify(result), 200

@app.route('/api/categories', methods=['GET'])
def get_categories():
    # Try to get from cache first
    cache_key = "categories"
    cached_categories = redis_client.get(cache_key)
    
    if cached_categories:
        return jsonify(eval(cached_categories)), 200
    
    # If not in cache, query database
    categories = Category.query.all()
    result = [category.to_dict() for category in categories]
    
    # Cache the result for 10 minutes
    redis_client.setex(cache_key, 600, str(result))
    
    return jsonify(result), 200

@app.route('/api/products', methods=['POST'])
@token_required
@admin_required
def create_product(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('price') or not data.get('category_id'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if category exists
    category = Category.query.get(data['category_id'])
    if not category:
        return jsonify({'message': 'Category not found'}), 404
    
    # Create new product
    new_product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=float(data['price']),
        stock=int(data.get('stock', 0)),
        category_id=data['category_id']
    )
    
    db.session.add(new_product)
    db.session.commit()
    
    # Invalidate cache
    for key in redis_client.keys("products:*"):
        redis_client.delete(key)
    
    return jsonify(new_product.to_dict()), 201

@app.route('/api/products/<product_id>', methods=['PUT'])
@token_required
@admin_required
def update_product(current_user_id, product_id):
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    data = request.get_json()
    
    if data.get('name'):
        product.name = data['name']
    if data.get('description') is not None:
        product.description = data['description']
    if data.get('price'):
        product.price = float(data['price'])
    if data.get('stock') is not None:
        product.stock = int(data['stock'])
    if data.get('category_id'):
        # Check if category exists
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({'message': 'Category not found'}), 404
        product.category_id = data['category_id']
    
    db.session.commit()
    
    # Invalidate cache
    redis_client.delete(f"product:{product_id}")
    for key in redis_client.keys("products:*"):
        redis_client.delete(key)
    
    return jsonify(product.to_dict()), 200

@app.route('/api/products/<product_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_product(current_user_id, product_id):
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    db.session.delete(product)
    db.session.commit()
    
    # Invalidate cache
    redis_client.delete(f"product:{product_id}")
    for key in redis_client.keys("products:*"):
        redis_client.delete(key)
    
    return jsonify({'message': 'Product deleted'}), 200

@app.route('/api/categories', methods=['POST'])
@token_required
@admin_required
def create_category(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if category already exists
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'message': 'Category already exists'}), 409
    
    # Create new category
    new_category = Category(name=data['name'])
    
    db.session.add(new_category)
    db.session.commit()
    
    # Invalidate cache
    redis_client.delete("categories")
    
    return jsonify(new_category.to_dict()), 201

@app.route('/api/inventory/check', methods=['POST'])
def check_inventory():
    data = request.get_json()
    
    if not data or not data.get('items'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    items = data['items']
    result = []
    
    for item in items:
        product_id = item.get('product_id')
        quantity = item.get('quantity', 1)
        
        product = Product.query.get(product_id)
        
        if not product:
            result.append({
                'product_id': product_id,
                'available': False,
                'message': 'Product not found'
            })
        elif product.stock < quantity:
            result.append({
                'product_id': product_id,
                'available': False,
                'message': f'Insufficient stock. Available: {product.stock}'
            })
        else:
            result.append({
                'product_id': product_id,
                'available': True,
                'message': 'In stock'
            })
    
    return jsonify(result), 200

@app.route('/api/inventory/update', methods=['POST'])
@token_required
def update_inventory(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('items'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    items = data['items']
    success = True
    message = 'Inventory updated successfully'
    
    for item in items:
        product_id = item.get('product_id')
        quantity = item.get('quantity', 0)
        operation = item.get('operation', 'decrease')
        
        product = Product.query.get(product_id)
        
        if not product:
            success = False
            message = f'Product {product_id} not found'
            break
        
        if operation == 'decrease':
            if product.stock < quantity:
                success = False
                message = f'Insufficient stock for product {product.name}'
                break
            product.stock -= quantity
        else:  # increase
            product.stock += quantity
    
    if success:
        db.session.commit()
        
        # Invalidate cache
        for product_id in [item.get('product_id') for item in items]:
            redis_client.delete(f"product:{product_id}")
        for key in redis_client.keys("products:*"):
            redis_client.delete(key)
    else:
        db.session.rollback()
    
    return jsonify({'success': success, 'message': message}), 200 if success else 400

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    print("\n\n\nShubhammm \n\n\n")
    print(f"\n\nConnecting to database at {DATABASE_URL}")
    with app.app_context():
        db.create_all()
        
        # Add initial categories if none exist
        if not Category.query.first():
            categories = ['Electronics', 'Clothing', 'Home & Kitchen', 'Books', 'Toys']
            for category_name in categories:
                db.session.add(Category(name=category_name))
            db.session.commit()
            
        # Add initial products if none exist
        if not Product.query.first():
            electronics = Category.query.filter_by(name='Electronics').first()
            
            products = [
                {
                    'name': 'Wireless Headphones',
                    'description': 'High-quality wireless headphones with noise cancellation',
                    'price': 129.99,
                    'stock': 50,
                    'category_id': electronics.id
                },
                {
                    'name': 'Smartphone',
                    'description': 'Latest model with advanced camera and long battery life',
                    'price': 699.99,
                    'stock': 30,
                    'category_id': electronics.id
                },
                {
                    'name': 'Laptop',
                    'description': 'Lightweight laptop with powerful processor and ample storage',
                    'price': 999.99,
                    'stock': 20,
                    'category_id': electronics.id
                },
                {
                    'name': 'Smartwatch',
                    'description': 'Track your fitness and stay connected with this smartwatch',
                    'price': 249.99,
                    'stock': 40,
                    'category_id': electronics.id
                }
            ]
            
            for product_data in products:
                db.session.add(Product(**product_data))
            db.session.commit()
            
    app.run(host='0.0.0.0', port=5002, debug=True)