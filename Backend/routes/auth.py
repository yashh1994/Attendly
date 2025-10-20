from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models.models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength (minimum 8 characters)"""
    return len(password) >= 8

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """User registration endpoint"""
    print("🔥 SIGNUP ENDPOINT HIT!")
    print(f"🔥 Request method: {request.method}")
    print(f"🔥 Request URL: {request.url}")
    print(f"🔥 Request headers: {dict(request.headers)}")
    
    try:
        data = request.get_json()
        print(f"🔥 Request data: {data}")
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"🔥 Missing field: {field}")
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate email format
        print(f"🔥 Validating email: {data['email']}")
        if not validate_email(data['email']):
            print(f"🔥 Invalid email format")
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        print(f"🔥 Validating password length: {len(data['password'])}")
        if not validate_password(data['password']):
            print(f"🔥 Password too short")
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Validate role
        print(f"🔥 Validating role: {data['role']}")
        if data['role'] not in ['teacher', 'student']:
            print(f"🔥 Invalid role")
            return jsonify({'error': 'Role must be either teacher or student'}), 400
        
        # Check if user already exists
        print(f"🔥 Checking if user exists for email: {data['email']}")
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            print(f"🔥 User already exists")
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Create new user
        print(f"🔥 Creating new user...")
        user = User(
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role']
        )
        user.set_password(data['password'])
        
        print(f"🔥 Adding user to database...")
        db.session.add(user)
        db.session.commit()
        print(f"🔥 User created successfully with ID: {user.id}")
        
        # Create access token
        print(f"🔥 Creating access token...")
        print(f"🔥 User ID: {user.id}, Type: {type(user.id)}")
        access_token = create_access_token(identity=str(user.id))
        
        print(f"🔥 Returning success response")
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict(),
            'access_token': access_token
        }), 201
        
    except Exception as e:
        print(f"🔥 ERROR in signup: {str(e)}")
        print(f"🔥 ERROR type: {type(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user by email
        user = User.query.filter_by(email=data['email'].lower()).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Create access token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            if not validate_email(data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=data['email'].lower()).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already taken'}), 409
            user.email = data['email'].lower()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password strength
        if not validate_password(data['new_password']):
            return jsonify({'error': 'New password must be at least 8 characters long'}), 400
        
        # Update password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@auth_bp.route('/update-role', methods=['PUT'])
@jwt_required()
def update_role():
    """Update user role"""
    try:
        print(f"🔥 UPDATE ROLE: Starting update role request")
        print(f"🔥 UPDATE ROLE: Request headers: {dict(request.headers)}")
        print(f"🔥 UPDATE ROLE: Request method: {request.method}")
        print(f"🔥 UPDATE ROLE: Request URL: {request.url}")
        
        user_id_str = get_jwt_identity()
        print(f"🔥 UPDATE ROLE: User ID from JWT: {user_id_str}, Type: {type(user_id_str)}")
        
        user_id = int(user_id_str)
        print(f"🔥 UPDATE ROLE: User ID converted to int: {user_id}")
        
        user = User.query.get(user_id)
        print(f"🔥 UPDATE ROLE: User found: {user.to_dict() if user else 'None'}")
        
        if not user:
            print(f"🔥 UPDATE ROLE: ERROR - User not found")
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        print(f"🔥 UPDATE ROLE: Request data: {data}")
        
        # Validate role
        if not data.get('role') or data['role'] not in ['teacher', 'student']:
            print(f"🔥 UPDATE ROLE: ERROR - Invalid role: {data.get('role') if data else 'No data'}")
            return jsonify({'error': 'Role must be either teacher or student'}), 400
        
        print(f"🔥 UPDATE ROLE: Updating user role from {user.role} to {data['role']}")
        
        # Update role
        user.role = data['role']
        user._update_full_name()  # Update computed field
        
        print(f"🔥 UPDATE ROLE: Committing changes to database...")
        db.session.commit()
        
        print(f"🔥 UPDATE ROLE: Role updated successfully")
        print(f"🔥 UPDATE ROLE: Updated user: {user.to_dict()}")
        
        return jsonify({
            'message': 'Role updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        print(f"🔥 UPDATE ROLE: ERROR - Exception occurred: {str(e)}")
        print(f"🔥 UPDATE ROLE: ERROR - Exception type: {type(e)}")
        import traceback
        print(f"🔥 UPDATE ROLE: ERROR - Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if token is valid"""
    try:
        print(f"🔥 VERIFY TOKEN: Starting token verification")
        print(f"🔥 VERIFY TOKEN: Request headers: {dict(request.headers)}")
        
        user_id_str = get_jwt_identity()
        print(f"🔥 VERIFY TOKEN: User ID from JWT: {user_id_str}, Type: {type(user_id_str)}")
        
        user_id = int(user_id_str)
        user = User.query.get(user_id)
        print(f"🔥 VERIFY TOKEN: User found: {user.to_dict() if user else 'None'}")
        
        if not user:
            print(f"🔥 VERIFY TOKEN: ERROR - User not found")
            return jsonify({'error': 'User not found'}), 404
        
        print(f"🔥 VERIFY TOKEN: Token is valid")
        return jsonify({
            'message': 'Token is valid',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        print(f"🔥 VERIFY TOKEN: ERROR - Exception occurred: {str(e)}")
        print(f"🔥 VERIFY TOKEN: ERROR - Exception type: {type(e)}")
        return jsonify({'error': 'Invalid token', 'details': str(e)}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side should clear token)"""
    try:
        current_user = get_current_user()
        
        if current_user:
            print(f"🔥 LOGOUT: User {current_user.id} ({current_user.email}) logging out")
        
        # Since we're using JWT tokens (stateless), the actual logout happens client-side
        # by clearing the token. This endpoint is just for logging purposes.
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        print(f"🔥 LOGOUT: ERROR - {str(e)}")
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200  # Return success anyway since logout is client-side