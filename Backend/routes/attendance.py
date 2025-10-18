from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import User, Class, ClassEnrollment, FaceData, AttendanceSession, AttendanceRecord, db
import face_recognition
import numpy as np
import base64
import json
import cv2
from PIL import Image
import io
import os
from datetime import datetime, date

attendance_bp = Blueprint('attendance', __name__)

def get_current_user():
    """Helper function to get current authenticated user"""
    user_id = get_jwt_identity()
    return User.query.get(user_id)

def get_vector_db():
    """Get vector database service"""
    if hasattr(current_app, 'vector_db') and current_app.vector_db:
        return current_app.vector_db
    return None

def decode_base64_image(base64_string):
    """Decode base64 image string to numpy array"""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return np.array(image)
    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")

def extract_faces_from_image(image_array):
    """Extract all face encodings from an image"""
    try:
        face_locations = face_recognition.face_locations(image_array, model='hog')
        
        if not face_locations:
            return []
        
        # Use large model for better accuracy in recognition
        model = os.getenv('FACE_ENCODING_MODEL', 'large')
        face_encodings = face_recognition.face_encodings(image_array, face_locations, model=model)
        return face_encodings
    except Exception as e:
        raise ValueError(f"Face extraction failed: {str(e)}")

def match_faces_with_students_vector_db(face_encodings, class_id, tolerance=0.6):
    """Match detected faces with enrolled students using vector database"""
    try:
        vector_db = get_vector_db()
        if not vector_db:
            return match_faces_with_students_fallback(face_encodings, class_id, tolerance)
        
        # Get enrolled students for this class
        enrolled_students = db.session.query(User.id, User.first_name, User.last_name, User.email).join(
            ClassEnrollment, User.id == ClassEnrollment.student_id
        ).filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.is_active == True,
            User.is_active == True
        ).all()
        
        enrolled_student_ids = set(student.id for student in enrolled_students)
        recognized_students = []
        
        for face_encoding in face_encodings:
            try:
                # Search for similar faces in vector database
                matches = vector_db.find_similar_faces(
                    face_encoding,
                    top_k=10,
                    threshold=tolerance
                )
                
                # Filter matches to only enrolled students in this class
                for match in matches:
                    user_id = match['user_id']
                    if user_id in enrolled_student_ids:
                        # Find student details
                        student = next((s for s in enrolled_students if s.id == user_id), None)
                        if student:
                            student_data = {
                                'id': student.id,
                                'name': f"{student.first_name} {student.last_name}",
                                'email': student.email,
                                'confidence': match['similarity'],
                                'recognition_method': 'vector_db'
                            }
                            
                            # Avoid duplicates
                            if not any(s['id'] == student.id for s in recognized_students):
                                recognized_students.append(student_data)
                        break  # Only take the best match per face
                        
            except Exception as e:
                print(f"Warning: Vector DB search failed for a face: {e}")
                continue
        
        return sorted(recognized_students, key=lambda x: x['confidence'], reverse=True)
        
    except Exception as e:
        print(f"Warning: Vector DB matching failed, using fallback: {e}")
        return match_faces_with_students_fallback(face_encodings, class_id, tolerance)

