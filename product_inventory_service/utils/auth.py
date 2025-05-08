from functools import wraps
from flask import request, jsonify, current_app
import jwt

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
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
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

# Middleware to log all incoming requests
def log_request():
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}") 