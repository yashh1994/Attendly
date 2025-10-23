# Quick Fix Script for Face Detection Issues

import subprocess
import sys

print("=" * 80)
print("FACE DETECTION QUICK FIX")
print("=" * 80)

print("\n1. Installing ArcFace dependencies...")
try:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "insightface==0.7.3", 
        "onnxruntime==1.16.3", 
        "onnx==1.15.0"
    ])
    print("✅ ArcFace installed successfully")
except Exception as e:
    print(f"❌ Failed to install ArcFace: {e}")
    print("⚠️ Will use legacy face_recognition fallback")

print("\n2. Testing face_recognition library...")
try:
    import face_recognition
    import numpy as np
    
    # Create a test image with random data
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # This will fail (no face) but confirms library works
    locations = face_recognition.face_locations(test_image)
    print(f"✅ face_recognition library is working (found {len(locations)} faces in random noise)")
except Exception as e:
    print(f"❌ face_recognition test failed: {e}")

print("\n3. Checking OpenCV...")
try:
    import cv2
    print(f"✅ OpenCV version: {cv2.__version__}")
except Exception as e:
    print(f"❌ OpenCV not available: {e}")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("\n1. Restart your Flask server:")
print("   python run_server.py")
print("\n2. Test student face upload from mobile app")
print("\n3. If still failing, check FACE_DETECTION_DEBUG.md for detailed troubleshooting")
print("\n" + "=" * 80)
