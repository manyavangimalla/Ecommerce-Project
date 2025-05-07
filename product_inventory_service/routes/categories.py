from flask import Blueprint, request, jsonify
from models import db, Category
from utils.auth import token_required, admin_required
from utils.cache import redis_client

categories_blueprint = Blueprint('categories', __name__)

@categories_blueprint.route('/', methods=['GET'])
def get_categories():
    # Try to get from cache first
    cache_key = "categories"
    cached_categories = redis_client.get(cache_key)
    
    if cached_categories:
        return jsonify(eval(cached_categories)), 200
    
    # If not in cache, query database
    categories = Category.query.all()
    result = [category.to_dict() for category in categories]
    
    # Cache the result for 10 minutes
    redis_client.setex(cache_key, 600, str(result))
    
    return jsonify(result), 200

@categories_blueprint.route('/', methods=['POST'])
@token_required
@admin_required
def create_category(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if category already exists
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'message': 'Category already exists'}), 409
    
    # Create new category
    new_category = Category(name=data['name'])
    
    db.session.add(new_category)
    db.session.commit()
    
    # Invalidate cache
    redis_client.delete("categories")
    
 