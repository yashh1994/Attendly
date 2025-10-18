from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import User, Class, ClassEnrollment, db
from sqlalchemy.exc import IntegrityError

classes_bp = Blueprint('classes', __name__)

def get_current_user():
    """Helper function to get current authenticated user"""
    user_id = get_jwt_identity()
    return User.query.get(user_id)

@classes_bp.route('/create', methods=['POST'])
@jwt_required()
def create_class():
    """Create a new class (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can create classes'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Class name is required'}), 400
        
        # Create new class
        new_class = Class(
            name=data['name'],
            description=data.get('description', ''),
            teacher_id=current_user.id
        )
        
        # Generate unique join code
        new_class.generate_join_code()
        
        db.session.add(new_class)
        db.session.commit()
        
        return jsonify({
            'message': 'Class created successfully',
            'class': new_class.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/my-classes', methods=['GET'])
@jwt_required()
def get_my_classes():
    """Get classes for current user (created classes for teachers, enrolled classes for students)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role == 'teacher':
            # Get classes created by teacher
            classes = Class.query.filter_by(teacher_id=current_user.id, is_active=True).all()
            classes_data = [class_obj.to_dict() for class_obj in classes]
        else:
            # Get classes enrolled by student
            enrollments = ClassEnrollment.query.filter_by(
                student_id=current_user.id, 
                is_active=True
            ).all()
            classes_data = [enrollment.class_ref.to_dict() for enrollment in enrollments]
        
        return jsonify({
            'classes': classes_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/<int:class_id>', methods=['GET'])
@jwt_required()
def get_class_details(class_id):
    """Get details of a specific class"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        class_obj = Class.query.get(class_id)
        
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if user has access to this class
        has_access = False
        if current_user.role == 'teacher' and class_obj.teacher_id == current_user.id:
            has_access = True
        elif current_user.role == 'student':
            enrollment = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                class_id=class_id,
                is_active=True
            ).first()
            has_access = enrollment is not None
        
        if not has_access:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get enrolled students if user is teacher
        class_data = class_obj.to_dict()
        if current_user.role == 'teacher':
            enrollments = ClassEnrollment.query.filter_by(
                class_id=class_id,
                is_active=True
            ).all()
            class_data['students'] = [
                {
                    'id': enrollment.student.id,
                    'name': f"{enrollment.student.first_name} {enrollment.student.last_name}",
                    'email': enrollment.student.email,
                    'enrolled_at': enrollment.enrolled_at.isoformat()
                }
                for enrollment in enrollments
            ]
        
        return jsonify({
            'class': class_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/join', methods=['POST'])
@jwt_required()
def join_class():
    """Join a class using join code (Student only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can join classes'}), 403
        
        data = request.get_json()
        
        if not data.get('join_code'):
            return jsonify({'error': 'Join code is required'}), 400
        
        # Find class by join code
        class_obj = Class.query.filter_by(
            join_code=data['join_code'].upper(),
            is_active=True
        ).first()
        
        if not class_obj:
            return jsonify({'error': 'Invalid join code'}), 404
        
        # Check if student is already enrolled
        existing_enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_obj.id
        ).first()
        
        if existing_enrollment:
            if existing_enrollment.is_active:
                return jsonify({'error': 'Already enrolled in this class'}), 409
            else:
                # Reactivate enrollment
                existing_enrollment.is_active = True
                db.session.commit()
                return jsonify({
                    'message': 'Successfully rejoined the class',
                    'class': class_obj.to_dict()
                }), 200
        
        # Create new enrollment
        enrollment = ClassEnrollment(
            student_id=current_user.id,
            class_id=class_obj.id
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully joined the class',
            'class': class_obj.to_dict()
        }), 200
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Already enrolled in this class'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/<int:class_id>/leave', methods=['POST'])
@jwt_required()
def leave_class(class_id):
    """Leave a class (Student only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can leave classes'}), 403
        
        # Find enrollment
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_active=True
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this class'}), 404
        
        # Deactivate enrollment
        enrollment.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully left the class'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/<int:class_id>/update', methods=['PUT'])
@jwt_required()
def update_class(class_id):
    """Update class details (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can update classes'}), 403
        
        class_obj = Class.query.get(class_id)
        
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        if class_obj.teacher_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Update allowed fields
        if 'name' in data:
            class_obj.name = data['name']
        if 'description' in data:
            class_obj.description = data['description']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Class updated successfully',
            'class': class_obj.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/<int:class_id>/regenerate-code', methods=['POST'])
@jwt_required()
def regenerate_join_code(class_id):
    """Regenerate join code for a class (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can regenerate join codes'}), 403
        
        class_obj = Class.query.get(class_id)
        
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        if class_obj.teacher_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate new join code
        class_obj.generate_join_code()
        db.session.commit()
        
        return jsonify({
            'message': 'Join code regenerated successfully',
            'new_join_code': class_obj.join_code
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500