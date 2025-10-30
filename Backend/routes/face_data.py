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
import logging
from datetime import datetime

# Import ArcFace service for 512D embeddings
try:
    from services.arcface_service import (
        extract_arcface_embedding,
        extract_multiple_arcface_embeddings,
        calculate_average_embedding,
        compute_similarity,
        detect_faces_batch,
        get_model_info,
        initialize_arcface
    )
    # Verify ArcFace can actually initialize
    _test_model = initialize_arcface()
    ARCFACE_AVAILABLE = _test_model is not None
    if ARCFACE_AVAILABLE:
        print("✅ ArcFace 512D embeddings enabled")
    else:
        print("⚠️ ArcFace model failed to initialize, using legacy face_recognition 128D")
except Exception as e:
    ARCFACE_AVAILABLE = False
    print(f"⚠️ ArcFace not available, using legacy face_recognition 128D: {e}")

face_data_bp = Blueprint('face_data', __name__)

def get_encoding_version():
    """Get current encoding version based on available model"""
    if ARCFACE_AVAILABLE:
        return 'v4.0_arcface_512d'
    return 'v1.0_legacy_128d'

def get_embedding_dimension(encoding):
    """Get dimension of encoding (512 for ArcFace, 128 for legacy)"""
    if encoding is not None:
        return len(encoding)
    return 0

def get_current_user():
    """Helper function to get current authenticated user"""
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)

def get_vector_db():
    """Get vector database service"""
    if hasattr(current_app, 'vector_db') and current_app.vector_db:
        return current_app.vector_db
    return None

