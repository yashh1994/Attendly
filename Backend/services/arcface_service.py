"""
ArcFace Service - 512-dimensional face recognition embeddings
Provides high-accuracy face detection and embedding extraction using InsightFace ArcFace model
"""

import os
import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global model instance
_arcface_model = None
_detection_model = None

def initialize_arcface():
    """
    Initialize ArcFace model for face recognition
    Downloads model if not present, loads for inference
    """
    global _arcface_model, _detection_model
    
    if _arcface_model is not None:
        return _arcface_model
    
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        logger.info("Initializing ArcFace model...")
        
        # Initialize face analysis app with detection and recognition
        app = FaceAnalysis(
            name='buffalo_l',  # High accuracy model
            providers=['CPUExecutionProvider'],  # Use CPU (can change to CUDA if GPU available)
            allowed_modules=['detection', 'recognition']
        )
        
        # Prepare model (downloads if needed)
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        _arcface_model = app
        logger.info("✅ ArcFace model initialized successfully")
        logger.info(f"   Model: buffalo_l (512D embeddings)")
        logger.info(f"   Detection size: 640x640")
        
        return _arcface_model
        
    except Exception as e:
        logger.error(f"Failed to initialize ArcFace model: {str(e)}")
        logger.error("Falling back to legacy face_recognition library")
        return None


def get_arcface_model():
    """Get or initialize ArcFace model"""
    global _arcface_model
    if _arcface_model is None:
        _arcface_model = initialize_arcface()
    return _arcface_model


def extract_arcface_embedding(image_array: np.ndarray, return_largest: bool = True) -> Optional[np.ndarray]:
    """
    Extract 512-dimensional ArcFace embedding from image
    Enhanced with script.py approach for better efficiency
    
    Args:
        image_array: NumPy array of image (RGB format)
        return_largest: If True, returns embedding from largest face; else returns all
    
    Returns:
        512-dimensional embedding vector or None if no face detected
    """
    try:
        model = get_arcface_model()
        
        if model is None:
            logger.warning("ArcFace model not available, cannot extract embedding")
            return None
        
        # Convert RGB to BGR (InsightFace expects BGR)
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            image_bgr = image_array
        
        # Detect and extract faces - using script.py approach
        try:
            faces = model.get(image_bgr)
        except Exception as e:
            logger.warning(f"ArcFace detection failed: {e}")
            faces = []

        # Safe check for empty faces list/array - avoid boolean evaluation of numpy arrays
        if faces is None or (hasattr(faces, '__len__') and len(faces) == 0):
            logger.debug("No face detected in image")
            return None
        
        if len(faces) > 1:
            logger.debug(f"Multiple faces detected ({len(faces)}), using largest face")
        
        if return_largest:
            # Find largest face by bounding box area (safe access)
            def _bbox_area(f):
                try:
                    bbox = getattr(f, 'bbox', None)
                    if bbox is None:
                        return 0
                    arr = np.asarray(bbox)
                    if arr.size >= 4:
                        w = float(arr[2]) - float(arr[0])
                        h = float(arr[3]) - float(arr[1])
                        return max(0.0, w * h)
                except Exception:
                    return 0
                return 0

            largest_face = max(faces, key=_bbox_area)

            # Retrieve embedding safely
            embedding = getattr(largest_face, 'normed_embedding', None)
            if embedding is None:
                embedding = getattr(largest_face, 'embedding', None)

            if embedding is None:
                logger.debug("Largest face has no embedding")
                return None

            embedding = np.asarray(embedding, dtype=np.float32)
            # Normalize if not unit
            nrm = np.linalg.norm(embedding)
            if nrm > 0:
                embedding = embedding / nrm

            logger.debug(f"Extracted ArcFace embedding: shape={embedding.shape}, norm={np.linalg.norm(embedding):.4f}")
            return embedding
        else:
            # Return all face embeddings
            embeddings = [face.normed_embedding for face in faces]
            return embeddings
    
    except Exception as e:
        logger.error(f"Error extracting ArcFace embedding: {str(e)}")
        return None


