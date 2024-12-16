from flask import Blueprint, request, jsonify, current_app
from models.models import UserModel, db_session
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta


auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Username and password are required."}), 400

    if db_session.query(UserModel).filter_by(email=email).first():
        return jsonify({"message": "Username already exists."}), 400

    hashed_password = generate_password_hash(password)
    new_user = UserModel(email=email, password=hashed_password, name=name)
    db_session.add(new_user)
    db_session.commit()

    return jsonify({"message": "User created successfully."}), 201

@auth_bp.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "email and password are required."}), 400

    user = db_session.query(UserModel).filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials."}), 401
    
    token = jwt.encode(
        {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        },
        current_app.config['SECRET_KEY'],
        algorithm="HS256"
    )

    return jsonify({"message": "Login successful.", "token": token}), 200

