from flask_sqlalchemy import SQLAlchemy
import datetime
import uuid
import json

# Initialize SQLAlchemy
# This should be initialized in app.py and imported here

db = SQLAlchemy()

class Notification(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # email, sms, in-app
    content = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text, nullable=True)  # JSON string
    is_read = db.Column(db.Boolean, default=False)
    sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'content': self.content,
            'data': json.loads(self.data) if self.data else None,
            'is_read': self.is_read,
            'sent': self.sent,
            'created_at': self.created_at.isoformat()
        }

class UserNotificationPreference(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False, unique=True)
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    app_notifications = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_notifications': self.email_notifications,
            'sms_notifications': self.sms_notifications,
            'app_notifications': self.app_notifications,
            'email': self.email,
            'phone': self.phone
        } 