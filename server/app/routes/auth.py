from flask import Blueprint, request, jsonify
from app import db, bcrypt, mail
from app.models.user import User
from flask_jwt_extended import create_access_token
from flask_mail import Message
import secrets

# Create a blueprint named 'auth' to group all authentication routes
auth = Blueprint('auth', __name__)

# ─── REGISTER ───────────────────────────────────────────────
@auth.route('/register', methods=['POST'])
def register():
    # Get the data sent from the app
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Check that all fields are provided
    if not username or not email or not password:
        return jsonify({'message': 'All fields are required'}), 400

    # Check if a user with this email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'Email already registered'}), 409

    # Hash the password before saving it to the database
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Create a new user object and save it to the database
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Account created successfully'}), 201


# ─── LOGIN ──────────────────────────────────────────────────
@auth.route('/login', methods=['POST'])
def login():
    # Get the data sent from the app
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Check that all fields are provided
    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    # Find the user in the database by email
    user = User.query.filter_by(email=email).first()

    # Check if user exists and if the password matches
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid email or password'}), 401

    # Generate a JWT token that keeps the user logged in
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful',
        'token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }), 200


# ─── FORGOT PASSWORD ────────────────────────────────────────
@auth.route('/forgot-password', methods=['POST'])
def forgot_password():
    # Get the email sent from the app
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    # Find the user in the database by email
    user = User.query.filter_by(email=email).first()

    # Always return success even if email not found
    # This prevents attackers from knowing which emails are registered
    if not user:
        return jsonify({'message': 'If this email exists, a reset link has been sent'}), 200

    # Generate a secure random reset token
    reset_token = secrets.token_urlsafe(32)

    # Save the token to the user's record in the database
    user.reset_token = reset_token
    db.session.commit()

    # Send the reset email
    reset_link = f"http://localhost:5000/auth/reset-password/{reset_token}"
    msg = Message(
        subject='CardioApp Password Reset',
        recipients=[email],
        body=f"Hello {user.username},\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you did not request this, ignore this email."
    )
    mail.send(msg)

    return jsonify({'message': 'If this email exists, a reset link has been sent'}), 200


# ─── RESET PASSWORD ─────────────────────────────────────────
@auth.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    # Find the user with this reset token
    user = User.query.filter_by(reset_token=token).first()

    if not user:
        return jsonify({'message': 'Invalid or expired reset token'}), 400

    # Get the new password from the request
    data = request.get_json()
    new_password = data.get('password')

    if not new_password:
        return jsonify({'message': 'New password is required'}), 400

    # Hash the new password and save it
    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    
    # Clear the reset token so it cannot be used again
    user.reset_token = None
    db.session.commit()

    return jsonify({'message': 'Password reset successful'}), 200

    # ─── TEST TOKEN (REMOVE BEFORE FINAL SUBMISSION) ────────────
@auth.route('/test-token', methods=['GET'])
def test_token():
    # Returns a token for user ID 1 for testing purposes only
    token = create_access_token(identity="1")
    return jsonify({'token': token}), 200