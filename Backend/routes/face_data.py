from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import User, FaceData, db
import face_recognition
import numpy as np
import base64
import json
import cv2
from PIL import Image
import io
import os

face_data_bp = Blueprint('face_data', __name__)

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
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64 string
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        return image_array
    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")

def extract_face_encoding(image_array, model='large'):
    """Extract face encoding from image array"""
    try:
        # Use model specified in environment or default
        face_model = os.getenv('FACE_ENCODING_MODEL', model)
        
        # Find face locations in the image
        face_locations = face_recognition.face_locations(image_array, model='hog')
        
        if not face_locations:
            raise ValueError("No face detected in the image")
        
        if len(face_locations) > 1:
            raise ValueError("Multiple faces detected. Please use an image with only one face")
        
        # Extract face encoding with specified model
        face_encodings = face_recognition.face_encodings(
            image_array, 
            face_locations, 
            model=face_model
        )
        
        if not face_encodings:
            raise ValueError("Could not extract face encoding")
        
        return face_encodings[0]
    except Exception as e:
        raise ValueError(f"Face encoding extraction failed: {str(e)}")

def save_image_file(image_array, user_id):
    """Save image file to uploads directory"""
    try:
        # Create uploads directory if it doesn't exist
        uploads_dir = 'uploads/face_images'
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{user_id}_{timestamp}.jpg"
        filepath = os.path.join(uploads_dir, filename)
        
        # Save image
        image = Image.fromarray(image_array)
        image.save(filepath, 'JPEG', quality=90)
        
        return filepath
    except Exception as e:
        return None

