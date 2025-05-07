from flask import Blueprint, request, jsonify
from models import db, User
from utils.auth import token_required
import bcrypt

users_blueprint = Blueprint('users', __name__)

@users_blueprint.route('/me', methods=['GET'])
@token_required
def get_user_profile(current_user):
    return jsonify(current_user.to_dict()), 200

@users_blueprint.route('/me', methods=['PUT'])
@token_required
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

@users_blueprint.route('/me/password', methods=['PUT'])
@token_required
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