from flask import Flask, request, jsonify
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
import datetime
import json
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jwt
from functools import wraps
from nats.aio.client import Client as NATS
import asyncio
from routes.notifications import notifications_blueprint
from extensions import db  # Import db from extensions
from models import Notification, UserNotificationPreference  # Import Notification and UserNotificationPreference models

app = Flask(__name__)

# Get individual database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

# Construct the database URL from individual components
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
print(f"Connecting to database at {DATABASE_URL.replace(db_password, '******')}")  # Log the URL without exposing password

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET')

# Email configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-password')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@shopeasy.com')

# Initialize db with the app
with app.app_context():
    db.init_app(app)

# NATS subscriber configuration
nats_client = NATS()

async def run(loop):
    print("\n\n Shubham starting nats client \n\n", flush=True)
    await nats_client.connect(servers=["nats://nats:4222"])
    print("\n\n Shubham connected to nats server \n\n", flush=True)
    
    async def message_handler(msg):
        event = json.loads(msg.data.decode('utf-8'))
        print(f"Received event: {event}")

        if event['event_type'] == 'order_created':
            # For now, just print the event
            print(f"\n\nShubham Order placed event received: {event}", flush=True)

    await nats_client.subscribe("order_created", cb=message_handler)
    print("\n\n Shubham subscribed to 'order_created' subject \n\n", flush=True)
    while True:
        await asyncio.sleep(1)  # Keep the listener alive

def start_nats_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run(loop))

# Start NATS listener in a background thread
nats_thread = threading.Thread(target=start_nats_listener, daemon=True)
nats_thread.start()

# Register blueprints
app.register_blueprint(notifications_blueprint, url_prefix='/api/notifications')

# Routes
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    print("\n\n Shubham starting notification service \n\n", flush=True)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True)