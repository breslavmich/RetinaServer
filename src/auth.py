from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from src.constants.http_status_codes import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT, HTTP_201_CREATED, \
    HTTP_401_UNAUTHORIZED, HTTP_200_OK
from src.database import User, db
import validators
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity


auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.post('/register')
def register():
    username = request.json['username']
    email = request.json['email']
    full_name = request.json['full_name']
    password = request.json['password']
    address = request.json['address']

    if len(password) < 6:
        return jsonify({'Error': "Password is too short"}), HTTP_400_BAD_REQUEST

    if len(username) < 3:
        return jsonify({'Error': "Username is too short"}), HTTP_400_BAD_REQUEST

    if not username.isalnum() or " " in username:
        return jsonify({'Error': "Invalid username. The username should be at"
                                 " least 3 characters long, without spaces"}), HTTP_400_BAD_REQUEST

    if not validators.email(email):
        return jsonify({'Error': "Email is invalid"}), HTTP_400_BAD_REQUEST

    if User.query.filter_by(email=email).first() is not None:
        return jsonify({'Error': "A user with this email already exists"}), HTTP_409_CONFLICT

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({'Error': "A user with this username already exists"}), HTTP_409_CONFLICT

    pwd_hash = generate_password_hash(password)

    user = User(username=username, password=pwd_hash, email=email, full_name=full_name, address=address)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created successfully!",
                    "user": {
                        'username': username,
                        'email': email,
                        'full name': full_name,
                        'address': address
                    }}), HTTP_201_CREATED


@auth.post('/login')
def login():
    email = request.json.get('email', '')
    password = request.json.get('password', '')

    user = User.query.filter_by(email=email).first()

    if user:
        is_pass_correct = check_password_hash(user.password, password)

        if is_pass_correct:
            refresh = create_refresh_token(identity=user.id)
            access = create_access_token(identity=user.id)

            return jsonify({
                'user': {
                    'refresh': refresh,
                    'access': access,
                    'username': user.username,
                    'email': user.email
                }
            }), HTTP_200_OK

    return jsonify({'Error': "Wrong email / password"}), HTTP_401_UNAUTHORIZED


@auth.get('/me')
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()
    return jsonify({'user': {
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'address': user.address
    }}), HTTP_200_OK


@auth.get('/token/refresh')
@jwt_required(refresh=True)
def refresh_user_token():
    identity = get_jwt_identity()
    access = create_access_token(identity=identity)

    return jsonify({
        'access': access
    }), HTTP_200_OK


@auth.patch("/update")
@auth.put("/update")
@jwt_required()
def update_user():
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({
            "Error": "No user with this id"
        }), HTTP_400_BAD_REQUEST

    username = request.json.get('username')
    email = request.json.get('email')
    full_name = request.json.get('full_name')
    address = request.json.get('address')

    updated = False

    if username:
        if len(username) < 3:
            return jsonify({'Error': "Username is too short"}), HTTP_400_BAD_REQUEST

        if not username.isalnum() or " " in username:
            return jsonify({'Error': "Invalid username. The username should be at"
                                     " least 3 characters long, without spaces"}), HTTP_400_BAD_REQUEST

        if User.query.filter_by(username=username).first() is not None:
            return jsonify({'Error': "A user with this username already exists"}), HTTP_409_CONFLICT

        user.username = username
        updated = True

    if email:
        if not validators.email(email):
            return jsonify({'Error': "Email is invalid"}), HTTP_400_BAD_REQUEST

        if User.query.filter_by(email=email).first() is not None:
            return jsonify({'Error': "A user with this email already exists"}), HTTP_409_CONFLICT

        user.email = email
        updated = True

    if full_name:
        user.full_name = full_name
        updated = True

    if address:
        user.address = address
        updated = True

    if not updated:
        return jsonify({}), HTTP_400_BAD_REQUEST

    db.session.commit()
    return jsonify({
        "message": "Updated successfully"
    }), HTTP_200_OK
