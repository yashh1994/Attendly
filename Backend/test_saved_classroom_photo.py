#!/usr/bin/env python3
"""
Test script to use the last saved classroom photo for face detection testing
This script loads the saved classroom photo and tests the face detection directly
"""

import os
import sys
import numpy as np
import base64
import json
from PIL import Image
import cv2

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_saved_classroom_photo():
    """Load the last saved classroom photo"""
    test_image_path = os.path.join('uploads', 'last_classroom_photo.jpg')
    
    if not os.path.exists(test_image_path):
        print(f"❌ No saved classroom photo found at {test_image_path}")
        print("   Please take attendance with a classroom photo first to save an image")
        return None
    
    try:
        # Load image using PIL
        image = Image.open(test_image_path)
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        print(f"✅ Loaded saved classroom photo: {image_array.shape}")
        return image_array
        
    except Exception as e:
        print(f"❌ Error loading saved image: {e}")
        return None

def image_to_base64(image_array):
    """Convert numpy image array to base64 string"""
    try:
        # Convert to PIL Image
        image = Image.fromarray(image_array)
        
        # Save to bytes buffer
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        
        # Encode to base64
        image_bytes = buffer.getvalue()
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        
        return base64_string
        
    except Exception as e:
        print(f"❌ Error converting image to base64: {e}")
        return None

def test_arcface_detection_directly(image_array):
    """Test ArcFace face detection directly without API"""
    print("\n" + "="*50)
    print("DIRECT ARCFACE FACE DETECTION TEST")
    print("="*50)
    
    try:
        # Import ArcFace service
        from services.arcface_service import detect_faces_batch, initialize_arcface
        
        # Initialize ArcFace
        print("Initializing ArcFace model...")
        model = initialize_arcface()
        
        if model is None:
            print("❌ ArcFace model failed to initialize")
            return False
        
        print("✅ ArcFace model initialized successfully")
        
        # Test face detection
        print("Detecting faces in saved classroom photo...")
        face_data_list = detect_faces_batch(image_array)
        
        print(f"✅ Detected {len(face_data_list)} faces")
        
        # Print details for each detected face
        for i, face_data in enumerate(face_data_list, 1):
            bbox = face_data.get('bbox', [0, 0, 0, 0])
            embedding_dim = face_data.get('embedding_dimension', 0)
            detection_score = face_data.get('detection_score', 0)
            
            print(f"  Face {i}:")
            print(f"    Bounding box: {bbox}")
            print(f"    Embedding dimension: {embedding_dim}")
            print(f"    Detection score: {detection_score:.3f}")
        
        return len(face_data_list) > 0
        
    except Exception as e:
        print(f"❌ Direct ArcFace test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_with_saved_photo():
    """Test the API endpoint with saved photo"""
    print("\n" + "="*50)
    print("API ENDPOINT TEST WITH SAVED PHOTO")
    print("="*50)
    
    image_array = load_saved_classroom_photo()
    if image_array is None:
        return False
    
    # Convert to base64
    base64_image = image_to_base64(image_array)
    if base64_image is None:
        return False
    
    try:
        import requests
        
        # Test data (you may need to adjust class_id and use real authentication)
        test_data = {
            "image": base64_image,
            "class_id": 1,
            "recognition_threshold": 0.675
        }
        
        # You would need a valid JWT token here
        headers = {
            "Content-Type": "application/json"
            # "Authorization": "Bearer your_jwt_token_here"
        }
        
        print("Making API request to recognize-from-photo endpoint...")
        print("⚠️  Note: This test requires valid authentication and running server")
        
        # This would require authentication, so just show the setup
        print("Test data prepared:")
        print(f"  Image size: {len(base64_image)} characters")
        print(f"  Class ID: {test_data['class_id']}")
        print(f"  Threshold: {test_data['recognition_threshold']}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test preparation failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 TESTING SAVED CLASSROOM PHOTO")
    print("="*50)
    
    # Load the saved image
    image_array = load_saved_classroom_photo()
    if image_array is None:
        print("\n💡 To use this test:")
        print("   1. Start the Flask server")
        print("   2. Use the mobile app to take attendance with a classroom photo")
        print("   3. Run this script to test with the saved photo")
        return
    
    # Test direct ArcFace detection
    detection_success = test_arcface_detection_directly(image_array)
    
    # Test API preparation
    api_prep_success = test_api_with_saved_photo()
    
    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY")
    print("="*50)
    print(f"✅ Image loaded: {image_array is not None}")
    print(f"{'✅' if detection_success else '❌'} Direct ArcFace detection: {detection_success}")
    print(f"{'✅' if api_prep_success else '❌'} API test preparation: {api_prep_success}")
    
    if detection_success:
        print("\n🎉 Face detection is working with the saved classroom photo!")
        print("   You can now debug why the API might be returning 0 faces.")
    else:
        print("\n⚠️  Face detection failed. Check:")
        print("   - ArcFace model installation")
        print("   - Image quality and format")
        print("   - Face visibility in the photo")

if __name__ == "__main__":
    main()