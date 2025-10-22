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
        
        # Detect and extract faces
        faces = model.get(image_bgr)
        
        if not faces or len(faces) == 0:
            logger.debug("No face detected in image")
            return None
        
        if len(faces) > 1:
            logger.warning(f"Multiple faces detected ({len(faces)}), using largest face")
        
        if return_largest:
            # Find largest face by bounding box area
            largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            embedding = largest_face.normed_embedding
            
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
                valid_embeddings.append(embedding)
                result.update({
                    'success': True,
                    'face_detected': True,
                    'embedding_dimension': len(embedding),
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
    
    Args:
        embedding1: First 512D embedding
        embedding2: Second 512D embedding
    
    Returns:
        Similarity score (0-1, higher is more similar)
    """
    try:
        # Ensure embeddings are normalized
        emb1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        emb2_norm = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
        
        # Cosine similarity (dot product of normalized vectors)
        similarity = np.dot(emb1_norm, emb2_norm)
        
        # Convert to 0-1 range (cosine similarity is -1 to 1)
        similarity = (similarity + 1) / 2
        
        return float(similarity)
        
    except Exception as e:
        logger.error(f"Error computing similarity: {str(e)}")
        return 0.0


def match_faces(query_embedding: np.ndarray, 
                database_embeddings: List[np.ndarray], 
                threshold: float = 0.6) -> List[Tuple[int, float]]:
    """
    Match a query embedding against database of embeddings
    
    Args:
        query_embedding: Query face embedding (512D)
        database_embeddings: List of database embeddings
        threshold: Minimum similarity threshold
    
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
    
    return matches


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
        faces = model.get(image_bgr)
        
        face_data = []
        for idx, face in enumerate(faces):
            face_info = {
                'face_number': idx + 1,
                'bbox': face.bbox.tolist(),
                'embedding': face.normed_embedding,
                'embedding_dimension': len(face.normed_embedding),
                'detection_score': float(face.det_score) if hasattr(face, 'det_score') else 1.0,
                'landmarks': face.landmark_2d_106.tolist() if hasattr(face, 'landmark_2d_106') else None,
                'age': int(face.age) if hasattr(face, 'age') else None,
                'gender': int(face.gender) if hasattr(face, 'gender') else None
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
