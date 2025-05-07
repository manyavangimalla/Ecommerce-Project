from flask import Flask
from routes.gateway import gateway_blueprint

app = Flask(__name__)

# Register blueprints
app.register_blueprint(gateway_blueprint)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)