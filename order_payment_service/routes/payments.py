from flask import Blueprint, request, jsonify
from models import db, Payment
from utils.auth import token_required

payments_blueprint = Blueprint('payments', __name__)

# Add payment-related routes here

@payments_blueprint.route('/<payment_id>', methods=['GET'])
@token_required
def get_payment(current_user_id, payment_id):
    payment = Payment.query.get(payment_id)
    
    if not payment:
        return jsonify({'message': 'Payment not found'}), 404
    
    # Ensure the user can only access their own payments
    if payment.order.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify(payment.to_dict()), 200 