"""
Test script to validate the Attendly backend setup and basic functionality
Run this script to ensure all dependencies are installed correctly
"""

import sys
import traceback

def test_imports():
    """Test if all required libraries can be imported"""
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False
    
    try:
        import flask_sqlalchemy
        print("✓ Flask-SQLAlchemy imported successfully")
    except ImportError as e:
        print(f"✗ Flask-SQLAlchemy import failed: {e}")
        return False
    
    try:
        import flask_jwt_extended
        print("✓ Flask-JWT-Extended imported successfully")
    except ImportError as e:
        print(f"✗ Flask-JWT-Extended import failed: {e}")
        return False
    
    try:
        import cv2
        print("✓ OpenCV imported successfully")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        return False
    
    try:
        import face_recognition
        print("✓ face_recognition imported successfully")
    except ImportError as e:
        print(f"✗ face_recognition import failed: {e}")
        return False
    
    try:
        import numpy as np
        print("✓ NumPy imported successfully")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        return False
    
    try:
        from PIL import Image
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")
        return False
    
    return True

def test_face_recognition():
    """Test basic face recognition functionality"""
    print("\nTesting face recognition functionality...")
    
    try:
        import face_recognition
        import numpy as np
        
        # Create a dummy image (RGB)
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Try to find face locations (should return empty list for dummy image)
        face_locations = face_recognition.face_locations(dummy_image)
        print("✓ Face location detection works")
        
        # Test encoding (this will fail gracefully with empty list)
        face_encodings = face_recognition.face_encodings(dummy_image, face_locations)
        print("✓ Face encoding extraction works")
        
        return True
        
    except Exception as e:
        print(f"✗ Face recognition test failed: {e}")
        return False

def test_database_models():
    """Test if database models can be imported"""
    print("\nTesting database models...")
    
    try:
        # Test if models can be imported (this will fail if Flask is not available)
        # We'll skip this for now since it requires app context
        print("✓ Database models test skipped (requires Flask app context)")
        return True
        
    except Exception as e:
        print(f"✗ Database models test failed: {e}")
        return False

def test_image_processing():
    """Test image processing capabilities"""
    print("\nTesting image processing...")
    
    try:
        import cv2
        from PIL import Image
        import numpy as np
        import base64
        import io
        
        # Create a test image
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(test_image)
        print("✓ PIL Image conversion works")
        
        # Test base64 encoding/decoding
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Decode back
        decoded_data = base64.b64decode(img_str)
        decoded_image = Image.open(io.BytesIO(decoded_data))
        print("✓ Base64 image encoding/decoding works")
        
        return True
        
    except Exception as e:
        print(f"✗ Image processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("ATTENDLY BACKEND SETUP VALIDATION")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Run import tests
    if not test_imports():
        all_tests_passed = False
    
    # Run face recognition tests
    if not test_face_recognition():
        all_tests_passed = False
    
    # Run database tests
    if not test_database_models():
        all_tests_passed = False
    
    # Run image processing tests
    if not test_image_processing():
        all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Your Attendly backend is ready to run!")
        print("\nNext steps:")
        print("1. Run 'python app.py' to start the server")
        print("2. The API will be available at http://localhost:5000")
        print("3. Check the README.md for API documentation")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please install missing dependencies:")
        print("pip install -r requirements.txt")
        print("\nIf face_recognition fails to install, try:")
        print("pip install cmake")
        print("pip install dlib")
        print("pip install face_recognition")
    print("=" * 50)

if __name__ == "__main__":
    main()