@face_data_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_face_data():
    """Upload and process face data for current user (Student only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403
        
        data = request.get_json()
        
        if not data.get('image'):
            return jsonify({'error': 'Image data is required'}), 400
        
        # Decode image
        try:
            image_array = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Extract face encoding
        try:
            face_encoding = extract_face_encoding(image_array)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Save image file (optional)
        image_path = save_image_file(image_array, current_user.id)
        
        # Get vector database service
        vector_db = get_vector_db()
        
        # Check if user already has face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        # Prepare metadata for vector database
        metadata = {
            'user_id': current_user.id,
            'user_name': f"{current_user.first_name} {current_user.last_name}",
            'email': current_user.email,
            'encoding_version': 'v1.0',
            'upload_method': 'single_image'
        }
        
        vector_db_id = None
        
        if vector_db:
            try:
                if existing_face_data and existing_face_data.vector_db_id:
                    # Update existing encoding in vector DB
                    success = vector_db.update_face_encoding(
                        current_user.id, 
                        face_encoding, 
                        metadata
                    )
                    vector_db_id = existing_face_data.vector_db_id
                    
                    if not success:
                        # If update fails, add as new
                        vector_db_id = vector_db.add_face_encoding(
                            current_user.id,
                            face_encoding,
                            metadata
                        )
                else:
                    # Add new encoding to vector DB
                    vector_db_id = vector_db.add_face_encoding(
                        current_user.id,
                        face_encoding,
                        metadata
                    )
                    
            except Exception as e:
                print(f"Warning: Vector DB operation failed: {e}")
                # Continue without vector DB
        
        if existing_face_data:
            # Update existing face data
            existing_face_data.vector_db_id = vector_db_id
            existing_face_data.encoding_metadata = metadata
            existing_face_data.image_path = image_path
            existing_face_data.encoding_version = 'v1.0'
            db.session.commit()
            
            return jsonify({
                'message': 'Face data updated successfully',
                'face_data': existing_face_data.to_dict(),
                'vector_db_enabled': vector_db is not None
            }), 200
        else:
            # Create new face data
            face_data = FaceData(
                user_id=current_user.id,
                vector_db_id=vector_db_id,
                encoding_metadata=metadata,
                image_path=image_path,
                encoding_version='v1.0'
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            return jsonify({
                'message': 'Face data uploaded successfully',
                'face_data': face_data.to_dict(),
                'vector_db_enabled': vector_db is not None
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/multiple-upload', methods=['POST'])
@jwt_required()
def upload_multiple_face_data():
    """Upload multiple face images for better recognition accuracy"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403
        
        data = request.get_json()
        
        if not data.get('images') or not isinstance(data['images'], list):
            return jsonify({'error': 'Images array is required'}), 400
        
        if len(data['images']) < 2 or len(data['images']) > 5:
            return jsonify({'error': 'Please provide 2-5 images for better accuracy'}), 400
        
        face_encodings = []
        successful_uploads = 0
        
        # Process each image
        for i, image_data in enumerate(data['images']):
            try:
                # Decode image
                image_array = decode_base64_image(image_data)
                
                # Extract face encoding
                face_encoding = extract_face_encoding(image_array)
                face_encodings.append(face_encoding)
                successful_uploads += 1
                
                # Save first image as reference
                if i == 0:
                    image_path = save_image_file(image_array, current_user.id)
                
            except ValueError as e:
                # Skip this image and continue with others
                continue
        
        if successful_uploads == 0:
            return jsonify({'error': 'No valid face images found'}), 400
        
        # Calculate average face encoding for better accuracy
        if len(face_encodings) > 1:
            average_encoding = np.mean(face_encodings, axis=0)
            # Normalize the averaged encoding
            average_encoding = average_encoding / np.linalg.norm(average_encoding)
        else:
            average_encoding = face_encodings[0]
        
        # Get vector database service
        vector_db = get_vector_db()
        
        # Prepare metadata
        metadata = {
            'user_id': current_user.id,
            'user_name': f"{current_user.first_name} {current_user.last_name}",
            'email': current_user.email,
            'encoding_version': 'v1.0',
            'upload_method': 'multiple_images',
            'images_processed': successful_uploads
        }
        
        # Update or create face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        vector_db_id = None
        
        if vector_db:
            try:
                if existing_face_data and existing_face_data.vector_db_id:
                    # Update existing encoding
                    success = vector_db.update_face_encoding(
                        current_user.id,
                        average_encoding,
                        metadata
                    )
                    vector_db_id = existing_face_data.vector_db_id
                    
                    if not success:
                        vector_db_id = vector_db.add_face_encoding(
                            current_user.id,
                            average_encoding,
                            metadata
                        )
                else:
                    # Add new encoding
                    vector_db_id = vector_db.add_face_encoding(
                        current_user.id,
                        average_encoding,
                        metadata
                    )
                    
            except Exception as e:
                print(f"Warning: Vector DB operation failed: {e}")
        
        if existing_face_data:
            existing_face_data.vector_db_id = vector_db_id
            existing_face_data.encoding_metadata = metadata
            existing_face_data.image_path = image_path if 'image_path' in locals() else existing_face_data.image_path
            db.session.commit()
            
            return jsonify({
                'message': f'Face data updated successfully using {successful_uploads} images',
                'face_data': existing_face_data.to_dict(),
                'images_processed': successful_uploads,
                'vector_db_enabled': vector_db is not None
            }), 200
        else:
            face_data = FaceData(
                user_id=current_user.id,
                vector_db_id=vector_db_id,
                encoding_metadata=metadata,
                image_path=image_path if 'image_path' in locals() else None
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            return jsonify({
                'message': f'Face data uploaded successfully using {successful_uploads} images',
                'face_data': face_data.to_dict(),
                'images_processed': successful_uploads,
                'vector_db_enabled': vector_db is not None
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/my-data', methods=['GET'])
@jwt_required()
def get_my_face_data():
    """Get current user's face data"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        vector_db = get_vector_db()
        vector_db_status = None
        
        if face_data and vector_db and face_data.vector_db_id:
            try:
                # Check if encoding exists in vector DB
                vector_data = vector_db.get_face_encoding(current_user.id)
                vector_db_status = 'connected' if vector_data else 'not_found'
            except Exception as e:
                vector_db_status = f'error: {str(e)}'
        
        if not face_data:
            return jsonify({
                'message': 'No face data found',
                'has_face_data': False,
                'vector_db_enabled': vector_db is not None,
                'vector_db_status': vector_db_status
            }), 200
        
        response_data = face_data.to_dict()
        response_data.update({
            'has_face_data': True,
            'vector_db_enabled': vector_db is not None,
            'vector_db_status': vector_db_status
        })
        
        return jsonify({
            'face_data': response_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_face_data():
    """Delete current user's face data"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({'error': 'No face data found'}), 404
        
        # Delete from vector database
        vector_db = get_vector_db()
        if vector_db and face_data.vector_db_id:
            try:
                vector_db.delete_face_encoding(current_user.id)
            except Exception as e:
                print(f"Warning: Failed to delete from vector DB: {e}")
        
        # Deactivate face data instead of deleting
        face_data.is_active = False
        
        # Delete image file if exists
        if face_data.image_path and os.path.exists(face_data.image_path):
            try:
                os.remove(face_data.image_path)
            except:
                pass  # Ignore file deletion errors
        
        db.session.commit()
        
        return jsonify({
            'message': 'Face data deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_face_data_stats():
    """Get face data statistics (Teacher only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can view face data statistics'}), 403
        
        # Get vector database stats
        vector_db = get_vector_db()
        vector_stats = vector_db.get_stats() if vector_db else {}
        
        # Get general statistics
        total_students = User.query.filter_by(role='student', is_active=True).count()
        students_with_face_data = FaceData.query.filter_by(is_active=True).count()
        
        return jsonify({
            'total_students': total_students,
            'students_with_face_data': students_with_face_data,
            'face_data_coverage': (students_with_face_data / total_students * 100) if total_students > 0 else 0,
            'vector_database': vector_stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_face_data():
    """Upload and process face data for current user (Student only)"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403
        
        data = request.get_json()
        
        if not data.get('image'):
            return jsonify({'error': 'Image data is required'}), 400
        
        # Decode image
        try:
            image_array = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Extract face encoding
        try:
            face_encoding = extract_face_encoding(image_array)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Save image file (optional)
        image_path = save_image_file(image_array, current_user.id)
        
        # Convert face encoding to JSON string for storage
        face_encoding_json = json.dumps(face_encoding.tolist())
        
        # Check if user already has face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if existing_face_data:
            # Update existing face data
            existing_face_data.face_encoding = face_encoding_json
            existing_face_data.image_path = image_path
            db.session.commit()
            
            return jsonify({
                'message': 'Face data updated successfully',
                'face_data': existing_face_data.to_dict()
            }), 200
        else:
            # Create new face data
            face_data = FaceData(
                user_id=current_user.id,
                face_encoding=face_encoding_json,
                image_path=image_path
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            return jsonify({
                'message': 'Face data uploaded successfully',
                'face_data': face_data.to_dict()
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/my-data', methods=['GET'])
@jwt_required()
def get_my_face_data():
    """Get current user's face data"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({
                'message': 'No face data found',
                'has_face_data': False
            }), 200
        
        return jsonify({
            'face_data': face_data.to_dict(),
            'has_face_data': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_face_data():
    """Delete current user's face data"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({'error': 'No face data found'}), 404
        
        # Deactivate face data instead of deleting
        face_data.is_active = False
        
        # Delete image file if exists
        if face_data.image_path and os.path.exists(face_data.image_path):
            try:
                os.remove(face_data.image_path)
            except:
                pass  # Ignore file deletion errors
        
        db.session.commit()
        
        return jsonify({
            'message': 'Face data deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/multiple-upload', methods=['POST'])
@jwt_required()
def upload_multiple_face_data():
    """Upload multiple face images for better recognition accuracy"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403
        
        data = request.get_json()
        
        if not data.get('images') or not isinstance(data['images'], list):
            return jsonify({'error': 'Images array is required'}), 400
        
        if len(data['images']) < 2 or len(data['images']) > 5:
            return jsonify({'error': 'Please provide 2-5 images for better accuracy'}), 400
        
        face_encodings = []
        successful_uploads = 0
        
        # Process each image
        for i, image_data in enumerate(data['images']):
            try:
                # Decode image
                image_array = decode_base64_image(image_data)
                
                # Extract face encoding
                face_encoding = extract_face_encoding(image_array)
                face_encodings.append(face_encoding)
                successful_uploads += 1
                
            except ValueError as e:
                # Skip this image and continue with others
                continue
        
        if successful_uploads == 0:
            return jsonify({'error': 'No valid face images found'}), 400
        
        # Calculate average face encoding for better accuracy
        if len(face_encodings) > 1:
            average_encoding = np.mean(face_encodings, axis=0)
        else:
            average_encoding = face_encodings[0]
        
        # Convert to JSON string for storage
        face_encoding_json = json.dumps(average_encoding.tolist())
        
        # Update or create face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if existing_face_data:
            existing_face_data.face_encoding = face_encoding_json
            db.session.commit()
            
            return jsonify({
                'message': f'Face data updated successfully using {successful_uploads} images',
                'face_data': existing_face_data.to_dict(),
                'images_processed': successful_uploads
            }), 200
        else:
            face_data = FaceData(
                user_id=current_user.id,
                face_encoding=face_encoding_json
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            return jsonify({
                'message': f'Face data uploaded successfully using {successful_uploads} images',
                'face_data': face_data.to_dict(),
                'images_processed': successful_uploads
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500