def match_faces_with_students_fallback(face_encodings, class_id, tolerance=0.6):
    """Fallback method using traditional face_recognition library"""
    try:
        # Get all enrolled students with face data for this class
        enrolled_students = db.session.query(
            User, FaceData, ClassEnrollment
        ).join(
            ClassEnrollment, User.id == ClassEnrollment.student_id
        ).join(
            FaceData, User.id == FaceData.user_id
        ).filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.is_active == True,
            FaceData.is_active == True,
            User.is_active == True
        ).all()
        
        if not enrolled_students:
            return []
        
        # Try to get encodings from vector DB first, then fallback to stored metadata
        known_face_encodings = []
        student_info = []
        
        vector_db = get_vector_db()
        
        for user, face_data, enrollment in enrolled_students:
            try:
                encoding = None
                
                # Try to get from vector DB
                if vector_db and face_data.vector_db_id:
                    try:
                        vector_data = vector_db.get_face_encoding(user.id)
                        if vector_data and 'encoding' in vector_data:
                            encoding = vector_data['encoding']
                    except:
                        pass
                
                # Fallback to metadata if available (though this is not ideal)
                if encoding is None and face_data.encoding_metadata:
                    # This is a fallback - ideally we should have encodings in vector DB
                    print(f"Warning: No vector encoding found for user {user.id}, skipping")
                    continue
                
                if encoding is not None:
                    known_face_encodings.append(encoding)
                    student_info.append({
                        'id': user.id,
                        'name': f"{user.first_name} {user.last_name}",
                        'email': user.email
                    })
                    
            except Exception as e:
                print(f"Warning: Could not process encoding for user {user.id}: {e}")
                continue
        
        if not known_face_encodings:
            return []
        
        # Match faces
        recognized_students = []
        
        for face_encoding in face_encodings:
            # Compare with known faces
            matches = face_recognition.compare_faces(
                known_face_encodings, 
                face_encoding, 
                tolerance=tolerance
            )
            
            # Find the best match
            if True in matches:
                # Calculate face distances for confidence
                face_distances = face_recognition.face_distance(
                    known_face_encodings, 
                    face_encoding
                )
                
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    confidence = 1 - face_distances[best_match_index]
                    
                    student = student_info[best_match_index].copy()
                    student['confidence'] = float(confidence)
                    student['recognition_method'] = 'fallback'
                    
                    # Avoid duplicates
                    if not any(s['id'] == student['id'] for s in recognized_students):
                        recognized_students.append(student)
        
        return sorted(recognized_students, key=lambda x: x['confidence'], reverse=True)
    
    except Exception as e:
        raise ValueError(f"Face matching failed: {str(e)}")

