from functools import wraps
from flask import request, jsonify, current_app
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print(f"Authorization header: {request.headers.get('Authorization')}")
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        print(f"Extracted token: {token}", flush=True)
        if not token:
            print("Token is missing!", flush=True)
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            print(f"Decoded JWT payload: {data}")
            current_user_id = data['user_id']
        except Exception as e:
            print(f"Token is invalid! Error: {e}")
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

# Middleware to log all incoming requests
def log_request():
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}") 