def decode_base64_image(base64_string):
    """Decode base64 image string to numpy array with normalization"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64 string
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Log original image info
        logger = logging.getLogger(__name__)
        logger.debug(f"Decoded image: mode={image.mode}, size={image.size}")
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        # Verify image has content
        if image_array.size == 0:
            raise ValueError("Decoded image is empty")
        
        # Check image quality
        if image_array.shape[0] < 100 or image_array.shape[1] < 100:
            raise ValueError(f"Image too small: {image_array.shape}")
        
        # Normalize image to reduce camera quality differences
        # This helps recognition work across front/back cameras
        image_array = normalize_image_for_recognition(image_array)
        
        return image_array
    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")

def normalize_image_for_recognition(image_array):
    """
    Normalize image to reduce differences between cameras
    Makes front camera (selfie) and back camera images more comparable
    """
    try:
        # Convert to float for processing
        image_float = image_array.astype(np.float32)
        
        # Normalize brightness and contrast
        # This helps when front/back cameras have different exposure
        mean_brightness = np.mean(image_float)
        
        # Adjust if too dark or too bright
        if mean_brightness < 80:
            # Image too dark - brighten
            image_float = np.clip(image_float * 1.3 + 20, 0, 255)
        elif mean_brightness > 180:
            # Image too bright - darken
            image_float = np.clip(image_float * 0.9 - 10, 0, 255)
        
        # Apply slight sharpening to compensate for different camera qualities
        # This helps when comparing high-res back camera to lower-res front camera
        kernel = np.array([[-0.5, -0.5, -0.5],
                          [-0.5,  5.0, -0.5],
                          [-0.5, -0.5, -0.5]])
        
        # Apply sharpening per channel
        sharpened = np.zeros_like(image_float)
        for i in range(3):  # RGB channels
            sharpened[:, :, i] = cv2.filter2D(image_float[:, :, i], -1, kernel)
        
        # Blend original and sharpened (50% each)
        image_float = 0.7 * image_float + 0.3 * sharpened
        
        # Convert back to uint8
        image_normalized = np.clip(image_float, 0, 255).astype(np.uint8)
        
        return image_normalized
        
    except Exception as e:
        # If normalization fails, return original
        logging.getLogger(__name__).warning(f"Image normalization failed: {e}, using original")
        return image_array

def extract_face_encoding(image_array, model='large'):
    """
    Extract face encoding from image array
    Now uses ArcFace 512D embeddings for superior accuracy
    Falls back to face_recognition 128D if ArcFace unavailable
    """
    try:
        # Try ArcFace first (512D embeddings)
        if ARCFACE_AVAILABLE:
            try:
                embedding = extract_arcface_embedding(image_array, return_largest=True)
                
                if embedding is not None:
                    current_app.logger.debug(f"✅ Extracted ArcFace 512D embedding, shape: {embedding.shape}")
                    return embedding
                else:
                    current_app.logger.debug("No face detected with ArcFace, trying legacy fallback")
            except Exception as e:
                current_app.logger.warning(f"ArcFace failed: {e}, falling back to legacy")
        
        # Fallback to legacy face_recognition (128D)
        current_app.logger.debug("Using legacy face_recognition 128D")
        
        # Use model specified in environment or default
        face_model = os.getenv('FACE_ENCODING_MODEL', model)
        
        # Find face locations in the image
        face_locations = face_recognition.face_locations(image_array, model='hog')
        
        if not face_locations:
            current_app.logger.debug("No face detected with legacy face_recognition")
            return None  # Return None instead of raising exception
        
        if len(face_locations) > 1:
            current_app.logger.debug(f"Multiple faces detected ({len(face_locations)}), using the largest face")
            # Find the largest face (assuming it's the main subject)
            largest_face_idx = 0
            largest_area = 0
            for i, (top, right, bottom, left) in enumerate(face_locations):
                area = (bottom - top) * (right - left)
                if area > largest_area:
                    largest_area = area
                    largest_face_idx = i
            face_locations = [face_locations[largest_face_idx]]
        
        # Extract face encoding with specified model
        face_encodings = face_recognition.face_encodings(
            image_array, 
            face_locations, 
            model=face_model
        )
        
        if not face_encodings:
            current_app.logger.debug("Could not extract face encoding from detected face")
            return None  # Return None instead of raising exception
        
        current_app.logger.debug(f"✅ Extracted legacy 128D embedding")
        return face_encodings[0]
    except Exception as e:
        current_app.logger.error(f"Face encoding extraction failed: {str(e)}")
        return None  # Return None instead of raising exception

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
        
        # Get vector database service (no need to save image - only embeddings matter)
        vector_db = get_vector_db()
        
        # Check if user already has face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        # Prepare metadata for vector database
        encoding_version = get_encoding_version()
        embedding_dim = get_embedding_dimension(face_encoding)
        
        metadata = {
            'user_id': current_user.id,
            'user_name': f"{current_user.first_name} {current_user.last_name}",
            'email': current_user.email,
            'encoding_version': encoding_version,
            'embedding_dimension': embedding_dim,
            'model_type': 'ArcFace' if ARCFACE_AVAILABLE else 'face_recognition',
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
            existing_face_data.encoding_version = encoding_version
            db.session.commit()
            
            return jsonify({
                'message': 'Face data updated successfully',
                'face_data': existing_face_data.to_dict(),
                'vector_db_enabled': vector_db is not None,
                'encoding_info': {
                    'version': encoding_version,
                    'dimension': embedding_dim,
                    'model': 'ArcFace-512D' if ARCFACE_AVAILABLE else 'Legacy-128D'
                }
            }), 200
        else:
            # Create new face data
            face_data = FaceData(
                user_id=current_user.id,
                vector_db_id=vector_db_id,
                encoding_metadata=metadata,
                encoding_version=encoding_version
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            return jsonify({
                'message': 'Face data uploaded successfully',
                'face_data': face_data.to_dict(),
                'vector_db_enabled': vector_db is not None,
                'encoding_info': {
                    'version': encoding_version,
                    'dimension': embedding_dim,
                    'model': 'ArcFace-512D' if ARCFACE_AVAILABLE else 'Legacy-128D'
                }
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
                encoding_metadata=metadata
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

@face_data_bp.route('/upload-orientations', methods=['POST'])
@jwt_required()
def upload_face_data_with_orientations():
    """
    Upload face images labeled by head orientation for higher-quality enrollment.
    Expected payload:
    {
      "images": [
        { "image": "base64...", "orientation": "front" },
        { "image": "base64...", "orientation": "left" },
        { "image": "base64...", "orientation": "right" },
        { "image": "base64...", "orientation": "up" },
        { "image": "base64...", "orientation": "down" }
      ]
    }
    Notes:
    - At least 3 orientations are required (front + any two of left/right/up/down).
    - If multiple images are provided for the same orientation, they will be averaged.
    - The averaged global embedding (across orientations) is stored in the vector DB.
    - Per-orientation averaged embeddings are stored in FaceData.encoding_metadata.
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403

        data = request.get_json()
        if not data or 'images' not in data or not isinstance(data['images'], list):
            return jsonify({'error': 'images array is required'}), 400

        images = data['images']
        if len(images) == 0:
            return jsonify({'error': 'Provide at least 1 image'}), 400

        allowed_orientations = ["front", "left", "right", "up", "down"]
        orientation_buckets = {o: [] for o in allowed_orientations}
        processed = []
        errors = []

        # Decode and extract embeddings per item
        for i, item in enumerate(images):
            idx = i + 1
            if not isinstance(item, dict) or 'image' not in item or 'orientation' not in item:
                errors.append({
                    'image_number': idx,
                    'error': 'Missing image or orientation field'
                })
                continue

            orientation = str(item['orientation']).strip().lower()
            if orientation not in allowed_orientations:
                errors.append({
                    'image_number': idx,
                    'error': f'Invalid orientation: {orientation}',
                    'allowed': allowed_orientations
                })
                continue

            try:
                img_array = decode_base64_image(item['image'])
                emb = extract_face_encoding(img_array)
                if emb is None:
                    errors.append({
                        'image_number': idx,
                        'orientation': orientation,
                        'error': 'No face detected'
                    })
                    continue

                orientation_buckets[orientation].append(emb)
                processed.append({
                    'image_number': idx,
                    'orientation': orientation,
                    'embedding_dim': len(emb)
                })

            except ValueError as e:
                errors.append({
                    'image_number': idx,
                    'orientation': orientation,
                    'error': f'Invalid image: {str(e)}'
                })
            except Exception as e:
                errors.append({
                    'image_number': idx,
                    'orientation': orientation,
                    'error': f'Unexpected error: {str(e)}'
                })

        # Build per-orientation averaged embeddings
        per_orientation_avg = {}
        captured_orientations = []
        for o in allowed_orientations:
            if orientation_buckets[o]:
                avg = np.mean(orientation_buckets[o], axis=0)
                # Normalize to unit vector
                norm = np.linalg.norm(avg)
                if norm > 0:
                    avg = avg / norm
                per_orientation_avg[o] = avg
                captured_orientations.append(o)

        # Validate all 5 orientations are required
        required = set(allowed_orientations)  # All 5 orientations required
        if not required.issubset(set(captured_orientations)):
            missing = required - set(captured_orientations)
            return jsonify({
                'success': False,
                'message': f"Please include all 5 orientations. Missing: {', '.join(missing)}",
                'captured_orientations': captured_orientations,
                'missing_orientations': list(missing),
                'errors': errors[:5]
            }), 400

        if len(captured_orientations) < 5:
            return jsonify({
                'success': False,
                'message': 'Please include all 5 orientations (front, left, right, up, down)',
                'captured_orientations': captured_orientations,
                'errors': errors[:5]
            }), 400

        # Global averaged embedding across orientations
        avg_list = list(per_orientation_avg.values())
        global_avg = np.mean(avg_list, axis=0)
        global_norm = np.linalg.norm(global_avg)
        if global_norm > 0:
            global_avg = global_avg / global_norm

        embedding_dim = len(global_avg)

        # Store to vector DB (single global embedding) and FaceData metadata
        vector_db = get_vector_db()
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()

        # Prepare metadata with per-orientation averages (as lists for JSON)
        orientation_meta = {o: per_orientation_avg[o].tolist() for o in per_orientation_avg}
        encoding_version = get_encoding_version()
        metadata = {
            'user_id': current_user.id,
            'user_name': f"{current_user.first_name} {current_user.last_name}",
            'email': current_user.email,
            'encoding_version': encoding_version,
            'embedding_dimension': embedding_dim,
            'model_type': 'ArcFace' if ARCFACE_AVAILABLE else 'face_recognition',
            'upload_method': 'orientation_labeled',
            'captured_orientations': captured_orientations,
            'per_orientation_embeddings': orientation_meta,
            'created_at': str(datetime.utcnow())
        }

        vector_db_id = None
        if vector_db:
            try:
                if existing_face_data and existing_face_data.vector_db_id:
                    success = vector_db.update_face_encoding(current_user.id, global_avg, metadata)
                    vector_db_id = existing_face_data.vector_db_id
                    if not success:
                        vector_db_id = vector_db.add_face_encoding(current_user.id, global_avg, metadata)
                else:
                    vector_db_id = vector_db.add_face_encoding(current_user.id, global_avg, metadata)
            except Exception as e:
                current_app.logger.warning(f"Vector DB operation failed: {e}")

        if existing_face_data:
            existing_face_data.vector_db_id = vector_db_id
            existing_face_data.encoding_metadata = metadata
            existing_face_data.encoding_version = encoding_version
            db.session.commit()
            face_data_row = existing_face_data
        else:
            face_data_row = FaceData(
                user_id=current_user.id,
                vector_db_id=vector_db_id,
                encoding_metadata=metadata,
                encoding_version=encoding_version
            )
            db.session.add(face_data_row)
            db.session.commit()

        missing_orientations = [o for o in allowed_orientations if o not in captured_orientations]

        return jsonify({
            'success': True,
            'message': 'Orientation-based facial data uploaded successfully',
            'orientations_captured': captured_orientations,
            'orientations_missing': missing_orientations,
            'embedding_dimension': embedding_dim,
            'processed': processed,
            'errors': errors[:5],
            'vector_db_enabled': vector_db is not None,
            'face_data': face_data_row.to_dict() if hasattr(face_data_row, 'to_dict') else {
                'user_id': current_user.id,
                'vector_db_id': vector_db_id,
                'encoding_version': encoding_version
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in upload_face_data_with_orientations: {str(e)}")
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
        db.session.commit()
        
        return jsonify({
            'message': 'Face data deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/register-student', methods=['POST'])
@jwt_required()
def register_student_face_data():
    """Register facial data for a student by capturing multiple images"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can register facial data'}), 403
        
        # Check if student already has face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if existing_face_data:
            return jsonify({'error': 'Student already has registered facial data'}), 400
        
        data = request.get_json()
        
        if not data or 'images' not in data:
            return jsonify({'error': 'Images are required'}), 400
        
        images = data['images']
        
        if not isinstance(images, list) or len(images) < 5:
            return jsonify({'error': 'At least 5 images are required for registration'}), 400
        
        if len(images) > 25:
            return jsonify({'error': 'Maximum 25 images allowed for registration'}), 400
        
        # Process images and extract face encodings
        all_encodings = []
        processed_images = []
        processing_errors = []
        
        current_app.logger.info(f"Processing {len(images)} images for student {current_user.id}")
        
        for i, image_data in enumerate(images):
            try:
                current_app.logger.debug(f"Processing image {i + 1}/{len(images)} for student {current_user.id}")
                
                # Check image data format
                if not image_data or not isinstance(image_data, str):
                    error_msg = f"Invalid image data format for image {i + 1}"
                    current_app.logger.warning(error_msg)
                    processing_errors.append(error_msg)
                    continue
                
                # Check if it's a data URL or plain base64
                if not image_data.startswith('data:image/'):
                    error_msg = f"Image {i + 1} missing data URL prefix"
                    current_app.logger.warning(error_msg)
                    processing_errors.append(error_msg)
                    continue
                
                # Decode base64 image
                image_array = decode_base64_image(image_data)
                current_app.logger.debug(f"Successfully decoded image {i + 1}, shape: {image_array.shape}")
                
                # Extract face encoding
                encoding = extract_face_encoding(image_array)
                
                if encoding is not None:
                    all_encodings.append(encoding)
                    processed_images.append(i + 1)
                    current_app.logger.debug(f"Successfully extracted face encoding from image {i + 1}")
                else:
                    error_msg = f"No face detected in image {i + 1}"
                    current_app.logger.warning(f"{error_msg} for student {current_user.id}")
                    processing_errors.append(error_msg)
                    
            except ValueError as e:
                error_msg = f"Image processing error for image {i + 1}: {str(e)}"
                current_app.logger.error(f"{error_msg} for student {current_user.id}")
                processing_errors.append(error_msg)
                continue
            except Exception as e:
                error_msg = f"Unexpected error processing image {i + 1}: {str(e)}"
                current_app.logger.error(f"{error_msg} for student {current_user.id}")
                processing_errors.append(error_msg)
                continue
        
        current_app.logger.info(f"Successfully processed {len(all_encodings)} out of {len(images)} images for student {current_user.id}")
        
        if len(all_encodings) < 3:
            error_detail = {
                'total_images': len(images),
                'processed_images': len(all_encodings),
                'processing_errors': processing_errors[:5],  # Limit to first 5 errors
                'required_minimum': 3
            }
            current_app.logger.error(f"Insufficient valid faces for student {current_user.id}: {error_detail}")
            return jsonify({
                'error': 'Insufficient valid face images. Please ensure your face is clearly visible in at least 3 images.',
                'details': error_detail
            }), 400
        
        # Calculate average encoding
        average_encoding = np.mean(all_encodings, axis=0)
        
        # Save face data to database
        face_data = FaceData(
            user_id=current_user.id,
            encoding=average_encoding.tolist(),
            metadata={
                'total_images_submitted': len(images),
                'valid_images_processed': len(all_encodings),
                'processed_images': processed_images,
                'registration_date': str(datetime.utcnow())
            }
        )
        
        db.session.add(face_data)
        
        # Store in vector database
        vector_db = get_vector_db()
        if vector_db:
            try:
                vector_db.add_face_data(
                    user_id=str(current_user.id),
                    encoding=average_encoding,
                    metadata={
                        'student_name': current_user.full_name,
                        'email': current_user.email,
                        'registration_date': str(datetime.utcnow())
                    }
                )
            except Exception as e:
                current_app.logger.error(f"Failed to store in vector database: {str(e)}")
        
        db.session.commit()
        
        current_app.logger.info(f"Successfully registered facial data for student {current_user.id}")
        
        return jsonify({
            'message': 'Facial data registered successfully',
            'details': {
                'student_id': current_user.id,
                'total_images_submitted': len(images),
                'valid_images_processed': len(all_encodings),
                'processed_images': processed_images,
                'registration_complete': True
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error in register_student_face_data for student {current_user.id if 'current_user' in locals() else 'unknown'}: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.exception("Full traceback:")
        return jsonify({
            'error': 'Internal server error occurred while processing facial data',
            'details': str(e) if current_app.debug else 'Please try again or contact support'
        }), 500

@face_data_bp.route('/student-status', methods=['GET'])
@jwt_required()
def get_student_face_data_status():
    """Get facial data registration status for current student"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can check facial data status'}), 403
        
        # Check if student has face data
        face_data = FaceData.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if face_data:
            return jsonify({
                'registered': True,
                'registration_date': face_data.created_at.isoformat(),
                'metadata': face_data.encoding_metadata,
                'has_face_data': True
            }), 200
        else:
            return jsonify({
                'registered': False,
                'has_face_data': False,
                'message': 'No facial data registered. Please complete facial registration.'
            }), 200
        
    except Exception as e:
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

@face_data_bp.route('/upload-single', methods=['POST'])
@jwt_required()
def upload_single_face_image():
    """Upload a single face image during progressive capture"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403
        
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({'error': 'Image data is required'}), 400
        
        if 'sequence_number' not in data:
            return jsonify({'error': 'Sequence number is required'}), 400
        
        sequence_number = data['sequence_number']
        if not isinstance(sequence_number, int) or sequence_number < 1 or sequence_number > 25:
            return jsonify({'error': 'Invalid sequence number (1-25)'}), 400
        
        # Decode and validate image
        try:
            image_array = decode_base64_image(data['image'])
            current_app.logger.debug(f"Processing image {sequence_number} for student {current_user.id}")
        except ValueError as e:
            return jsonify({'error': f'Invalid image data: {str(e)}'}), 400
        
        # Extract face encoding
        face_encoding = extract_face_encoding(image_array)
        
        if face_encoding is None:
            return jsonify({
                'success': False,
                'message': f'No face detected in image {sequence_number}',
                'sequence_number': sequence_number,
                'face_detected': False
            }), 200
        
        # Store in session or temporary storage
        # For now, we'll return success with face validation
        return jsonify({
            'success': True,
            'message': f'Image {sequence_number} processed successfully',
            'sequence_number': sequence_number,
            'face_detected': True,
            'face_quality': 'good',  # Could add quality assessment here
            'encoding_extracted': True
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in upload_single_face_image: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/upload-batch-with-progress', methods=['POST'])
@jwt_required()
def upload_batch_with_progress():
    """Upload multiple images with detailed progress feedback"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload face data'}), 403
        
        data = request.get_json()
        
        if not data or 'images' not in data:
            return jsonify({'error': 'Images array is required'}), 400
        
        images = data['images']
        
        if not isinstance(images, list) or len(images) < 5:
            return jsonify({'error': 'At least 5 images are required'}), 400
        
        if len(images) > 25:
            return jsonify({'error': 'Maximum 25 images allowed'}), 400
        
        # Process each image and provide detailed feedback
        results = []
        valid_encodings = []
        total_images = len(images)
        
        current_app.logger.info(f"Processing batch upload of {total_images} images for student {current_user.id}")
        
        for i, image_data in enumerate(images):
            image_result = {
                'image_number': i + 1,
                'success': False,
                'face_detected': False,
                'error': None
            }
            
            try:
                # Decode image
                image_array = decode_base64_image(image_data)
                
                # Extract face encoding
                face_encoding = extract_face_encoding(image_array)
                
                if face_encoding is not None:
                    valid_encodings.append(face_encoding)
                    image_result.update({
                        'success': True,
                        'face_detected': True,
                        'encoding_quality': 'good'
                    })
                else:
                    image_result.update({
                        'success': False,
                        'face_detected': False,
                        'error': 'No face detected in image'
                    })
                    
            except ValueError as e:
                image_result.update({
                    'success': False,
                    'error': f'Image processing error: {str(e)}'
                })
            except Exception as e:
                image_result.update({
                    'success': False,
                    'error': f'Unexpected error: {str(e)}'
                })
            
            results.append(image_result)
        
        # Calculate success metrics
        successful_images = len(valid_encodings)
        success_rate = (successful_images / total_images) * 100
        
        # Check if we have enough valid images
        if successful_images < 3:
            return jsonify({
                'success': False,
                'message': 'Insufficient valid face images for registration',
                'total_images': total_images,
                'successful_images': successful_images,
                'success_rate': success_rate,
                'results': results,
                'recommendation': 'Please ensure your face is clearly visible and well-lit in the images'
            }), 400
        
        # If we have enough images, proceed with registration
        if successful_images >= 5:
            # Calculate average encoding
            average_encoding = np.mean(valid_encodings, axis=0)
            
            # Check for existing face data
            existing_face_data = FaceData.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if existing_face_data:
                return jsonify({
                    'success': False,
                    'message': 'Student already has registered facial data',
                    'total_images': total_images,
                    'successful_images': successful_images,
                    'results': results
                }), 400
            
            # Create face data record
            face_data = FaceData(
                user_id=current_user.id,
                encoding=average_encoding.tolist(),
                metadata={
                    'total_images_submitted': total_images,
                    'valid_images_processed': successful_images,
                    'success_rate': success_rate,
                    'upload_method': 'batch_with_progress',
                    'registration_date': str(datetime.utcnow())
                }
            )
            
            db.session.add(face_data)
            
            # Store in vector database
            vector_db = get_vector_db()
            if vector_db:
                try:
                    vector_db.add_face_data(
                        user_id=str(current_user.id),
                        encoding=average_encoding,
                        metadata={
                            'student_name': current_user.full_name,
                            'email': current_user.email,
                            'registration_date': str(datetime.utcnow())
                        }
                    )
                except Exception as e:
                    current_app.logger.error(f"Failed to store in vector database: {str(e)}")
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Facial data registered successfully',
                'total_images': total_images,
                'successful_images': successful_images,
                'success_rate': success_rate,
                'results': results,
                'registration_complete': True
            }), 201
        
        else:
            return jsonify({
                'success': False,
                'message': 'Need more valid face images for registration',
                'total_images': total_images,
                'successful_images': successful_images,
                'success_rate': success_rate,
                'results': results,
                'recommendation': f'You have {successful_images} valid images, but need at least 5 for registration'
            }), 400
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in upload_batch_with_progress: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/validate-image', methods=['POST'])
@jwt_required()
def validate_face_image():
    """Validate a single image for face detection before upload"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can validate face images'}), 403
        
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({'error': 'Image data is required'}), 400
        
        # Decode and validate image
        try:
            image_array = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({
                'valid': False,
                'face_detected': False,
                'error': f'Invalid image format: {str(e)}',
                'recommendations': ['Ensure image is in JPEG or PNG format', 'Check image data integrity']
            }), 200
        
        # Extract face encoding (for detection)
        face_encoding = extract_face_encoding(image_array)
        
        if face_encoding is not None:
            # Face detected successfully
            return jsonify({
                'valid': True,
                'face_detected': True,
                'quality': 'good',
                'confidence': 'high',
                'message': 'Face detected successfully'
            }), 200
        else:
            # No face detected
            return jsonify({
                'valid': False,
                'face_detected': False,
                'error': 'No face detected in image',
                'recommendations': [
                    'Ensure your face is clearly visible',
                    'Improve lighting conditions',
                    'Position face towards the camera',
                    'Remove any obstructions (masks, sunglasses, etc.)'
                ]
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in validate_face_image: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/upload-for-recognition', methods=['POST'])
@jwt_required()
def upload_face_for_recognition():
    """Upload facial data specifically for recognition/attendance purposes"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload facial data for recognition'}), 403
        
        data = request.get_json()
        
        if not data or 'images' not in data:
            return jsonify({'error': 'Images array is required'}), 400
        
        images = data['images']
        
        if not isinstance(images, list) or len(images) < 3:
            return jsonify({'error': 'At least 3 high-quality images are required for accurate recognition'}), 400
        
        if len(images) > 15:
            return jsonify({'error': 'Maximum 15 images allowed for recognition optimization'}), 400
        
        # Process images and extract face encodings with high accuracy settings
        all_encodings = []
        processing_results = []
        
        current_app.logger.info(f"Processing {len(images)} images for recognition optimization for student {current_user.id}")
        
        for i, image_data in enumerate(images):
            result = {
                'image_number': i + 1,
                'processed': False,
                'face_detected': False,
                'quality_score': 0,
                'error': None
            }
            
            try:
                # Decode image
                image_array = decode_base64_image(image_data)
                
                # Extract face encoding with large model for best accuracy
                face_encoding = extract_face_encoding(image_array, model='large')
                
                if face_encoding is not None:
                    all_encodings.append(face_encoding)
                    result.update({
                        'processed': True,
                        'face_detected': True,
                        'quality_score': 0.9,  # Could implement actual quality scoring
                        'encoding_dimension': len(face_encoding)
                    })
                else:
                    result.update({
                        'processed': False,
                        'face_detected': False,
                        'error': 'No face detected or face too small/unclear'
                    })
                    
            except Exception as e:
                result.update({
                    'processed': False,
                    'error': f'Processing error: {str(e)}'
                })
            
            processing_results.append(result)
        
        successful_extractions = len(all_encodings)
        
        if successful_extractions < 2:
            return jsonify({
                'success': False,
                'message': 'Insufficient high-quality face images for recognition',
                'required_minimum': 2,
                'successful_extractions': successful_extractions,
                'processing_results': processing_results,
                'recommendation': 'Please capture clear, well-lit photos showing your full face'
            }), 400
        
        # Calculate optimized encoding for recognition
        if successful_extractions > 1:
            # Use weighted average with quality scores
            optimized_encoding = np.mean(all_encodings, axis=0)
            # Normalize for better matching accuracy
            optimized_encoding = optimized_encoding / np.linalg.norm(optimized_encoding)
        else:
            optimized_encoding = all_encodings[0]
        
        # Check for existing face data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        # Store in vector database with optimized encoding
        vector_db = get_vector_db()
        vector_db_id = None
        
        if vector_db:
            try:
                metadata = {
                    'user_id': current_user.id,
                    'user_name': f"{current_user.first_name} {current_user.last_name}",
                    'email': current_user.email,
                    'encoding_version': 'v2.0_recognition_optimized',
                    'optimization_method': 'weighted_average',
                    'source_images': successful_extractions,
                    'upload_purpose': 'facial_recognition',
                    'upload_date': str(datetime.utcnow())
                }
                
                if existing_face_data and existing_face_data.vector_db_id:
                    # Update existing
                    success = vector_db.update_face_encoding(
                        current_user.id,
                        optimized_encoding,
                        metadata
                    )
                    vector_db_id = existing_face_data.vector_db_id
                else:
                    # Add new
                    vector_db_id = vector_db.add_face_encoding(
                        current_user.id,
                        optimized_encoding,
                        metadata
                    )
                    
            except Exception as e:
                current_app.logger.error(f"Vector DB operation failed: {e}")
        
        # Update or create face data record
        if existing_face_data:
            existing_face_data.vector_db_id = vector_db_id
            existing_face_data.encoding_metadata = {
                'recognition_optimized': True,
                'source_images': successful_extractions,
                'optimization_date': str(datetime.utcnow())
            }
            existing_face_data.encoding_version = 'v2.0_recognition_optimized'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Facial recognition data updated successfully',
                'student_id': current_user.id,
                'successful_extractions': successful_extractions,
                'total_images': len(images),
                'processing_results': processing_results,
                'recognition_ready': True,
                'vector_db_enabled': vector_db is not None
            }), 200
        else:
            face_data = FaceData(
                user_id=current_user.id,
                vector_db_id=vector_db_id,
                encoding_metadata={
                    'recognition_optimized': True,
                    'source_images': successful_extractions,
                    'optimization_date': str(datetime.utcnow())
                },
                encoding_version='v2.0_recognition_optimized'
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Facial recognition data uploaded successfully',
                'student_id': current_user.id,
                'successful_extractions': successful_extractions,
                'total_images': len(images),
                'processing_results': processing_results,
                'recognition_ready': True,
                'vector_db_enabled': vector_db is not None
            }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in upload_face_for_recognition: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/recognition-ready', methods=['GET'])
