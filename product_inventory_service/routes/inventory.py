from flask import Blueprint, request, jsonify
from models import db, Product
from utils.auth import token_required
from utils.cache import redis_client

inventory_blueprint = Blueprint('inventory', __name__)

@inventory_blueprint.route('/check', methods=['POST'])
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

@inventory_blueprint.route('/update', methods=['POST'])
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