def extract_multiple_arcface_embeddings(image_arrays: List[np.ndarray]) -> Tuple[List[np.ndarray], List[Dict]]:
    """
    Extract ArcFace embeddings from multiple images and calculate average
    
    Args:
        image_arrays: List of image arrays
    
    Returns:
        Tuple of (valid_embeddings, processing_results)
    """
    valid_embeddings = []
    processing_results = []
    
    for idx, image_array in enumerate(image_arrays):
        result = {
            'image_number': idx + 1,
            'success': False,
            'face_detected': False,
            'embedding_dimension': 0,
            'quality_score': 0.0
        }
        
        try:
            embedding = extract_arcface_embedding(image_array)
            
            if embedding is not None:
                # Ensure numpy array and normalization
                emb_arr = np.asarray(embedding, dtype=np.float32)
                nrm = np.linalg.norm(emb_arr)
                if nrm > 0:
                    emb_arr = emb_arr / nrm

                valid_embeddings.append(emb_arr)
                result.update({
                    'success': True,
                    'face_detected': True,
                    'embedding_dimension': int(emb_arr.shape[0]),
                    'quality_score': 0.95  # ArcFace provides high quality embeddings
                })
            else:
                result['error'] = 'No face detected'
                
        except Exception as e:
            result['error'] = str(e)
        
        processing_results.append(result)
    
    return valid_embeddings, processing_results


