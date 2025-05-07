from flask import Flask, request, jsonify
import os
import jwt
import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from functools import wraps
from routes.auth import auth_blueprint
from routes.users import users_blueprint
from extensions import db  # Import db from extensions

app = Flask(__name__)

# Get individual database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

# Construct the database URL from individual components
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
print(f"Connecting to database at {DATABASE_URL}", flush=True)  # Log the URL without exposing password

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET')

bcrypt = Bcrypt(app)

# Register blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
app.register_blueprint(users_blueprint, url_prefix='/api/users')

# Routes
@app.route('/api/auth/register', methods=['POST'])
def register():

    print("\n\nShubham Register endpoint hit", flush=True)

    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 409
    
    # Hash the password
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # Create new user
    new_user = User(
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        email=data['email'],
        password=hashed_password,
        address=data.get('address', ''),
        city=data.get('city', ''),
        state=data.get('state', ''),
        zip_code=data.get('zip_code', '')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing credentials'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, app.config['JWT_SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 200

@app.route('/api/users/me', methods=['GET'])
def get_user_profile(current_user):
    return jsonify(current_user.to_dict()), 200

@app.route('/api/users/me', methods=['PUT'])
def update_user_profile(current_user):
    data = request.get_json()
    
    if data.get('first_name'):
        current_user.first_name = data['first_name']
    if data.get('last_name'):
        current_user.last_name = data['last_name']
    if data.get('address'):
        current_user.address = data['address']
    if data.get('city'):
        current_user.city = data['city']
    if data.get('state'):
        current_user.state = data['state']
    if data.get('zip_code'):
        current_user.zip_code = data['zip_code']
    
    db.session.commit()
    
    return jsonify(current_user.to_dict()), 200

@app.route('/api/users/me/password', methods=['PUT'])
def change_password(current_user):
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    if not bcrypt.check_password_hash(current_user.password, data['current_password']):
        return jsonify({'message': 'Current password is incorrect'}), 401
    
    # Hash the new password
    current_user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')
    db.session.commit()
    
    return jsonify({'message': 'Password updated successfully'}), 200

@app.route('/api/auth/validate', methods=['GET'])
def validate_token(current_user):
    return jsonify({'message': 'Token is valid', 'user_id': current_user.id}), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    print("Starting User Auth Service...")
    with app.app_context():
        db.init_app(app)  # Initialize db with the app
        db.create_all()  # Create all tables
    app.run(host='0.0.0.0', port=8080, debug=True)