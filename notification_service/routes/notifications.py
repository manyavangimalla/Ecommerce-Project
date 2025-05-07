from flask import Blueprint, request, jsonify
from models import db, Notification, UserNotificationPreference
from utils.auth import token_required
from utils.notifications import send_notification
import json

notifications_blueprint = Blueprint('notifications', __name__)

@notifications_blueprint.route('/', methods=['POST'])
def create_notification():
    data = request.get_json()
    
    if not data or not data.get('user_id') or not data.get('type'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Generate notification content based on type
    content = ""
    notification_data = {}
    
    if data.get('type') == 'order_placed':
        order_data = data.get('data', {})
        content = f"Your order #{order_data.get('order_id')} has been placed successfully. Total amount: ${order_data.get('total_amount', 0):.2f}"
        notification_data = {
            'subject': 'Order Confirmation',
            'order_id': order_data.get('order_id'),
            'total_amount': order_data.get('total_amount', 0)
        }
    
    elif data.get('type') == 'order_status_changed':
        order_data = data.get('data', {})
        content = f"Your order #{order_data.get('order_id')} status has been updated from {order_data.get('old_status')} to {order_data.get('new_status')}."
        notification_data = {
            'subject': 'Order Status Update',
            'order_id': order_data.get('order_id'),
            'new_status': order_data.get('new_status')
        }
    
    elif data.get('type') == 'order_cancelled':
        order_data = data.get('data', {})
        content = f"Your order #{order_data.get('order_id')} has been cancelled."
        notification_data = {
            'subject': 'Order Cancellation',
            'order_id': order_data.get('order_id')
        }
    
    else:
        # For custom notifications
        content = data.get('content', 'You have a new notification')
        notification_data = data.get('data', {})
    
    # Create email notification
    email_notification = Notification(
        user_id=data['user_id'],
        type='email',
        content=content,
        data=json.dumps(notification_data)
    )
    db.session.add(email_notification)
    
    # Create in-app notification
    app_notification = Notification(
        user_id=data['user_id'],
        type='in-app',
        content=content,
        data=json.dumps(notification_data)
    )
    db.session.add(app_notification)
    
    db.session.commit()
    
    return jsonify({'message': 'Notification created successfully'}), 201

@notifications_blueprint.route('/', methods=['GET'])
@token_required
def get_user_notifications(current_user_id):
    notification_type = request.args.get('type', 'in-app')
    read_status = request.args.get('read')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = Notification.query.filter_by(user_id=current_user_id, type=notification_type)
    
    if read_status is not None:
        is_read = read_status.lower() == 'true'
        query = query.filter_by(is_read=is_read)
    
    notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [notification.to_dict() for notification in notifications.items],
        'total': notifications.total,
        'pages': notifications.pages,
        'page': page,
        'unread_count': Notification.query.filter_by(user_id=current_user_id, type=notification_type, is_read=False).count()
    }
    
    return jsonify(result), 200

@notifications_blueprint.route('/<notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_user_id, notification_id):
    notification = Notification.query.get(notification_id)
    
    if not notification:
        return jsonify({'message': 'Notification not found'}), 404
    
    # Ensure the user can only mark their own notifications
    if notification.user_id != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify(notification.to_dict()), 200

@notifications_blueprint.route('/preferences', methods=['GET'])
@token_required
def get_notification_preferences(current_user_id):
    preferences = UserNotificationPreference.query.filter_by(user_id=current_user_id).first()
    
    if not preferences:
        preferences = UserNotificationPreference(user_id=current_user_id)
        db.session.add(preferences)
        db.session.commit()
    
    return jsonify(preferences.to_dict()), 200

@notifications_blueprint.route('/preferences', methods=['PUT'])
@token_required
def update_notification_preferences(current_user_id):
    data = request.get_json()
    
    preferences = UserNotificationPreference.query.filter_by(user_id=current_user_id).first()
    
    if not preferences:
        preferences = UserNotificationPreference(user_id=current_user_id)
        db.session.add(preferences)
    
    if 'email_notifications' in data:
        preferences.email_notifications = bool(data['email_notifications'])
    if 'sms_notifications' in data:
        preferences.sms_notifications = bool(data['sms_notifications'])
    if 'app_notifications' in data:
        preferences.app_notifications = bool(data['app_notifications'])
    if 'email' in data:
        preferences.email = data['email']
    if 'phone' in data:
        preferences.phone = data['phone']
    
    db.session.commit()
    
    return jsonify(preferences.to_dict()), 200 