@attendance_bp.route('/recognize-faces', methods=['POST'])
@jwt_required()
def recognize_faces():
    """Process images and identify students from a specific class (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can recognize faces for attendance'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('class_id'):
            return jsonify({'error': 'Class ID is required'}), 400
        
        if not data.get('images') or not isinstance(data['images'], list):
            return jsonify({'error': 'Images array is required'}), 400
        
        class_id = data['class_id']
        tolerance = float(data.get('tolerance', os.getenv('FACE_RECOGNITION_TOLERANCE', 0.6)))
        
        # Verify teacher owns this class
        class_obj = Class.query.filter_by(id=class_id, teacher_id=current_user.id, is_active=True).first()
        if not class_obj:
            return jsonify({'error': 'Class not found or access denied'}), 404
        
        all_recognized_students = []
        processed_images = 0
        total_faces_detected = 0
        recognition_method = None
        
        # Process each image
        for i, image_data in enumerate(data['images']):
            try:
                # Decode image
                image_array = decode_base64_image(image_data)
                
                # Extract faces from image
                face_encodings = extract_faces_from_image(image_array)
                total_faces_detected += len(face_encodings)
                
                if face_encodings:
                    # Match faces with enrolled students using vector DB
                    recognized_students = match_faces_with_students_vector_db(
                        face_encodings, 
                        class_id, 
                        tolerance
                    )
                    
                    if recognized_students and recognition_method is None:
                        recognition_method = recognized_students[0].get('recognition_method', 'unknown')
                    
                    # Add to overall list (avoiding duplicates)
                    for student in recognized_students:
                        existing_student = next(
                            (s for s in all_recognized_students if s['id'] == student['id']), 
                            None
                        )
                        
                        if existing_student:
                            # Update with higher confidence if found
                            if student['confidence'] > existing_student['confidence']:
                                existing_student.update(student)
                        else:
                            all_recognized_students.append(student)
                
                processed_images += 1
                
            except ValueError as e:
                # Skip this image and continue
                continue
            except Exception as e:
                print(f"Warning: Error processing image {i}: {e}")
                continue
        
        if processed_images == 0:
            return jsonify({'error': 'No valid images to process'}), 400
        
        # Sort by confidence
        all_recognized_students.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Get vector DB status
        vector_db = get_vector_db()
        vector_db_stats = vector_db.get_stats() if vector_db else {}
        
        return jsonify({
            'message': f'Face recognition completed. Found {len(all_recognized_students)} students.',
            'class_id': class_id,
            'class_name': class_obj.name,
            'recognized_students': all_recognized_students,
            'images_processed': processed_images,
            'total_faces_detected': total_faces_detected,
            'recognition_method': recognition_method or 'vector_db',
            'tolerance_used': tolerance,
            'vector_db_status': {
                'enabled': vector_db is not None,
                'stats': vector_db_stats
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@attendance_bp.route('/create-session', methods=['POST'])
@jwt_required()
def create_attendance_session():
    """Create a new attendance session for a class (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can create attendance sessions'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('class_id'):
            return jsonify({'error': 'Class ID is required'}), 400
        
        if not data.get('session_name'):
            return jsonify({'error': 'Session name is required'}), 400
        
        class_id = data['class_id']
        
        # Verify teacher owns this class
        class_obj = Class.query.filter_by(id=class_id, teacher_id=current_user.id, is_active=True).first()
        if not class_obj:
            return jsonify({'error': 'Class not found or access denied'}), 404
        
        # Parse session date
        session_date = date.today()
        if data.get('session_date'):
            try:
                session_date = datetime.strptime(data['session_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create attendance session
        session = AttendanceSession(
            class_id=class_id,
            session_name=data['session_name'],
            session_date=session_date,
            created_by=current_user.id
        )
        
        # Set initial counts
        session.total_students = ClassEnrollment.query.filter_by(
            class_id=class_id, 
            is_active=True
        ).count()
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'message': 'Attendance session created successfully',
            'session': session.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@attendance_bp.route('/mark-attendance', methods=['POST'])
@jwt_required()
def mark_attendance():
    """Mark attendance for students in a specific session (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can mark attendance'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('session_id'):
            return jsonify({'error': 'Session ID is required'}), 400
        
        if not data.get('student_ids') or not isinstance(data['student_ids'], list):
            return jsonify({'error': 'Student IDs array is required'}), 400
        
        session_id = data['session_id']
        student_ids = data['student_ids']
        recognition_method = data.get('recognition_method', 'manual')
        confidence_scores = data.get('confidence_scores', {})  # Optional confidence scores
        
        # Verify session exists and teacher has access
        session = AttendanceSession.query.join(Class).filter(
            AttendanceSession.id == session_id,
            Class.teacher_id == current_user.id,
            AttendanceSession.is_active == True
        ).first()
        
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        marked_students = []
        already_marked = []
        invalid_students = []
        
        for student_id in student_ids:
            # Verify student is enrolled in the class
            enrollment = ClassEnrollment.query.filter_by(
                student_id=student_id,
                class_id=session.class_id,
                is_active=True
            ).first()
            
            if not enrollment:
                invalid_students.append(student_id)
                continue
            
            # Check if attendance already marked for this student in this session
            existing_record = AttendanceRecord.query.filter_by(
                session_id=session_id,
                student_id=student_id
            ).first()
            
            if existing_record:
                already_marked.append({
                    'student_id': student_id,
                    'student_name': f"{enrollment.student.first_name} {enrollment.student.last_name}",
                    'status': existing_record.status
                })
                continue
            
            # Get confidence score for this student
            confidence = confidence_scores.get(str(student_id))
            
            # Create attendance record
            attendance_record = AttendanceRecord(
                session_id=session_id,
                student_id=student_id,
                status='present',
                marked_by=current_user.id,
                recognition_method=recognition_method,
                recognition_confidence=confidence
            )
            
            db.session.add(attendance_record)
            marked_students.append({
                'student_id': student_id,
                'student_name': f"{enrollment.student.first_name} {enrollment.student.last_name}",
                'status': 'present',
                'confidence': confidence,
                'recognition_method': recognition_method
            })
        
        # Update session attendance counts
        session.update_attendance_counts()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Attendance marked for {len(marked_students)} students',
            'session_id': session_id,
            'session_name': session.session_name,
            'marked_students': marked_students,
            'already_marked': already_marked,
            'invalid_students': invalid_students,
            'summary': {
                'total_requested': len(student_ids),
                'newly_marked': len(marked_students),
                'already_marked': len(already_marked),
                'invalid': len(invalid_students)
            },
            'session_stats': {
                'total_students': session.total_students,
                'present_count': session.present_count,
                'absent_count': session.absent_count
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@attendance_bp.route('/sessions/<int:class_id>', methods=['GET'])
@jwt_required()
def get_class_sessions(class_id):
    """Get all attendance sessions for a class"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check access to class
        if current_user.role == 'teacher':
            class_obj = Class.query.filter_by(id=class_id, teacher_id=current_user.id, is_active=True).first()
        else:
            # Student can view sessions for classes they're enrolled in
            enrollment = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                class_id=class_id,
                is_active=True
            ).first()
            class_obj = enrollment.class_ref if enrollment else None
        
        if not class_obj:
            return jsonify({'error': 'Class not found or access denied'}), 404
        
        # Get sessions
        sessions = AttendanceSession.query.filter_by(
            class_id=class_id,
            is_active=True
        ).order_by(AttendanceSession.session_date.desc()).all()
        
        sessions_data = []
        for session in sessions:
            session_dict = session.to_dict()
            
            # Add attendance count for this session
            if current_user.role == 'teacher':
                # Teacher sees all attendance records
                attendance_count = AttendanceRecord.query.filter_by(session_id=session.id).count()
                session_dict['attendance_count'] = attendance_count
            else:
                # Student sees only their own attendance
                student_attendance = AttendanceRecord.query.filter_by(
                    session_id=session.id,
                    student_id=current_user.id
                ).first()
                session_dict['my_attendance'] = student_attendance.to_dict() if student_attendance else None
            
            sessions_data.append(session_dict)
        
        return jsonify({
            'class_id': class_id,
            'class_name': class_obj.name,
            'sessions': sessions_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@attendance_bp.route('/session/<int:session_id>/records', methods=['GET'])
@jwt_required()
def get_session_attendance(session_id):
    """Get attendance records for a specific session"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get session and verify access
        if current_user.role == 'teacher':
            session = AttendanceSession.query.join(Class).filter(
                AttendanceSession.id == session_id,
                Class.teacher_id == current_user.id,
                AttendanceSession.is_active == True
            ).first()
        else:
            # Student can view session if they're enrolled in the class
            session = AttendanceSession.query.join(Class).join(ClassEnrollment).filter(
                AttendanceSession.id == session_id,
                ClassEnrollment.student_id == current_user.id,
                ClassEnrollment.is_active == True,
                AttendanceSession.is_active == True
            ).first()
        
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get attendance records
        if current_user.role == 'teacher':
            # Teacher sees all records
            records = AttendanceRecord.query.filter_by(session_id=session_id).all()
            records_data = [record.to_dict() for record in records]
        else:
            # Student sees only their own record
            record = AttendanceRecord.query.filter_by(
                session_id=session_id,
                student_id=current_user.id
            ).first()
            records_data = [record.to_dict()] if record else []
        
        # Calculate statistics
        total_present = len([r for r in records_data if r['status'] == 'present'])
        total_absent = len([r for r in records_data if r['status'] == 'absent'])
        
        return jsonify({
            'session': session.to_dict(),
            'attendance_records': records_data,
            'statistics': {
                'total_present': total_present,
                'total_absent': total_absent,
                'total_enrolled': session.total_students,
                'attendance_rate': (total_present / session.total_students * 100) if session.total_students > 0 else 0
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500