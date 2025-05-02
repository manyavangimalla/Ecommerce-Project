from flask import Flask, request, jsonify, Response
import os
import requests
import json

app = Flask(__name__)

# Middleware to log all incoming requests
@app.before_request
def log_request():
    print(f"Incoming request: {request.method} {request.url}", flush=True)
    print(f"Headers: {dict(request.headers)}")
    if request.data:
        print(f"Body: {request.data.decode('utf-8')}")

# Service URLs
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://localhost:5001')
PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:5002')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:5003')
NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://localhost:5004')

# Routes that don't require authentication
PUBLIC_ROUTES = [
    '/api/auth/login',
    '/api/auth/register',
    '/api/products',
    '/api/categories',
    '/api/products/'
]

# Request forwarding logic
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def forward_request(path):
    full_path = f"/{path}"
    
    # Determine which service to route to
    if full_path.startswith('/api/auth') or full_path.startswith('/api/users'):
        target_url = f"{USER_SERVICE_URL}{full_path}"
    elif full_path.startswith('/api/products') or full_path.startswith('/api/categories') or full_path.startswith('/api/inventory'):
        target_url = f"{PRODUCT_SERVICE_URL}{full_path}"
    elif full_path.startswith('/api/orders'):
        target_url = f"{ORDER_SERVICE_URL}{full_path}"
    elif full_path.startswith('/api/notifications'):
        target_url = f"{NOTIFICATION_SERVICE_URL}{full_path}"
    else:
        return jsonify({'message': 'Route not found'}), 404
    
    # Check authentication except for public routes
    requires_auth = True
    for route in PUBLIC_ROUTES:
        if full_path.startswith(route) and request.method == 'GET':
            requires_auth = False
            break
    
    headers = {}
    for key, value in request.headers:
        if key != 'Host':
            headers[key] = value
    
    if requires_auth and 'Authorization' not in headers:
        return jsonify({'message': 'Authentication required'}), 401
    
    # Proxy request to the appropriate service
    try:
        if request.method == 'GET':
            response = requests.get(
                target_url,
                headers=headers,
                params=request.args
            )
        elif request.method == 'POST':
            response = requests.post(
                target_url,
                headers=headers,
                json=request.get_json() if request.is_json else None,
                data=request.form if not request.is_json else None
            )
        elif request.method == 'PUT':
            response = requests.put(
                target_url,
                headers=headers,
                json=request.get_json() if request.is_json else None,
                data=request.form if not request.is_json else None
            )
        elif request.method == 'DELETE':
            response = requests.delete(
                target_url,
                headers=headers
            )
        else:
            return jsonify({'message': 'Method not supported'}), 405
        
        # Forward the response back to the client
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    
    except requests.exceptions.RequestException as e:
        print(f"Error forwarding request: {str(e)}")
        return jsonify({'message': 'Service unavailable'}), 503

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    health_status = {
        'status': 'healthy',
        'services': {}
    }
    
    # Check health of all services
    services = {
        'user': USER_SERVICE_URL,
        'product': PRODUCT_SERVICE_URL,
        'order': ORDER_SERVICE_URL,
        'notification': NOTIFICATION_SERVICE_URL
    }
    
    all_healthy = True
    
    for name, url in services.items():
        try:
            response = requests.get(f"{url}/health", timeout=2)
            status = response.status_code == 200
            health_status['services'][name] = 'healthy' if status else 'unhealthy'
            if not status:
                all_healthy = False
        except:
            health_status['services'][name] = 'unavailable'
            all_healthy = False
    
    if not all_healthy:
        health_status['status'] = 'degraded'
    
    return jsonify(health_status), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)