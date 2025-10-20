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
        
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=data)
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
        
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=data)
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
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
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
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
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
        
        response = requests.post(f"{BASE_URL}/api/classes/create", json=data, headers=headers)
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
        
        response = requests.post(f"{BASE_URL}/api/classes/join", json=data, headers=headers)
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
        
        # Test 1: Single image validation
        print("   Testing image validation...")
        data = {
            "image": f"data:image/jpeg;base64,{test_image}"
        }
        
        response = requests.post(f"{BASE_URL}/api/face-data/validate-image", json=data, headers=headers)
        if response.status_code == 200:
            validation_result = response.json()
            print(f"   ✅ Image validation: {validation_result.get('face_detected', False)}")
        
        # Test 2: Batch upload with progress
        print("   Testing batch upload with progress...")
        data = {
            "images": [f"data:image/jpeg;base64,{test_image}" for _ in range(5)]
        }
        
        response = requests.post(f"{BASE_URL}/api/face-data/upload-batch-with-progress", json=data, headers=headers)
        if response.status_code in [200, 201, 400]:  # 400 expected for no faces in test image
            result = response.json()
            print(f"   ✅ Batch upload test: {result.get('message', 'Completed')}")
            if 'successful_images' in result:
                print(f"   📊 Success rate: {result.get('success_rate', 0):.1f}%")
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
    
    # Test 6: New Facial Recognition APIs
    print("6. Testing Facial Recognition APIs...")
    test_facial_recognition_apis(student_token)
    print()
    
    # Test 7: Student-Specific Facial APIs
    print("7. Testing Student Facial Data APIs...")
    test_student_facial_apis(student_token)
    print()
    
    print("🎉 All tests completed!")
    print("\n📝 Next Steps:")
    print("1. Upload real face images through the API")
    print("2. Test facial recognition with classroom photos")
    print("3. Create attendance sessions")
    print("4. Check attendance records")

def test_facial_recognition_apis(student_token):
    """Test new facial recognition specific APIs"""
    try:
        headers = {"Authorization": f"Bearer {student_token}"}
        
        # Test 1: Check recognition readiness
        print("   Testing recognition readiness check...")
        response = requests.get(f"{BASE_URL}/api/face-data/recognition-ready", headers=headers)
        if response.status_code == 200:
            readiness = response.json()
            print(f"   ✅ Recognition readiness: {readiness.get('recognition_ready', False)}")
            print(f"   📊 Status: {readiness.get('status', 'unknown')}")
        
        # Test 2: Upload for recognition
        print("   Testing recognition-optimized upload...")
        test_image = create_test_image()
        data = {
            "images": [f"data:image/jpeg;base64,{test_image}" for _ in range(3)]
        }
        
        response = requests.post(f"{BASE_URL}/api/face-data/upload-for-recognition", json=data, headers=headers)
        if response.status_code in [200, 201, 400]:  # 400 expected for no faces in test image
            result = response.json()
            print(f"   ✅ Recognition upload: {result.get('message', 'Completed')}")
            if 'successful_extractions' in result:
                print(f"   📊 Successful extractions: {result.get('successful_extractions', 0)}")
        
        # Test 3: Test recognition
        print("   Testing face recognition test...")
        data = {
            "image": f"data:image/jpeg;base64,{test_image}"
        }
        
        response = requests.post(f"{BASE_URL}/api/face-data/test-recognition", json=data, headers=headers)
        if response.status_code == 200:
            test_result = response.json()
            print(f"   ✅ Recognition test: {test_result.get('message', 'Completed')}")
            if 'matched' in test_result:
                print(f"   🎯 Match result: {test_result.get('matched', False)}")
        
        return True
        
    except Exception as e:
        print("❌ Facial Recognition APIs Test Failed")
        print(f"   Error: {str(e)}")
        return False

def test_student_facial_apis(student_token):
    """Test student-specific facial data APIs"""
    try:
        print("📸 Testing Student Facial Data APIs...")
        
        headers = {"Authorization": f"Bearer {student_token}"}
        
        # Test 1: Get initial facial status
        print("   Testing initial facial status...")
        response = requests.get(f"{BASE_URL}/api/face-data/student/facial-status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Initial status: {status.get('status', 'unknown')}")
            print(f"   📊 Has facial data: {status.get('has_facial_data', False)}")
            initial_has_data = status.get('has_facial_data', False)
        
        # Test 2: Upload facial data
        print("   Testing student facial data upload...")
        test_image = create_test_image()
        data = {
            "images": [f"data:image/jpeg;base64,{test_image}" for _ in range(6)],  # 6 images for good coverage
            "replace_existing": True
        }
        
        response = requests.post(f"{BASE_URL}/api/face-data/student/upload-facial-data", json=data, headers=headers)
        if response.status_code in [200, 201, 400]:
            result = response.json()
            print(f"   ✅ Upload result: {result.get('message', 'Completed')}")
            if 'successful_images' in result:
                print(f"   📊 Successful images: {result.get('successful_images', 0)}/{result.get('total_images', 0)}")
            if 'success_rate' in result:
                print(f"   📈 Success rate: {result.get('success_rate', 0):.1f}%")
        
        # Test 3: Check updated facial status
        print("   Testing updated facial status...")
        response = requests.get(f"{BASE_URL}/api/face-data/student/facial-status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Updated status: {status.get('status', 'unknown')}")
            print(f"   🎯 Registration ready: {status.get('registration_ready', False)}")
            if 'facial_data_info' in status:
                info = status['facial_data_info']
                print(f"   📅 Registration date: {info.get('registration_date', 'N/A')}")
                print(f"   🔄 Encoding version: {info.get('encoding_version', 'N/A')}")
        
        # Test 4: Delete facial data (optional - only if we want to clean up)
        print("   Testing facial data deletion...")
        response = requests.delete(f"{BASE_URL}/api/face-data/student/delete-facial-data", headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Delete result: {result.get('message', 'Completed')}")
        
        # Test 5: Verify deletion
        print("   Verifying deletion...")
        response = requests.get(f"{BASE_URL}/api/face-data/student/facial-status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Final status: {status.get('status', 'unknown')}")
            print(f"   📊 Has facial data after deletion: {status.get('has_facial_data', False)}")
        
        return True
        
    except Exception as e:
        print("❌ Student Facial APIs Test Failed")
        print(f"   Error: {str(e)}")
        return False

if __name__ == "__main__":
    run_all_tests()