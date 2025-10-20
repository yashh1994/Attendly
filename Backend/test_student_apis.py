#!/usr/bin/env python3
"""
Quick test script to verify the new student facial APIs work correctly
"""

import requests
import json
import base64
from PIL import Image
import io

BASE_URL = "http://localhost:5000"

def create_test_image():
    """Create a simple test image"""
    image = Image.new('RGB', (100, 100), color='blue')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    image_bytes = buffer.getvalue()
    return base64.b64encode(image_bytes).decode('utf-8')

def test_student_apis():
    """Test the new student facial APIs"""
    print("🧪 Testing Student Facial Data APIs\n")
    
    # First, we need to register and login as a student
    print("1. Testing student registration...")
    
    # Register student
    student_data = {
        "first_name": "Test",
        "last_name": "Student", 
        "email": "student@test.com",
        "password": "testpass123",
        "role": "student"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=student_data)
        if response.status_code in [201, 400]:  # 400 if already exists
            print("✅ Student registration: OK")
        else:
            print(f"❌ Student registration failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Student registration error: {e}")
        return
    
    # Login student
    print("2. Testing student login...")
    login_data = {
        "email": "student@test.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()['token']
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Student login: OK")
        else:
            print(f"❌ Student login failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Student login error: {e}")
        return
    
    # Test facial status (should be empty initially)
    print("3. Testing initial facial status...")
    try:
        response = requests.get(f"{BASE_URL}/api/face-data/student/facial-status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Initial status: {status.get('status', 'unknown')}")
            print(f"   Has facial data: {status.get('has_facial_data', False)}")
        else:
            print(f"❌ Get facial status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Get facial status error: {e}")
    
    # Test facial data upload
    print("4. Testing facial data upload...")
    test_image = create_test_image()
    upload_data = {
        "images": [f"data:image/jpeg;base64,{test_image}" for _ in range(6)],
        "replace_existing": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/face-data/student/upload-facial-data", json=upload_data, headers=headers)
        if response.status_code in [200, 201, 400]:  # 400 expected for test images
            result = response.json()
            print(f"✅ Upload result: {result.get('message', 'Completed')}")
            if 'successful_images' in result:
                print(f"   Successful images: {result.get('successful_images', 0)}/{result.get('total_images', 0)}")
            if 'success_rate' in result:
                print(f"   Success rate: {result.get('success_rate', 0):.1f}%")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Upload error: {e}")
    
    # Test facial status after upload
    print("5. Testing facial status after upload...")
    try:
        response = requests.get(f"{BASE_URL}/api/face-data/student/facial-status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Updated status: {status.get('status', 'unknown')}")
            print(f"   Has facial data: {status.get('has_facial_data', False)}")
            print(f"   Registration ready: {status.get('registration_ready', False)}")
        else:
            print(f"❌ Get updated status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Get updated status error: {e}")
    
    print("\n🎉 Student Facial API testing completed!")
    print("\n📝 API Endpoints Available:")
    print("   POST /api/face-data/student/upload-facial-data")
    print("   GET  /api/face-data/student/facial-status") 
    print("   DELETE /api/face-data/student/delete-facial-data")

if __name__ == "__main__":
    test_student_apis()