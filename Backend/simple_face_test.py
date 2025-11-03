#!/usr/bin/env python3
"""
Simple Face Detection Test
Just checks if faces are detected in the last classroom image
"""

import os
import sys
import numpy as np
from PIL import Image
import cv2

def test_simple_face_detection():
    """Simple test to see if any faces are detected"""
    
    # Check if image exists
    image_path = os.path.join('uploads', 'last_classroom_photo.jpg')
    
    if not os.path.exists(image_path):
        print("❌ No classroom photo found. Take attendance first to save an image.")
        return
    
    print("📸 Loading classroom image...")
    
    try:
        # Load image
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image_array = np.array(image)
        print(f"✅ Image loaded: {image_array.shape}")
        
        # Convert RGB to BGR for OpenCV/ArcFace
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        print(f"✅ Image converted to BGR: {image_bgr.shape}")
        
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return
    
    # --- Direct matching test ---
    print("\n🔍 Testing direct embedding match against vector database...")

    # Load reference embedding from vector database
    try:
        # Import vector database service
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from services.vector_db import get_vector_db_service
        
        # Get vector database instance
        vector_db = get_vector_db_service()
        print(f"✅ Connected to vector database: {vector_db.db_type}")
        
        # Get stats to see what's available
        stats = vector_db.get_stats()
        print(f"📊 Vector DB stats: {stats['total_encodings']} embeddings, dimension: {stats['encoding_dimension']}")
        
        if stats['total_encodings'] == 0:
            print("❌ No embeddings found in vector database")
            print("   Please register face data first using the mobile app")
            return
        
        # Get all encodings from ChromaDB to find the first available one
        if vector_db.db_type == "chroma":
            collection = vector_db.db.collection
            all_data = collection.get(include=["embeddings", "metadatas"])
            
            # Safe check for embeddings (avoid array boolean evaluation)
            embeddings = all_data['embeddings']
            if embeddings is None or (hasattr(embeddings, '__len__') and len(embeddings) == 0):
                print("❌ No embeddings retrieved from ChromaDB")
                return
            
            # Use the first embedding as reference
            ref_vec = np.array(all_data['embeddings'][0], dtype=np.float32)
            user_info = all_data['metadatas'][0] if all_data['metadatas'] else {}
            user_id = user_info.get('user_id', 'unknown')
            
            # Normalize the reference vector
            ref_norm = np.linalg.norm(ref_vec)
            if ref_norm > 0:
                ref_vec = ref_vec / ref_norm
            
            print(f"✅ Loaded reference embedding for user_id={user_id} (dim={ref_vec.shape[0]})")
        
        else:
            print("❌ Only ChromaDB is supported for direct embedding access")
            return
            
    except Exception as e:
        print(f"❌ Failed to load reference embedding from vector DB: {e}")
        import traceback
        traceback.print_exc()
        return

    # Try ArcFace first (preferred for 512D)
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'], allowed_modules=['detection','recognition'])
        app.prepare(ctx_id=0, det_size=(640,640))
        faces = app.get(image_bgr)
        print(f"🔎 ArcFace detected {len(faces)} faces")

        if len(faces) == 0:
            print("❌ No faces detected by ArcFace")
            return

        # For each detected face, get embedding and compare
        for i, face in enumerate(faces, start=1):
            # Safely get embedding without using boolean OR on numpy arrays
            emb = getattr(face, 'normed_embedding', None)
            if emb is None:
                emb = getattr(face, 'embedding', None)

            if emb is None:
                print(f"Face {i}: no embedding available, skipping")
                continue

            try:
                emb_arr = np.asarray(emb, dtype=np.float32)
                # Normalize
                e_norm = np.linalg.norm(emb_arr)
                if e_norm > 0:
                    emb_arr = emb_arr / e_norm

                # Ensure same dimension
                if emb_arr.shape[0] != ref_vec.shape[0]:
                    print(f"⚠️  Embedding dimension mismatch for face {i} (ref={ref_vec.shape[0]}, detected={emb_arr.shape[0]}). Skipping similarity check.")
                    continue

                # Compute cosine similarity
                sim = float(np.dot(ref_vec, emb_arr))
                print(f"Face {i}: similarity = {sim:.4f}")
                if sim >= 0.65:
                    print(f"✅ Face {i} MATCHES reference (threshold 0.65)")
                else:
                    print(f"❌ Face {i} does NOT match reference")

            except Exception as inner_e:
                print(f"⚠️  Failed to process embedding for face {i}: {inner_e}")
                continue

        return

    except Exception as e:
        print(f"⚠️  ArcFace not usable ({type(e).__name__}): {e}")

    # Fallback to face_recognition (128D) if ArcFace not available
    try:
        import face_recognition
        # Convert to RGB (image_array is RGB already)
        rgb = image_array
        encodings = face_recognition.face_encodings(rgb)
        print(f"🔎 face_recognition detected {len(encodings)} faces")
        if len(encodings) == 0:
            print("❌ No faces detected by face_recognition")
            return

        # Use first encoding
        for i, enc in enumerate(encodings, start=1):
            enc_arr = np.asarray(enc, dtype=np.float32)
            # If reference is 512D and enc is 128D, they are incompatible
            if enc_arr.shape[0] != ref_vec.shape[0]:
                print(f"⚠️  Embedding dimension mismatch (ref={ref_vec.shape[0]}, detected={enc_arr.shape[0]}). Skipping similarity check.")
                continue
            enc_norm = np.linalg.norm(enc_arr)
            if enc_norm > 0:
                enc_arr = enc_arr / enc_norm
            sim = float(np.dot(ref_vec, enc_arr))
            print(f"Face {i}: similarity = {sim:.4f}")
            if sim >= 0.65:
                print(f"✅ Face {i} MATCHES reference (threshold 0.65)")
            else:
                print(f"❌ Face {i} does NOT match reference")

    except Exception as e:
        print(f"❌ No suitable face recognition backend available: {e}")

if __name__ == "__main__":
    print("🔍 SIMPLE FACE DETECTION TEST")
    print("=" * 40)
    test_simple_face_detection()