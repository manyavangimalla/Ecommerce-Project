from flask import Flask, request, jsonify
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
import datetime
import requests
import jwt
from functools import wraps
import redis
from routes.products import products_blueprint
from routes.categories import categories_blueprint
from routes.inventory import inventory_blueprint

app = Flask(__name__)

# Get individual database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

# Use Kubernetes DNS for service discovery
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

# Middleware to log all incoming requests
@app.before_request
def log_request():
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}")

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

# Register blueprints
app.register_blueprint(products_blueprint, url_prefix='/api/products')
app.register_blueprint(categories_blueprint, url_prefix='/api/categories')
app.register_blueprint(inventory_blueprint, url_prefix='/api/inventory')

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
            
    app.run(host='0.0.0.0', port=8080, debug=True)