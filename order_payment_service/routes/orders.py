from flask import Blueprint, request, jsonify
from models import db, Order, OrderItem
from utils.auth import token_required
from utils.notifications import send_notification
from utils.nats_client import publish_order_created_event
import requests
import asyncio
import os
import uuid

orders_blueprint = Blueprint('orders', __name__)

@orders_blueprint.route('/', methods=['POST'])
@token_required
def create_order(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('items') or not data.get('shipping_address') or not data.get('payment_method'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Validate inventory
    items_to_check = [{'product_id': item['product_id'], 'quantity': item['quantity']} for item in data['items']]
    try:
        inventory_response = requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/inventory/check",
            json={'items': items_to_check}
        )
        inventory_data = inventory_response.json()
        
        # Check if all items are available
        for item in inventory_data:
            if not item['available']:
                return jsonify({'message': item['message']}), 400
    except:
        return jsonify({'message': 'Error checking inventory'}), 500
    
    # Calculate total amount
    total_amount = sum(item['price'] * item['quantity'] for item in data['items'])
    
    # Create new order
    new_order = Order(
        user_id=current_user_id,
        total_amount=total_amount,
        shipping_address=data['shipping_address'],
        billing_address=data.get('billing_address', data['shipping_address']),
        payment_method=data['payment_method']
    )
    
    # Add order items
    for item in data['items']:
        new_order.items.append(OrderItem(
            product_id=item['product_id'],
            product_name=item['product_name'],
            quantity=item['quantity'],
            price=item['price']
        ))
    
    db.session.add(new_order)
    
    # Create payment record
    payment = Payment(
        order_id=new_order.id,
        amount=total_amount,
        payment_method=data['payment_method']
    )
    
    db.session.add(payment)
    db.session.commit()
    
    # Process payment
    # In a real application, this would integrate with a payment gateway like Stripe
    payment_successful = True
    
    if payment_successful:
        payment.status = 'completed'
        payment.transaction_id = str(uuid.uuid4())  # This would be the transaction ID from the payment gateway
        new_order.status = 'processing'
        
        # Update inventory
        try:
            requests.post(
                f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/inventory/update",
                headers={'Authorization': request.headers.get('Authorization')},
                json={'items': [{'product_id': item['product_id'], 'quantity': item['quantity'], 'operation': 'decrease'} for item in data['items']]}
            )
        except:
            # Log error, but don't fail the order
            pass
        
        # Send notification
        send_notification(
            current_user_id,
            'order_placed',
            {
                'order_id': new_order.id,
                'total_amount': total_amount,
                'status': new_order.status
            }
        )
        # Publish order_created event to NATS
        order_event = {
            'event_type': 'order_created',
            'order_id': new_order.id,
            'user_id': current_user_id,
            'items': [{'product_id': item.product_id, 'quantity': item.quantity} for item in new_order.items]
        }
        asyncio.run(publish_order_created_event(order_event))
    else:
        payment.status = 'failed'
        new_order.status = 'cancelled'
    
    db.session.commit()
    
    return jsonify({
        'order': new_order.to_dict(),
        'payment': payment.to_dict()
    }), 201

@orders_blueprint.route('/', methods=['GET'])
@token_required
def get_user_orders(current_user_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    orders = Order.query.filter_by(user_id=current_user_id).order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'page': page
    }
    
    return jsonify(result), 200

@orders_blueprint.route('/<order_id>', methods=['GET'])
@token_required
def get_order(current_user_id, order_id):
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    # Ensure the user can only access their own orders
    if order.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify(order.to_dict()), 200

@orders_blueprint.route('/<order_id>/cancel', methods=['POST'])
@token_required
def cancel_order(current_user_id, order_id):
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    # Ensure the user can only cancel their own orders
    if order.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Can only cancel orders in pending or processing status
    if order.status not in ['pending', 'processing']:
        return jsonify({'message': 'Cannot cancel order in current status'}), 400
    
    # Update order status
    order.status = 'cancelled'
    
    # Restore inventory
    try:
        requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/inventory/update",
            headers={'Authorization': request.headers.get('Authorization')},
            json={'items': [{'product_id': item.product_id, 'quantity': item.quantity, 'operation': 'increase'} for item in order.items]}
        )
    except:
        # Log error, but don't fail the cancellation
        pass
    
    db.session.commit()
    
    # Send notification
    send_notification(
        current_user_id,
        'order_cancelled',
        {
            'order_id': order.id,
            'total_amount': order.total_amount,
            'status': order.status
        }
    )
    
    return jsonify(order.to_dict()), 200 