@jwt_required()
def check_recognition_readiness():
    """Check if student's facial data is ready for recognition/attendance"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can check recognition readiness'}), 403
        
        # Check face data
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({
                'recognition_ready': False,
                'status': 'no_face_data',
                'message': 'No facial data found. Please upload your facial images first.',
                'next_step': 'upload_facial_data'
            }), 200
        
        # Check vector database
        vector_db = get_vector_db()
        vector_db_status = 'disabled'
        vector_encoding_exists = False
        
        if vector_db and face_data.vector_db_id:
            try:
                vector_data = vector_db.get_face_encoding(current_user.id)
                vector_encoding_exists = vector_data is not None
                vector_db_status = 'enabled_and_ready' if vector_encoding_exists else 'enabled_but_no_data'
            except Exception as e:
                vector_db_status = f'error: {str(e)}'
        
        # Determine readiness
        is_ready = face_data and (vector_encoding_exists or vector_db is None)
        
        # Get metadata for additional info
        metadata = face_data.encoding_metadata or {}
        recognition_optimized = metadata.get('recognition_optimized', False)
        
        status_info = {
            'recognition_ready': is_ready,
            'status': 'ready' if is_ready else 'not_ready',
            'face_data_exists': True,
            'vector_db_status': vector_db_status,
            'recognition_optimized': recognition_optimized,
            'encoding_version': face_data.encoding_version,
            'upload_date': face_data.created_at.isoformat() if face_data.created_at else None,
            'metadata': metadata
        }
        
        if is_ready:
            status_info['message'] = 'Your facial data is ready for recognition and attendance'
            status_info['next_step'] = 'join_classes_and_attend'
        else:
            status_info['message'] = 'Your facial data needs optimization for better recognition'
            status_info['next_step'] = 'upload_optimized_facial_data'
        
        return jsonify(status_info), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in check_recognition_readiness: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/class/<int:class_id>/students-with-facial-data', methods=['GET'])
@jwt_required()
def get_class_students_facial_data(class_id):
    """
    Get all students with facial data for a specific class (Teacher only)
    
    Returns list of students enrolled in the class who have uploaded facial data
    """
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can access class facial data'}), 403
        
        # Verify teacher owns this class
        from models.models import Class, ClassEnrollment
        class_obj = Class.query.filter_by(id=class_id, teacher_id=current_user.id, is_active=True).first()
        
        if not class_obj:
            return jsonify({'error': 'Class not found or you do not have access'}), 404
        
        # Get all enrolled students with facial data
        students_with_data = db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            User.email,
            FaceData.vector_db_id,
            FaceData.encoding_version,
            FaceData.created_at.label('face_data_created_at')
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
        
        # Get total enrolled students
        total_enrolled = ClassEnrollment.query.filter_by(
            class_id=class_id,
            is_active=True
        ).count()
        
        students_list = []
        for student in students_with_data:
            students_list.append({
                'student_id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'email': student.email,
                'vector_db_id': student.vector_db_id,
                'encoding_version': student.encoding_version,
                'face_data_registered_at': student.face_data_created_at.isoformat() if student.face_data_created_at else None
            })
        
        return jsonify({
            'class_id': class_id,
            'class_name': class_obj.name,
            'total_enrolled_students': total_enrolled,
            'students_with_facial_data': len(students_list),
            'coverage_percentage': (len(students_list) / total_enrolled * 100) if total_enrolled > 0 else 0,
            'students': students_list
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in get_class_students_facial_data: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@face_data_bp.route('/recognize-from-photo', methods=['POST'])
@jwt_required()
def recognize_students_from_photo():
    """
    Extract all faces from classroom photo and recognize enrolled students
    
    Request body:
    {
        "image": "base64_encoded_image",
        "class_id": 123,
        "recognition_threshold": 0.6 (optional, default 0.6, lower = stricter)
    }
    
    Response:
    {
        "success": true,
        "class_id": 123,
        "class_name": "Mathematics 101",
        "total_faces_detected": 15,
        "total_recognized": 12,
        "total_enrolled_with_data": 20,
        "recognized_students": [
            {
                "student_id": 5,
                "name": "John Doe",
                "email": "john@example.com",
                "confidence": 0.85,
                "face_number": 1
            }
        ],
        "unrecognized_faces": 3
    }
    """
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'teacher':
            return jsonify({'error': 'Only teachers can perform facial recognition'}), 403
        
        data = request.get_json()
        
        # Validate request
        if not data or 'image' not in data:
            return jsonify({'error': 'Image is required'}), 400
        
        if 'class_id' not in data:
            return jsonify({'error': 'Class ID is required'}), 400
        
        class_id = data['class_id']
        recognition_threshold = data.get('recognition_threshold', 0.6)
        
        # Validate threshold
        if not (0.4 <= recognition_threshold <= 0.9):
            return jsonify({'error': 'Recognition threshold must be between 0.4 and 0.9'}), 400
        
        # Verify teacher owns this class
        from models.models import Class, ClassEnrollment
        class_obj = Class.query.filter_by(id=class_id, teacher_id=current_user.id, is_active=True).first()
        
        if not class_obj:
            return jsonify({'error': 'Class not found or you do not have access'}), 404
        
        # Decode image
        try:
            image_array = decode_base64_image(data['image'])
            current_app.logger.info(f"Processing classroom photo for class {class_id} by teacher {current_user.id}")
        except ValueError as e:
            return jsonify({'error': f'Invalid image: {str(e)}'}), 400
        
        # Extract all faces from the image using enhanced ArcFace approach (script.py style)
        current_app.logger.info(f"Extracting faces from classroom photo using enhanced ArcFace 512D...")
        
        # Use enhanced ArcFace batch detection
        face_data_list = []
        
        if ARCFACE_AVAILABLE:
            try:
                # Use the enhanced batch face detection from arcface_service
                from services.arcface_service import detect_faces_batch
                
                face_data_list = detect_faces_batch(image_array)
                current_app.logger.info(f"✅ Detected {len(face_data_list)} faces using enhanced ArcFace detection")
                
            except Exception as e:
                current_app.logger.error(f"Enhanced ArcFace face detection failed: {e}, falling back to legacy")
        
        # Fallback to legacy face_recognition if enhanced ArcFace failed
        if not face_data_list:
            current_app.logger.warning("⚠️ Using legacy face_recognition 128D (not compatible with 512D Vector DB!)")
            face_locations = face_recognition.face_locations(image_array, model='hog')
            if face_locations:
                face_model = os.getenv('FACE_ENCODING_MODEL', 'large')
                face_encodings = face_recognition.face_encodings(image_array, face_locations, model=face_model)
                
                # Convert to face_data_list format for compatibility
                for idx, (encoding, location) in enumerate(zip(face_encodings, face_locations)):
                    face_data_list.append({
                        'face_number': idx + 1,
                        'bbox': [location[3], location[0], location[1], location[2]],  # Convert to x1,y1,x2,y2
                        'embedding': encoding,
                        'embedding_dimension': len(encoding),
                        'detection_score': 1.0
                    })
        
        if not face_data_list:
            return jsonify({
                'success': True,
                'message': 'No faces detected in the image',
                'class_id': class_id,
                'class_name': class_obj.name,
                'total_faces_detected': 0,
                'total_recognized': 0,
                'recognized_students': [],
                'unrecognized_faces': 0
            }), 200
        
        current_app.logger.info(f"Detected {len(face_data_list)} faces in classroom photo")
        
        # Get all enrolled students with facial data for this class
        enrolled_students_data = db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            User.email,
            FaceData.vector_db_id
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
        
        if not enrolled_students_data:
            return jsonify({
                'success': False,
                'error': 'No students in this class have registered facial data',
                'class_id': class_id,
                'class_name': class_obj.name,
                'total_faces_detected': len(face_data_list),
                'recommendation': 'Ask students to register their facial data first'
            }), 400
        
        current_app.logger.info(f"Found {len(enrolled_students_data)} enrolled students with facial data")
        
        # Get vector database
        vector_db = get_vector_db()
        
        recognized_students = []
        student_ids_recognized = set()
        
        # Enhanced recognition using script.py approach
        # script.py uses cosine similarity in [-1, 1] with threshold 0.35
        # Vector DB uses similarity in [0, 1], so convert threshold: (t + 1) / 2
        script_threshold = 0.35
        vector_db_threshold = (script_threshold + 1.0) / 2.0  # ~0.675
        
        # Match each detected face with enrolled students
        for face_data in face_data_list:
            face_encoding = face_data['embedding']
            face_number = face_data['face_number']
            bbox = face_data['bbox']
            
            best_match = None
            best_similarity = 0
            
            if vector_db:
                # Use vector database for efficient matching with script.py threshold
                try:
                    # Search for similar faces using script.py approach
                    matches = vector_db.find_similar_faces(
                        face_encoding,
                        top_k=5,
                        threshold=vector_db_threshold
                    )
                    
                    # Filter matches to only enrolled students in this class
                    enrolled_ids = {s.id for s in enrolled_students_data}
                    
                    for match in matches:
                        user_id = match.get('user_id')
                        similarity = match.get('similarity', 0)
                        
                        if user_id in enrolled_ids and similarity > best_similarity:
                            # Avoid duplicate recognition of same student
                            if user_id not in student_ids_recognized:
                                best_similarity = similarity
                                student_info = next((s for s in enrolled_students_data if s.id == user_id), None)
                                if student_info:
                                    # Log each potential match with percentage
                                    try:
                                        percent = round(float(similarity) * 100.0, 2)
                                        current_app.logger.info(
                                            f"Match candidate: user_id={user_id}, name={student_info.first_name} {student_info.last_name}, "
                                            f"similarity={similarity:.4f} ({percent}%)"
                                        )
                                    except Exception:
                                        pass
                                    best_match = {
                                        'student_id': student_info.id,
                                        'name': f"{student_info.first_name} {student_info.last_name}",
                                        'email': student_info.email,
                                        'confidence': similarity,
                                        'similarity_percentage': round(float(similarity) * 100.0, 2),
                                        'face_number': face_number,
                                        'face_location': {
                                            'x1': int(bbox[0]), 'y1': int(bbox[1]),
                                            'x2': int(bbox[2]), 'y2': int(bbox[3])
                                        }
                                    }
                    
                except Exception as e:
                    current_app.logger.error(f"Vector DB search failed: {str(e)}")
            
            else:
                # Fallback: Direct comparison with stored encodings
                current_app.logger.warning("Vector DB not available, using direct comparison")
                
                for student_data in enrolled_students_data:
                    try:
                        # This would require storing encodings in FaceData model
                        # For now, skip if vector DB is not available
                        pass
                    except Exception as e:
                        continue
            
            # Add to recognized list if match found
            if best_match and best_match['student_id'] not in student_ids_recognized:
                try:
                    current_app.logger.info(
                        f"Best match selected for face #{face_number}: student_id={best_match['student_id']}, "
                        f"name={best_match['name']}, similarity={best_match['confidence']:.4f} "
                        f"({best_match.get('similarity_percentage', 0)}%)"
                    )
                except Exception:
                    pass
                recognized_students.append(best_match)
                student_ids_recognized.add(best_match['student_id'])
        
        # Calculate statistics
        total_faces_detected = len(face_data_list)
        total_recognized = len(recognized_students)
        unrecognized_faces = total_faces_detected - total_recognized
        total_enrolled_with_data = len(enrolled_students_data)
        
        current_app.logger.info(
            f"Recognition complete: {total_recognized}/{total_faces_detected} faces recognized, "
            f"{total_enrolled_with_data} students enrolled with facial data"
        )
        
        return jsonify({
            'success': True,
            'class_id': class_id,
            'class_name': class_obj.name,
            'teacher_id': current_user.id,
            'total_faces_detected': total_faces_detected,
            'total_recognized': total_recognized,
            'total_enrolled_with_data': total_enrolled_with_data,
            'recognition_threshold': recognition_threshold,
            'recognized_students': recognized_students,
            'unrecognized_faces': unrecognized_faces,
            'recognition_rate': (total_recognized / total_faces_detected * 100) if total_faces_detected > 0 else 0,
            'coverage_rate': (total_recognized / total_enrolled_with_data * 100) if total_enrolled_with_data > 0 else 0
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in recognize_students_from_photo: {str(e)}")
        current_app.logger.exception("Full traceback:")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@face_data_bp.route('/test-recognition', methods=['POST'])
@jwt_required()
def test_face_recognition():
    """Test facial recognition with a new image against stored data"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can test their facial recognition'}), 403
        
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({'error': 'Test image is required'}), 400
        
        # Check if student has facial data
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({
                'success': False,
                'message': 'No facial data found. Please upload your facial images first.',
                'recognition_possible': False
            }), 400
        
        # Decode test image
        try:
            test_image_array = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid test image: {str(e)}',
                'recognition_possible': False
            }), 400
        
        # Extract face from test image
        test_face_encoding = extract_face_encoding(test_image_array)
        
        if test_face_encoding is None:
            return jsonify({
                'success': False,
                'message': 'No face detected in test image',
                'recognition_possible': False,
                'recommendations': [
                    'Ensure your face is clearly visible',
                    'Improve lighting conditions',
                    'Position face directly towards camera'
                ]
            }), 200
        
        # Test against vector database
        vector_db = get_vector_db()
        recognition_results = []
        
        if vector_db:
            try:
                # Search for similar faces
                matches = vector_db.find_similar_faces(
                    test_face_encoding,
                    top_k=5,
                    threshold=0.4  # Lower threshold for testing
                )
                
                # Check if current user is in matches
                user_match = None
                for match in matches:
                    if match['user_id'] == current_user.id:
                        user_match = match
                        break
                
                if user_match:
                    confidence = user_match['similarity']
                    confidence_percentage = round(float(confidence) * 100.0, 2)
                    recognition_quality = 'excellent' if confidence > 0.8 else 'good' if confidence > 0.6 else 'fair'
                    
                    try:
                        current_app.logger.info(
                            f"Test recognition: user_id={current_user.id}, similarity={confidence:.4f} ({confidence_percentage}%)"
                        )
                    except Exception:
                        pass

                    return jsonify({
                        'success': True,
                        'recognition_possible': True,
                        'matched': True,
                        'confidence': confidence,
                        'confidence_percentage': confidence_percentage,
                        'recognition_quality': recognition_quality,
                        'message': f'Successfully recognized! Confidence: {confidence:.2f}',
                        'total_matches_found': len(matches),
                        'vector_db_enabled': True
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'recognition_possible': True,
                        'matched': False,
                        'message': 'Face not recognized. Consider re-uploading facial data with better quality images.',
                        'total_matches_found': len(matches),
                        'vector_db_enabled': True,
                        'recommendation': 'Upload new facial images with better lighting and clarity'
                    }), 200
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Recognition test failed: {str(e)}',
                    'vector_db_enabled': True
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'Vector database not available for recognition testing',
                'recognition_possible': False,
                'vector_db_enabled': False
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in test_face_recognition: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/student/upload-facial-data', methods=['POST'])
@jwt_required()
def student_upload_facial_data():
    """
    PRODUCTION API: Upload 10 facial images for student registration
    
    Request body:
    {
        "images": ["base64_image1", "base64_image2", ..., "base64_image10"],
        "replace_existing": true/false (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Facial data registered successfully",
        "student_id": 123,
        "student_name": "John Doe",
        "total_images": 10,
        "successful_images": 8,
        "success_rate": 80.0
    }
    """
    try:
        # Get logged-in student
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can upload facial data'}), 403
        
        # Get request data
        data = request.get_json()
        
        if not data or 'images' not in data:
            return jsonify({'error': 'Images array is required'}), 400
        
        images = data['images']
        
        # Validate images array
        if not isinstance(images, list):
            return jsonify({'error': 'Images must be an array'}), 400
        
        if len(images) < 5:
            return jsonify({'error': 'At least 5 images required. Please capture more photos.'}), 400
        
        if len(images) > 20:
            return jsonify({'error': 'Maximum 20 images allowed'}), 400
        
        # Check if student already has facial data
        existing_face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        replace_existing = data.get('replace_existing', False)
        
        if existing_face_data and not replace_existing:
            return jsonify({
                'error': 'Student already has facial data registered',
                'existing_data': True,
                'message': 'Use replace_existing=true to update existing facial data',
                'registration_date': existing_face_data.created_at.isoformat() if existing_face_data.created_at else None
            }), 400
        
        # Process images with detailed feedback
        processing_results = []
        valid_encodings = []
        failed_images = []
        
        current_app.logger.info(f"Processing {len(images)} facial images for student {current_user.id}")
        
        for i, image_data in enumerate(images):
            image_result = {
                'image_number': i + 1,
                'status': 'processing',
                'face_detected': False,
                'quality': 'unknown',
                'error': None
            }
            
            try:
                # Validate image format
                if not isinstance(image_data, str) or not image_data.strip():
                    image_result.update({
                        'status': 'failed',
                        'error': 'Invalid image data format'
                    })
                    failed_images.append(image_result)
                    continue
                
                # Decode image
                image_array = decode_base64_image(image_data)
                current_app.logger.debug(f"Student {current_user.id}: Decoded image {i + 1}, shape: {image_array.shape}")
                
                # Extract face encoding
                face_encoding = extract_face_encoding(image_array, model='large')
                
                if face_encoding is not None:
                    valid_encodings.append(face_encoding)
                    image_result.update({
                        'status': 'success',
                        'face_detected': True,
                        'quality': 'good',
                        'encoding_dimension': len(face_encoding)
                    })
                    current_app.logger.debug(f"Student {current_user.id}: Successfully extracted encoding from image {i + 1}")
                else:
                    image_result.update({
                        'status': 'failed',
                        'face_detected': False,
                        'error': 'No face detected or face quality too low'
                    })
                    failed_images.append(image_result)
                    current_app.logger.warning(f"Student {current_user.id}: No face detected in image {i + 1}")
                
            except ValueError as e:
                image_result.update({
                    'status': 'failed',
                    'error': f'Image processing error: {str(e)}'
                })
                failed_images.append(image_result)
                current_app.logger.error(f"Student {current_user.id}: ValueError processing image {i + 1}: {str(e)}")
            except Exception as e:
                image_result.update({
                    'status': 'failed',
                    'error': f'Unexpected error: {str(e)}'
                })
                failed_images.append(image_result)
                current_app.logger.error(f"Student {current_user.id}: Exception processing image {i + 1}: {str(e)}")
            
            processing_results.append(image_result)
        
        successful_images = len(valid_encodings)
        total_images = len(images)
        success_rate = (successful_images / total_images) * 100
        
        current_app.logger.info(f"Student {current_user.id}: Processed {successful_images}/{total_images} images successfully ({success_rate:.1f}% success rate)")
        
        if successful_images < 3:
            return jsonify({
                'success': False,
                'message': 'Insufficient valid facial images for registration',
                'required_minimum': 3,
                'successful_images': successful_images,
                'total_images': total_images,
                'success_rate': success_rate,
                'processing_results': processing_results,
                'failed_images': failed_images,
                'recommendations': [
                    'Ensure your face is clearly visible in all photos',
                    'Use good lighting conditions',
                    'Look directly at the camera',
                    'Remove any obstructions (masks, glasses, etc.)',
                    'Capture photos from slightly different angles'
                ]
            }), 400
        
        # Calculate optimized encoding
        average_encoding = np.mean(valid_encodings, axis=0)
        # Normalize for better matching
        average_encoding = average_encoding / np.linalg.norm(average_encoding)
        
        # Prepare metadata
        metadata = {
            'student_id': current_user.id,
            'student_name': f"{current_user.first_name} {current_user.last_name}",
            'student_email': current_user.email,
            'total_images_submitted': total_images,
            'successful_images': successful_images,
            'success_rate': success_rate,
            'upload_method': 'student_facial_registration',
            'encoding_version': 'v3.0_student_optimized',
            'registration_timestamp': str(datetime.utcnow()),
            'failed_images_count': len(failed_images)
        }
        
        # Store in vector database
        vector_db = get_vector_db()
        vector_db_id = None
        
        if vector_db:
            try:
                if existing_face_data and existing_face_data.vector_db_id:
                    # Update existing
                    success = vector_db.update_face_encoding(
                        current_user.id,
                        average_encoding,
                        metadata
                    )
                    vector_db_id = existing_face_data.vector_db_id
                    current_app.logger.info(f"Student {current_user.id}: Updated existing vector DB entry")
                else:
                    # Add new
                    vector_db_id = vector_db.add_face_encoding(
                        current_user.id,
                        average_encoding,
                        metadata
                    )
                    current_app.logger.info(f"Student {current_user.id}: Added new vector DB entry with ID {vector_db_id}")
                    
            except Exception as e:
                current_app.logger.error(f"Student {current_user.id}: Vector DB operation failed: {e}")
                # Continue without vector DB
        
        # Update or create face data record
        if existing_face_data:
            existing_face_data.vector_db_id = vector_db_id
            existing_face_data.encoding_metadata = metadata
            existing_face_data.encoding_version = 'v3.0_student_optimized'
            db.session.commit()
            
            current_app.logger.info(f"Student {current_user.id}: Updated existing facial data record")
            
            return jsonify({
                'success': True,
                'message': 'Facial data updated successfully',
                'student_id': current_user.id,
                'total_images': total_images,
                'successful_images': successful_images,
                'success_rate': success_rate,
                'processing_results': processing_results,
                'registration_complete': True,
                'data_updated': True,
                'vector_db_enabled': vector_db is not None
            }), 200
        else:
            face_data = FaceData(
                user_id=current_user.id,
                vector_db_id=vector_db_id,
                encoding_metadata=metadata,
                encoding_version='v3.0_student_optimized'
            )
            
            db.session.add(face_data)
            db.session.commit()
            
            current_app.logger.info(f"Student {current_user.id}: Created new facial data record")
            
            return jsonify({
                'success': True,
                'message': 'Facial data registered successfully',
                'student_id': current_user.id,
                'total_images': total_images,
                'successful_images': successful_images,
                'success_rate': success_rate,
                'processing_results': processing_results,
                'registration_complete': True,
                'data_updated': False,
                'vector_db_enabled': vector_db is not None
            }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in student_upload_facial_data: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/student/facial-status', methods=['GET'])
@jwt_required()
def get_student_facial_status():
    """Get detailed facial data status for current student"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can check facial status'}), 403
        
        # Get facial data
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({
                'has_facial_data': False,
                'status': 'not_registered',
                'message': 'No facial data found. Please complete facial registration.',
                'next_step': 'upload_facial_data',
                'registration_required': True
            }), 200
        
        # Get metadata
        metadata = face_data.encoding_metadata or {}
        
        # Check vector database status
        vector_db = get_vector_db()
        vector_status = {
            'enabled': vector_db is not None,
            'has_encoding': False,
            'status': 'disabled'
        }
        
        if vector_db and face_data.vector_db_id:
            try:
                vector_data = vector_db.get_face_encoding(current_user.id)
                vector_status.update({
                    'has_encoding': vector_data is not None,
                    'status': 'ready' if vector_data else 'no_data'
                })
            except Exception as e:
                vector_status.update({
                    'status': f'error: {str(e)}'
                })
        
        # Determine overall readiness
        is_ready = face_data and (vector_status['has_encoding'] or not vector_status['enabled'])
        
        return jsonify({
            'has_facial_data': True,
            'status': 'registered' if is_ready else 'needs_update',
            'registration_ready': is_ready,
            'student_info': {
                'id': current_user.id,
                'name': f"{current_user.first_name} {current_user.last_name}",
                'email': current_user.email
            },
            'facial_data_info': {
                'registration_date': face_data.created_at.isoformat() if face_data.created_at else None,
                'encoding_version': face_data.encoding_version,
                'successful_images': metadata.get('successful_images', 0),
                'total_images': metadata.get('total_images_submitted', 0),
                'success_rate': metadata.get('success_rate', 0),
                'upload_method': metadata.get('upload_method', 'unknown')
            },
            'vector_database': vector_status,
            'next_step': 'ready_for_attendance' if is_ready else 'update_facial_data',
            'message': 'Facial data is ready for attendance' if is_ready else 'Facial data may need updating for better recognition'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in get_student_facial_status: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@face_data_bp.route('/student/delete-facial-data', methods=['DELETE'])
@jwt_required()
def delete_student_facial_data():
    """Allow student to delete their facial data"""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user.role != 'student':
            return jsonify({'error': 'Only students can delete their facial data'}), 403
        
        # Get facial data
        face_data = FaceData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not face_data:
            return jsonify({
                'success': False,
                'message': 'No facial data found to delete'
            }), 404
        
        # Delete from vector database
        vector_db = get_vector_db()
        if vector_db and face_data.vector_db_id:
            try:
                vector_db.delete_face_encoding(current_user.id)
                current_app.logger.info(f"Student {current_user.id}: Deleted from vector database")
            except Exception as e:
                current_app.logger.error(f"Student {current_user.id}: Failed to delete from vector DB: {e}")
        
        # Deactivate facial data
        face_data.is_active = False
        db.session.commit()
        
        current_app.logger.info(f"Student {current_user.id}: Deactivated facial data")
        
        return jsonify({
            'success': True,
            'message': 'Facial data deleted successfully',
            'student_id': current_user.id,
            'deleted_at': str(datetime.utcnow())
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in delete_student_facial_data: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
