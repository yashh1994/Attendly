from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import User, Class, ClassEnrollment, FaceData, db
from sqlalchemy.exc import IntegrityError

classes_bp = Blueprint('classes', __name__)

def get_current_user():
    """Helper function to get current authenticated user"""
    user_id = int(get_jwt_identity())
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
        
        # Check if student has registered facial data
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            print(f"❌ Join class failed: Student {current_user.email} has not registered facial data")
            return jsonify({
                'error': 'Facial data required',
                'message': 'You must register your facial data before joining a class. Please register your face data from the Account page.'
            }), 403
        
        print(f"✅ Student {current_user.email} has facial data registered")
        
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
        
        print(f"📝 Student {current_user.email} attempting to join class: {class_obj.name}")
        
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
                
                # Update class student count
                class_obj.update_student_count()
                
                db.session.commit()
                print(f"✅ Student {current_user.email} rejoined class: {class_obj.name}")
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
        
        # Update class student count
        class_obj.update_student_count()
        
        db.session.commit()
        
        print(f"✅ Student {current_user.email} successfully joined class: {class_obj.name}")
        
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
            print(f"❌ Leave class failed: User not found")
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            print(f"❌ Leave class failed: User {current_user.email} is not a student (role: {current_user.role})")
            return jsonify({'error': 'Only students can leave classes'}), 403
        
        print(f"📤 Student {current_user.email} attempting to leave class ID: {class_id}")
        
        # Find enrollment
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_active=True
        ).first()
        
        if not enrollment:
            print(f"❌ Leave class failed: Student {current_user.email} not enrolled in class {class_id}")
            return jsonify({'error': 'Not enrolled in this class'}), 404
        
        # Get class details for logging
        class_obj = Class.query.get(class_id)
        class_name = class_obj.name if class_obj else f"Class {class_id}"
        
        # Deactivate enrollment (soft delete)
        enrollment.is_active = False
        enrollment.updated_at = db.func.now()
        db.session.commit()
        
        print(f"✅ Student {current_user.email} successfully left class: {class_name}")
        
        return jsonify({
            'message': f'Successfully left the class',
            'class_id': class_id,
            'class_name': class_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error leaving class {class_id}: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@classes_bp.route('/<int:class_id>/enrollment-status', methods=['GET'])
@jwt_required()
def get_enrollment_status(class_id):
    """Get enrollment status for a specific class (Student only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can check enrollment status'}), 403
        
        # Get class details
        class_obj = Class.query.get(class_id)
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check current active enrollment
        active_enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_active=True
        ).first()
        
        # Get all enrollment history (including inactive)
        all_enrollments = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id
        ).order_by(ClassEnrollment.created_at.desc()).all()
        
        enrollment_history = []
        for enrollment in all_enrollments:
            enrollment_history.append({
                'id': enrollment.id,
                'joined_at': enrollment.created_at.isoformat(),
                'left_at': enrollment.updated_at.isoformat() if not enrollment.is_active else None,
                'is_active': enrollment.is_active
            })
        
        return jsonify({
            'class_id': class_id,
            'class_name': class_obj.name,
            'is_enrolled': active_enrollment is not None,
            'can_rejoin': True,  # Students can always rejoin if they have the code
            'enrollment_history': enrollment_history,
            'total_enrollments': len(all_enrollments)
        }), 200
        
    except Exception as e:
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

@classes_bp.route('/dashboard-stats', methods=['GET'])
@jwt_required()
def get_teacher_dashboard_stats():
    """Get teacher dashboard statistics"""
    try:
        from models.models import AttendanceSession, AttendanceRecord
        from sqlalchemy import func, and_
        from datetime import datetime, date
        
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can access dashboard stats'}), 403
        
        # Get teacher's classes
        teacher_classes = Class.query.filter_by(
            teacher_id=current_user.id,
            is_active=True
        ).all()
        
        # Calculate total classes
        total_classes = len(teacher_classes)
        print(f'🔥 BACKEND: Teacher {current_user.id} has {total_classes} classes: {[c.id for c in teacher_classes]}')
        
        # Calculate total students across all classes by counting active enrollments
        total_students = db.session.query(func.count(ClassEnrollment.id)).join(Class).filter(
            Class.teacher_id == current_user.id,
            Class.is_active == True,
            ClassEnrollment.is_active == True
        ).scalar() or 0
        
        print(f'🔥 BACKEND: Total students calculated: {total_students}')
        
        # Debug: Get detailed enrollment info
        enrollments = db.session.query(ClassEnrollment).join(Class).filter(
            Class.teacher_id == current_user.id,
            Class.is_active == True,
            ClassEnrollment.is_active == True
        ).all()
        
        print(f'🔥 BACKEND: Found {len(enrollments)} active enrollments:')
        for enrollment in enrollments:
            print(f'  - Class {enrollment.class_id}: Student {enrollment.student_id}')
        
        # Get today's sessions
        today = date.today()
        today_sessions = AttendanceSession.query.join(Class).filter(
            Class.teacher_id == current_user.id,
            func.date(AttendanceSession.session_date) == today,
            AttendanceSession.is_active == True
        ).count()
        
        # Calculate average attendance rate
        # Get all attendance records for teacher's classes
        attendance_stats = db.session.query(
            func.avg(
                func.cast(AttendanceSession.present_count, db.Float) / 
                func.nullif(AttendanceSession.total_students, 0) * 100
            ).label('avg_attendance')
        ).join(Class).filter(
            Class.teacher_id == current_user.id,
            AttendanceSession.total_students > 0,
            AttendanceSession.is_active == True
        ).first()
        
        avg_attendance = round(attendance_stats.avg_attendance or 0, 1) if attendance_stats.avg_attendance else 0
        
        # Get recent activity (last 7 days of sessions)
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        
        recent_sessions = AttendanceSession.query.join(Class).filter(
            Class.teacher_id == current_user.id,
            AttendanceSession.session_date >= week_ago,
            AttendanceSession.is_active == True
        ).order_by(AttendanceSession.session_date.desc()).limit(5).all()
        
        recent_activity = []
        for session in recent_sessions:
            recent_activity.append({
                'id': session.id,
                'class_name': session.class_ref.name,
                'session_name': session.session_name,
                'date': session.session_date.isoformat(),
                'present_count': session.present_count,
                'total_students': session.total_students,
                'attendance_rate': round((session.present_count / session.total_students * 100) if session.total_students > 0 else 0, 1)
            })
        
        # Debug information
        debug_info = {
            'teacher_classes_count': len(teacher_classes),
            'class_names': [c.name for c in teacher_classes],
            'individual_student_counts': [c.student_count for c in teacher_classes]
        }
        
        result = {
            'statistics': {
                'total_classes': total_classes,
                'total_students': total_students,
                'todays_sessions': today_sessions,
                'avg_attendance_rate': avg_attendance
            },
            'recent_activity': recent_activity,
            'debug': {
                'teacher_id': current_user.id,
                'teacher_name': f'{current_user.first_name} {current_user.last_name}',
                'teacher_classes_count': len(teacher_classes),
                'class_names': [c.name for c in teacher_classes],
                'individual_student_counts': [c.student_count for c in teacher_classes],
                'enrollment_count': len(enrollments)
            },
            'summary': {
                'message': f'Dashboard stats for {current_user.first_name} {current_user.last_name}',
                'generated_at': datetime.utcnow().isoformat()
            }
        }
        
        print(f'🔥 BACKEND: Final dashboard response: {result}')
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500