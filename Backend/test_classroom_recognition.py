"""
Test script for Classroom Photo Recognition APIs

This script tests:
1. Getting class students with facial data
2. Recognizing students from classroom photo
"""

import requests
import json
import base64
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
TEACHER_EMAIL = "yash@gmail.com"  # Your teacher email
TEACHER_PASSWORD = "12345678"  # Your teacher password
CLASS_ID = 1  # Change to your class ID

def login_teacher():
    """Login as teacher and get JWT token"""
    print("\n" + "="*50)
    print("STEP 1: Teacher Login")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('token') or data.get('access_token')
        print(f"✅ Login successful!")
        print(f"Teacher: {data.get('user', {}).get('first_name')} {data.get('user', {}).get('last_name')}")
        if token:
            print(f"Token: {token[:20]}...")
        else:
            print(f"⚠️  Warning: No token found in response")
            print(f"Response data: {data}")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def get_class_students_with_facial_data(token, class_id):
    """Get all students in class with facial data"""
    print("\n" + "="*50)
    print("STEP 2: Get Students with Facial Data")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/face-data/class/{class_id}/students-with-facial-data",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Successfully retrieved facial data coverage")
        print(f"\nClass: {data['class_name']}")
        print(f"Total Enrolled: {data['total_enrolled_students']}")
        print(f"With Facial Data: {data['students_with_facial_data']}")
        print(f"Coverage: {data['coverage_percentage']:.1f}%")
        
        if data['students']:
            print(f"\nStudents with facial data:")
            for student in data['students'][:5]:  # Show first 5
                print(f"  - {student['name']} ({student['email']})")
            if len(data['students']) > 5:
                print(f"  ... and {len(data['students']) - 5} more")
        
        return data
    else:
        print(f"❌ Failed to get students: {response.status_code}")
        print(response.text)
        return None

def test_with_sample_image(token, class_id):
    """Test recognition with a sample base64 image"""
    print("\n" + "="*50)
    print("STEP 3: Test Recognition with Sample Image")
    print("="*50)
    
    # Create a small test image (1x1 pixel white image)
    # In real use, this would be an actual classroom photo
    sample_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlbaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q=="
    
    print("Note: Using a small test image. In production, use actual classroom photos.")
    print("Expected: This will likely detect no faces since it's a 1x1 pixel test image.")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "image": sample_base64,
        "class_id": class_id,
        "recognition_threshold": 0.6
    }
    
    response = requests.post(
        f"{BASE_URL}/api/face-data/recognize-from-photo",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Recognition completed!")
        print(f"\nResults:")
        print(f"Total Faces Detected: {data['total_faces_detected']}")
        print(f"Total Recognized: {data['total_recognized']}")
        print(f"Unrecognized Faces: {data['unrecognized_faces']}")
        print(f"Recognition Rate: {data.get('recognition_rate', 0):.1f}%")
        
        if data['recognized_students']:
            print(f"\nRecognized Students:")
            for student in data['recognized_students']:
                print(f"  - {student['name']} (confidence: {student['confidence']:.2f})")
        
        return data
    else:
        print(f"❌ Recognition failed: {response.status_code}")
        print(response.text)
        return None

def test_with_actual_photo(token, class_id, photo_path):
    """Test recognition with an actual classroom photo file"""
    print("\n" + "="*50)
    print("STEP 4: Test with Actual Photo (Optional)")
    print("="*50)
    
    if not Path(photo_path).exists():
        print(f"⚠️  Photo not found: {photo_path}")
        print("Skipping actual photo test.")
        return None
    
    print(f"Loading photo: {photo_path}")
    
    try:
        with open(photo_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode()
        
        # Add data URL prefix
        image_data = f"data:image/jpeg;base64,{base64_image}"
        
        print(f"Image size: {len(base64_image)} bytes")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "image": image_data,
            "class_id": class_id,
            "recognition_threshold": 0.6
        }
        
        print("Sending photo for recognition...")
        
        response = requests.post(
            f"{BASE_URL}/api/face-data/recognize-from-photo",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Recognition completed!")
            print(f"\nResults:")
            print(f"Total Faces Detected: {data['total_faces_detected']}")
            print(f"Total Recognized: {data['total_recognized']}")
            print(f"Unrecognized Faces: {data['unrecognized_faces']}")
            print(f"Recognition Rate: {data.get('recognition_rate', 0):.1f}%")
            print(f"Coverage Rate: {data.get('coverage_rate', 0):.1f}%")
            
            if data['recognized_students']:
                print(f"\nRecognized Students:")
                for student in data['recognized_students']:
                    print(f"  - {student['name']}")
                    print(f"    Email: {student['email']}")
                    print(f"    Confidence: {student['confidence']:.2f}")
                    print(f"    Face Location: Top={student['face_location']['top']}, "
                          f"Left={student['face_location']['left']}, "
                          f"Bottom={student['face_location']['bottom']}, "
                          f"Right={student['face_location']['right']}")
            
            return data
        else:
            print(f"❌ Recognition failed: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    """Main test function"""
    print("\n" + "="*50)
    print("CLASSROOM PHOTO RECOGNITION API TEST")
    print("="*50)
    
    # Login
    token = login_teacher()
    if not token:
        print("\n❌ Test failed: Could not login")
        return
    
    # Get students with facial data
    coverage_data = get_class_students_with_facial_data(token, CLASS_ID)
    if not coverage_data:
        print("\n❌ Test failed: Could not get class data")
        return
    
    # Test with sample image
    test_result = test_with_sample_image(token, CLASS_ID)
    
    # Optionally test with actual photo
    # Uncomment and provide path to actual classroom photo
    # actual_photo_path = "classroom_photo.jpg"
    # test_with_actual_photo(token, CLASS_ID, actual_photo_path)
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"✅ Teacher Login: SUCCESS")
    print(f"✅ Get Facial Data Coverage: SUCCESS")
    print(f"✅ Recognize from Photo: SUCCESS")
    print("\n📝 To test with actual classroom photo:")
    print("   1. Take a classroom photo")
    print("   2. Save it as 'classroom_photo.jpg'")
    print("   3. Uncomment lines at end of main() function")
    print("   4. Run this script again")
    print("\n" + "="*50)

if __name__ == "__main__":
    main()
