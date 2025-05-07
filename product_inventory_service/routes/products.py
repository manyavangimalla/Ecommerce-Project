from flask import Blueprint, request, jsonify
from models import db, Product, Category
from utils.auth import token_required, admin_required
from utils.cache import redis_client

products_blueprint = Blueprint('products', __name__)

@products_blueprint.route('/', methods=['GET'])
def get_products():
    # Get query parameters
    category = request.args.get('category')
    search = request.args.get('search')
    sort = request.args.get('sort', 'name')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Try to get from cache first
    cache_key = f"products:{category or ''}:{search or ''}:{sort}:{page}:{per_page}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return jsonify(eval(cached_result)), 200
    
    # If not in cache, query database
    query = Product.query
    
    if category:
        category_obj = Category.query.filter_by(name=category).first()
        if category_obj:
            query = query.filter_by(category_id=category_obj.id)
    
    if search:
        search = f"%{search}%"
        query = query.filter(Product.name.ilike(search) | Product.description.ilike(search))
    
    # Apply sorting
    if sort == 'price_low':
        query = query.order_by(Product.price)
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'newest':
        query = query.order_by(Product.created_at.desc())
    else:  # default to name
        query = query.order_by(Product.name)
    
    # Apply pagination
    products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'items': [product.to_dict() for product in products.items],
        'total': products.total,
        'pages': products.pages,
        'page': page
    }
    
    # Cache the result for 5 minutes
    redis_client.setex(cache_key, 300, str(result))
    
    return jsonify(result), 200

@products_blueprint.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    # Try to get from cache first
    cache_key = f"product:{product_id}"
    cached_product = redis_client.get(cache_key)
    
    if cached_product:
        return jsonify(eval(cached_product)), 200
    
    # If not in cache, query database
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    result = product.to_dict()
    
    # Cache the result for 5 minutes
    redis_client.setex(cache_key, 300, str(result))
    
    return jsonify(result), 200

@products_blueprint.route('/', methods=['POST'])
@token_required
@admin_required
def create_product(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('price') or not data.get('category_id'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if category exists
    category = Category.query.get(data['category_id'])
    if not category:
        return jsonify({'message': 'Category not found'}), 404
    
    # Create new product
    new_product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=float(data['price']),
        stock=int(data.get('stock', 0)),
        category_id=data['category_id']
    )
    
    db.session.add(new_product)
    db.session.commit()
    
    # Invalidate cache
    for key in redis_client.keys("products:*"):
        redis_client.delete(key)
    
    return jsonify(new_product.to_dict()), 201

@products_blueprint.route('/<product_id>', methods=['PUT'])
@token_required
@admin_required
def update_product(current_user_id, product_id):
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    data = request.get_json()
    
    if data.get('name'):
        product.name = data['name']
    if data.get('description') is not None:
        product.description = data['description']
    if data.get('price'):
        product.price = float(data['price'])
    if data.get('stock') is not None:
        product.stock = int(data['stock'])
    if data.get('category_id'):
        # Check if category exists
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({'message': 'Category not found'}), 404
        product.category_id = data['category_id']
    
    db.session.commit()
    
    # Invalidate cache
    redis_client.delete(f"product:{product_id}")
    for key in redis_client.keys("products:*"):
        redis_client.delete(key)
    
    return jsonify(product.to_dict()), 200

@products_blueprint.route('/<product_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_product(current_user_id, product_id):
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    db.session.delete(product)
    db.session.commit()
    
    # Invalidate cache
    redis_client.delete(f"product:{product_id}")
    for key in redis_client.keys("products:*"):
        redis_client.delete(key)
    
    return jsonify({'message': 'Product deleted'}), 200 