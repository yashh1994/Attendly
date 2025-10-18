"""
Test script for AI-Powered Attendance System Backend
Run this script to verify all components are working correctly
"""

import requests
import json
import base64
import os
from PIL import Image
import io

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test if the server is running and healthy"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health Check Passed")
            print(f"   Status: {data['status']}")
            print(f"   Database: {data['database']}")
            print(f"   Vector DB: {data['vector_db']}")
            if 'vector_db_type' in data:
                print(f"   Vector DB Type: {data['vector_db_type']}")
            return True
        else:
            print("❌ Health Check Failed")
            print(f"   Status Code: {response.status_code}")
            return False
    except Exception as e:
        print("❌ Health Check Failed")
        print(f"   Error: {str(e)}")
        return False

def test_teacher_signup():
    """Test teacher registration"""
    try:
        data = {
            "first_name": "Test",
            "last_name": "Teacher",
            "email": "teacher@test.com",
            "password": "testpassword123",
            "role": "teacher"
        }
        
        response = requests.post(f"{BASE_URL}/auth/signup", json=data)
        if response.status_code == 201:
            print("✅ Teacher Signup Passed")
            return True
        elif response.status_code == 400 and "already exists" in response.json().get('error', ''):
            print("✅ Teacher Already Exists (OK)")
            return True
        else:
            print("❌ Teacher Signup Failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return False
    except Exception as e:
        print("❌ Teacher Signup Failed")
        print(f"   Error: {str(e)}")
        return False

def test_student_signup():
    """Test student registration"""
    try:
        data = {
            "first_name": "Test",
            "last_name": "Student",
            "email": "student@test.com",
            "password": "testpassword123",
            "role": "student"
        }
        
        response = requests.post(f"{BASE_URL}/auth/signup", json=data)
        if response.status_code == 201:
            print("✅ Student Signup Passed")
            return True
        elif response.status_code == 400 and "already exists" in response.json().get('error', ''):
            print("✅ Student Already Exists (OK)")
            return True
        else:
            print("❌ Student Signup Failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return False
    except Exception as e:
        print("❌ Student Signup Failed")
        print(f"   Error: {str(e)}")
        return False

def test_teacher_login():
    """Test teacher login and return JWT token"""
    try:
        data = {
            "email": "teacher@test.com",
            "password": "testpassword123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=data)
        if response.status_code == 200:
            token = response.json()['access_token']
            print("✅ Teacher Login Passed")
            return token
        else:
            print("❌ Teacher Login Failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return None
    except Exception as e:
        print("❌ Teacher Login Failed")
        print(f"   Error: {str(e)}")
        return None

def test_student_login():
    """Test student login and return JWT token"""
    try:
        data = {
            "email": "student@test.com",
            "password": "testpassword123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=data)
        if response.status_code == 200:
            token = response.json()['access_token']
            print("✅ Student Login Passed")
            return token
        else:
            print("❌ Student Login Failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return None
    except Exception as e:
        print("❌ Student Login Failed")
        print(f"   Error: {str(e)}")
        return None

def test_create_class(teacher_token):
    """Test class creation"""
    try:
        headers = {"Authorization": f"Bearer {teacher_token}"}
        data = {
            "name": "Test Computer Science Class",
            "description": "Test class for AI attendance system"
        }
        
        response = requests.post(f"{BASE_URL}/classes/create", json=data, headers=headers)
        if response.status_code == 201:
            class_data = response.json()['class']
            print("✅ Class Creation Passed")
            print(f"   Class ID: {class_data['id']}")
            print(f"   Join Code: {class_data['join_code']}")
            return class_data['id'], class_data['join_code']
        else:
            print("❌ Class Creation Failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return None, None
    except Exception as e:
        print("❌ Class Creation Failed")
        print(f"   Error: {str(e)}")
        return None, None

def test_join_class(student_token, join_code):
    """Test student joining class"""
    try:
        headers = {"Authorization": f"Bearer {student_token}"}
        data = {"join_code": join_code}
        
        response = requests.post(f"{BASE_URL}/classes/join", json=data, headers=headers)
        if response.status_code == 200:
            print("✅ Class Join Passed")
            return True
        elif response.status_code == 400 and "already enrolled" in response.json().get('error', ''):
            print("✅ Student Already Enrolled (OK)")
            return True
        else:
            print("❌ Class Join Failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return False
    except Exception as e:
        print("❌ Class Join Failed")
        print(f"   Error: {str(e)}")
        return False

def create_test_image():
    """Create a simple test image"""
    # Create a simple red square image
    img = Image.new('RGB', (200, 200), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_data = buffer.getvalue()
    return base64.b64encode(img_data).decode('utf-8')

def test_face_data_upload(student_token):
    """Test face data upload (with simple test image)"""
    try:
        headers = {"Authorization": f"Bearer {student_token}"}
        test_image = create_test_image()
        
        data = {
            "images": [f"data:image/jpeg;base64,{test_image}"]
        }
        
        response = requests.post(f"{BASE_URL}/face-data/upload", json=data, headers=headers)
        if response.status_code == 200:
            print("✅ Face Data Upload Passed (Note: Test image may not contain faces)")
            return True
        else:
            result = response.json()
            if "No faces detected" in result.get('error', ''):
                print("✅ Face Data Upload Working (No faces in test image - expected)")
                return True
            else:
                print("❌ Face Data Upload Failed")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response.json()}")
                return False
    except Exception as e:
        print("❌ Face Data Upload Failed")
        print(f"   Error: {str(e)}")
        return False

def run_all_tests():
    """Run all tests in sequence"""
    print("🚀 Starting AI Attendance System Tests...\n")
    
    # Test 1: Health Check
    print("1. Testing Health Check...")
    if not test_health_check():
        print("❌ Cannot proceed - server is not healthy")
        return
    print()
    
    # Test 2: User Registration
    print("2. Testing User Registration...")
    test_teacher_signup()
    test_student_signup()
    print()
    
    # Test 3: User Login
    print("3. Testing User Login...")
    teacher_token = test_teacher_login()
    student_token = test_student_login()
    
    if not teacher_token or not student_token:
        print("❌ Cannot proceed - login failed")
        return
    print()
    
    # Test 4: Class Management
    print("4. Testing Class Management...")
    class_id, join_code = test_create_class(teacher_token)
    if class_id and join_code:
        test_join_class(student_token, join_code)
    print()
    
    # Test 5: Face Data
    print("5. Testing Face Data Upload...")
    test_face_data_upload(student_token)
    print()
    
    print("🎉 All tests completed!")
    print("\n📝 Next Steps:")
    print("1. Upload real face images through the API")
    print("2. Create attendance sessions")
    print("3. Test face recognition with classroom photos")
    print("4. Check attendance records")

if __name__ == "__main__":
    run_all_tests()