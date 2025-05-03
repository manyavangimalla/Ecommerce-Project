# Frontend/db.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name or '',
            'last_name': self.last_name or '',
            'address': self.address or '',
            'city': self.city or '',
            'state': self.state or '',
            'zip_code': self.zip_code or ''
        }

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def create_user(email, password, first_name='', last_name='', address='', city='', state='', zip_code=''):
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user