def calculate_average_embedding(embeddings: List[np.ndarray]) -> np.ndarray:
    """
    Calculate weighted average of multiple embeddings and normalize
    
    Args:
        embeddings: List of embedding vectors
    
    Returns:
        Averaged and normalized 512D embedding
    """
    if not embeddings:
        raise ValueError("No embeddings provided")
    
    if len(embeddings) == 1:
        return embeddings[0]
    
    # Calculate mean
    avg_embedding = np.mean(embeddings, axis=0)
    
    # Normalize to unit vector (ArcFace expects normalized embeddings)
    norm = np.linalg.norm(avg_embedding)
    if norm > 0:
        avg_embedding = avg_embedding / norm
    
    logger.debug(f"Averaged {len(embeddings)} embeddings, final norm: {np.linalg.norm(avg_embedding):.4f}")
    
    return avg_embedding


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Compute cosine similarity between two ArcFace embeddings
    Uses the efficient approach from script.py - direct cosine similarity
    
    Args:
        embedding1: First 512D embedding (already normalized by ArcFace)
        embedding2: Second 512D embedding (already normalized by ArcFace)
    
    Returns:
        Similarity score (cosine similarity, -1 to 1, higher is more similar)
    """
    try:
        # Direct cosine similarity - handle non-normalized inputs gracefully
        try:
            a = np.asarray(embedding1, dtype=np.float32)
            b = np.asarray(embedding2, dtype=np.float32)
            na = np.linalg.norm(a)
            nb = np.linalg.norm(b)
            if na == 0 or nb == 0:
                return 0.0
            similarity = float(np.dot(a, b) / (na * nb))
            return similarity
        except Exception as e:
            logger.warning(f"compute_similarity failed: {e}")
            return 0.0
        
    except Exception as e:
        logger.error(f"Error computing similarity: {str(e)}")
        return 0.0


def match_faces(query_embedding: np.ndarray, 
                database_embeddings: List[np.ndarray], 
                threshold: float = 0.35) -> List[Tuple[int, float]]:
    """
    Match a query embedding against database of embeddings
    Enhanced with script.py approach - optimized similarity threshold
    
    Args:
        query_embedding: Query face embedding (512D)
        database_embeddings: List of database embeddings
        threshold: Minimum similarity threshold (default 0.35 like script.py)
    
    Returns:
        List of (index, similarity) tuples for matches above threshold, sorted by similarity
    """
    matches = []
    
    for idx, db_embedding in enumerate(database_embeddings):
        similarity = compute_similarity(query_embedding, db_embedding)
        
        if similarity >= threshold:
            matches.append((idx, similarity))
    
    # Sort by similarity (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    logger.debug(f"Found {len(matches)} matches above threshold {threshold}")
    return matches


def recognize_face_in_image(image_array: np.ndarray, 
                           database_embeddings: List[np.ndarray],
                           student_names: List[str] = None,
                           threshold: float = 0.35) -> List[Dict]:
    """
    Recognize faces in an image against a database of known faces
    Inspired by script.py approach for efficient recognition
    
    Args:
        image_array: Image as numpy array (RGB)
        database_embeddings: List of known face embeddings
        student_names: Optional list of student names corresponding to embeddings
        threshold: Recognition threshold (default 0.35)
    
    Returns:
        List of recognized faces with similarity scores
    """
    try:
        model = get_arcface_model()
        
        if model is None:
            return []
        
        # Convert RGB to BGR
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Detect all faces in the image
        try:
            faces = model.get(image_bgr)
        except Exception as e:
            logger.warning(f"ArcFace batch get failed in recognition: {e}")
            faces = []
        
        recognized_faces = []
        
        for face_idx, face in enumerate(faces):
            # Safely get embedding and convert to numpy array
            query_embedding = getattr(face, 'normed_embedding', None) or getattr(face, 'embedding', None)
            if query_embedding is None:
                logger.warning(f"Face {face_idx + 1} has no embedding, skipping recognition for this face")
                continue

            try:
                query_embedding = np.asarray(query_embedding, dtype=np.float32)
                qnorm = np.linalg.norm(query_embedding)
                if qnorm > 0:
                    query_embedding = query_embedding / qnorm
                else:
                    logger.warning(f"Query embedding for face {face_idx + 1} has zero norm, skipping")
                    continue
            except Exception as e:
                logger.warning(f"Failed to process query embedding for face {face_idx + 1}: {e}")
                continue
            
            # Find matches
            matches = match_faces(query_embedding, database_embeddings, threshold)
            
            # Safe bbox extraction
            # Safe bbox extraction
            try:
                bbox_raw = getattr(face, 'bbox', None)
                if bbox_raw is None:
                    bbox = [0, 0, 100, 100]
                else:
                    # try several conversion strategies
                    if isinstance(bbox_raw, list):
                        bbox = bbox_raw
                    else:
                        try:
                            bbox = np.asarray(bbox_raw).tolist()
                        except Exception:
                            bbox = [float(bbox_raw[0]) if hasattr(bbox_raw, '__len__') and len(bbox_raw) > 0 else 0,
                                    float(bbox_raw[1]) if hasattr(bbox_raw, '__len__') and len(bbox_raw) > 1 else 0,
                                    float(bbox_raw[2]) if hasattr(bbox_raw, '__len__') and len(bbox_raw) > 2 else 100,
                                    float(bbox_raw[3]) if hasattr(bbox_raw, '__len__') and len(bbox_raw) > 3 else 100]
            except Exception:
                bbox = [0, 0, 100, 100]
            
            face_info = {
                'face_number': face_idx + 1,
                'bbox': bbox,
                'matches': []
            }
            
            for match_idx, similarity in matches:
                match_info = {
                    'database_index': match_idx,
                    'similarity': similarity,
                    'student_name': student_names[match_idx] if student_names and match_idx < len(student_names) else f"Student_{match_idx}"
                }
                face_info['matches'].append(match_info)
            
            recognized_faces.append(face_info)
        
        logger.info(f"Recognized {len(recognized_faces)} faces in image")
        return recognized_faces
        
    except Exception as e:
        logger.error(f"Error in face recognition: {str(e)}")
        return []


def detect_faces_batch(image_array: np.ndarray) -> List[Dict]:
    """
    Detect all faces in an image and return their embeddings with metadata
    
    Args:
        image_array: Image as numpy array (RGB)
    
    Returns:
        List of dictionaries with face info (bbox, embedding, landmarks, etc.)
    """
    try:
        model = get_arcface_model()
        
        if model is None:
            return []
        
        # Convert RGB to BGR
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Detect faces
        try:
            faces = model.get(image_bgr)
        except Exception as e:
            logger.warning(f"ArcFace batch get failed in detect_faces_batch: {e}")
            faces = []

        face_data = []
        # Handle faces array safely - avoid direct boolean evaluation of numpy arrays
        faces_list = faces if faces is not None else []
        if hasattr(faces_list, '__len__') and len(faces_list) == 0:
            faces_list = []
        
        for idx, face in enumerate(faces_list):
            # Retrieve embedding safely and convert to numpy array
            embedding = getattr(face, 'normed_embedding', None) or getattr(face, 'embedding', None)

            if embedding is None:
                logger.warning(f"Face {idx + 1} has no embedding, skipping")
                continue

            try:
                emb_arr = np.asarray(embedding, dtype=np.float32)
                # Normalize if not already unit norm
                norm = np.linalg.norm(emb_arr)
                if norm > 0:
                    emb_arr = emb_arr / norm
            except Exception as e:
                logger.warning(f"Failed to convert embedding for face {idx + 1}: {e}")
                continue

            # Safe bbox extraction (supports list, tuple, numpy array or None)
            try:
                bbox_raw = getattr(face, 'bbox', None)
                if bbox_raw is None:
                    bbox = [0, 0, 100, 100]
                else:
                    if isinstance(bbox_raw, list):
                        bbox = bbox_raw
                    else:
                        try:
                            bbox = np.asarray(bbox_raw).tolist()
                        except Exception:
                            # Fallback to try indexing
                            try:
                                bbox = [float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3])]
                            except Exception:
                                bbox = [0, 0, 100, 100]
            except Exception:
                bbox = [0, 0, 100, 100]

            # Safe landmarks extraction
            try:
                lm_raw = getattr(face, 'landmark_2d_106', None)
                landmarks = None
                if lm_raw is not None:
                    if isinstance(lm_raw, list):
                        landmarks = lm_raw
                    else:
                        try:
                            landmarks = np.asarray(lm_raw).tolist()
                        except Exception:
                            landmarks = None
            except Exception:
                landmarks = None

            try:
                det_score = float(getattr(face, 'det_score', 1.0))
            except Exception:
                det_score = 1.0

            try:
                age_val = int(getattr(face, 'age', 0)) if getattr(face, 'age', None) is not None else None
            except Exception:
                age_val = None

            try:
                gender_val = int(getattr(face, 'gender', 0)) if getattr(face, 'gender', None) is not None else None
            except Exception:
                gender_val = None

            face_info = {
                'face_number': idx + 1,
                'bbox': bbox,
                'embedding': emb_arr,
                'embedding_dimension': int(emb_arr.shape[0]),
                'detection_score': det_score,
                'landmarks': landmarks,
                'age': age_val,
                'gender': gender_val
            }
            face_data.append(face_info)

        logger.info(f"Detected {len(face_data)} faces in image")
        return face_data
        
    except Exception as e:
        logger.error(f"Error in batch face detection: {str(e)}")
        return []


def get_model_info() -> Dict:
    """Get information about the loaded ArcFace model"""
    model = get_arcface_model()
    
    if model is None:
        return {
            'status': 'not_loaded',
            'model_name': None,
            'embedding_dimension': 0
        }
    
    return {
        'status': 'loaded',
        'model_name': 'buffalo_l',
        'embedding_dimension': 512,
        'framework': 'InsightFace',
        'providers': ['CPUExecutionProvider']
    }


# Backward compatibility wrapper for legacy code
def extract_face_encoding_legacy(image_array: np.ndarray) -> Optional[np.ndarray]:
    """
    Legacy function name for backward compatibility
    Now uses ArcFace 512D instead of face_recognition 128D
    """
    return extract_arcface_embedding(image_array)
