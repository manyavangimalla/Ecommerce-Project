from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from routes.orders import orders_blueprint
from routes.payments import payments_blueprint
from routes.admin import admin_blueprint
import os

app = Flask(__name__)

# Get individual database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

# Construct the database URL from individual components
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
print(f"Connecting to database at {DATABASE_URL.replace(db_password, '******')}", flush=True)  # Log the URL without exposing password

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Register blueprints
app.register_blueprint(orders_blueprint, url_prefix='/api/orders')
app.register_blueprint(payments_blueprint, url_prefix='/api/payments')
app.register_blueprint(admin_blueprint, url_prefix='/api/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)