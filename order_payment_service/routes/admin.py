from flask import Blueprint, request, jsonify
from models import db, Order
from utils.auth import token_required

admin_blueprint = Blueprint('admin', __name__)

# Add admin-related routes here

@admin_blueprint.route('/orders', methods=['GET'])
@token_required
def get_all_orders(current_user_id):
    # In a real app, check if user is admin
    
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'page': page
    }
    
    return jsonify(result), 200

@admin_blueprint.route('/orders/<order_id>/status', methods=['PUT'])
@token_required
def update_order_status(current_user_id, order_id):
    # In a real app, check if user is admin
    
    data = request.get_json()
    
    if not data or not data.get('status'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    # Validate status transition
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({'message': 'Invalid status'}), 400
    
    # Update order status
    old_status = order.status
    order.status = data['status']
    db.session.commit()
    
    # Send notification
    send_notification(
        order.user_id,
        'order_status_changed',
        {
            'order_id': order.id,
            'old_status': old_status,
            'new_status': order.status
        }
    )
    
    return jsonify(order.to_dict()), 200 