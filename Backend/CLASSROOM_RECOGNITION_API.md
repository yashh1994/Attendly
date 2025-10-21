# Classroom Photo Recognition API Documentation

## Overview
This API enables teachers to take a classroom photo and automatically recognize students based on their registered facial data. The system extracts all faces from the photo and matches them only against students enrolled in the specified class.

---

## API Endpoints

### 1. Get Class Students with Facial Data
**GET** `/api/face-data/class/<class_id>/students-with-facial-data`

Get all students enrolled in a class who have registered facial data.

#### Authorization
- **Required:** Teacher role
- **Header:** `Authorization: Bearer <teacher_token>`

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| class_id | integer | The ID of the class |

#### Response (200 OK)
```json
{
  "class_id": 123,
  "class_name": "Mathematics 101",
  "total_enrolled_students": 30,
  "students_with_facial_data": 25,
  "coverage_percentage": 83.33,
  "students": [
    {
      "student_id": 5,
      "name": "John Doe",
      "email": "john.doe@example.com",
      "vector_db_id": "user_5",
      "encoding_version": "v2.0_recognition_optimized",
      "face_data_registered_at": "2025-10-15T10:30:00"
    }
  ]
}
```

#### Error Responses
- **403:** Not a teacher or no access to class
- **404:** Class not found
- **500:** Internal server error

---

### 2. Recognize Students from Classroom Photo
**POST** `/api/face-data/recognize-from-photo`

Upload a classroom photo to automatically recognize and identify enrolled students.

#### Authorization
- **Required:** Teacher role
- **Header:** `Authorization: Bearer <teacher_token>`

#### Request Body
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "class_id": 123,
  "recognition_threshold": 0.6
}
```

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| image | string | Yes | Base64 encoded classroom photo |
| class_id | integer | Yes | The ID of the class |
| recognition_threshold | float | No | Recognition confidence threshold (0.4-0.9, default 0.6). Lower = stricter matching |

#### Recognition Threshold Guide
- **0.4-0.5:** Very strict (fewer matches, very high confidence)
- **0.6 (default):** Balanced (recommended for most cases)
- **0.7-0.8:** Lenient (more matches, may include some false positives)
- **0.9:** Very lenient (not recommended for production)

#### Response (200 OK)
```json
{
  "success": true,
  "class_id": 123,
  "class_name": "Mathematics 101",
  "teacher_id": 10,
  "total_faces_detected": 15,
  "total_recognized": 12,
  "total_enrolled_with_data": 25,
  "recognition_threshold": 0.6,
  "recognized_students": [
    {
      "student_id": 5,
      "name": "John Doe",
      "email": "john.doe@example.com",
      "confidence": 0.85,
      "face_number": 1,
      "face_location": {
        "top": 100,
        "right": 250,
        "bottom": 300,
        "left": 150
      }
    },
    {
      "student_id": 8,
      "name": "Jane Smith",
      "email": "jane.smith@example.com",
      "confidence": 0.78,
      "face_number": 2,
      "face_location": {
        "top": 120,
        "right": 450,
        "bottom": 320,
        "left": 350
      }
    }
  ],
  "unrecognized_faces": 3,
  "recognition_rate": 80.0,
  "coverage_rate": 48.0
}
```

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether recognition was successful |
| class_id | integer | The class ID processed |
| class_name | string | Name of the class |
| teacher_id | integer | ID of teacher who performed recognition |
| total_faces_detected | integer | Total number of faces found in photo |
| total_recognized | integer | Number of faces successfully matched to students |
| total_enrolled_with_data | integer | Total enrolled students with facial data |
| recognition_threshold | float | Threshold used for matching |
| recognized_students | array | List of recognized students with details |
| unrecognized_faces | integer | Number of faces that couldn't be matched |
| recognition_rate | float | Percentage of detected faces that were recognized |
| coverage_rate | float | Percentage of enrolled students recognized |

#### Error Responses

**400 Bad Request - No Faces Detected:**
```json
{
  "success": true,
  "message": "No faces detected in the image",
  "class_id": 123,
  "class_name": "Mathematics 101",
  "total_faces_detected": 0,
  "total_recognized": 0,
  "recognized_students": [],
  "unrecognized_faces": 0
}
```

**400 Bad Request - No Facial Data:**
```json
{
  "success": false,
  "error": "No students in this class have registered facial data",
  "class_id": 123,
  "class_name": "Mathematics 101",
  "total_faces_detected": 15,
  "recommendation": "Ask students to register their facial data first"
}
```

**403 Forbidden:**
```json
{
  "error": "Only teachers can perform facial recognition"
}
```

**404 Not Found:**
```json
{
  "error": "Class not found or you do not have access"
}
```

---

## Usage Flow

### Step 1: Check Class Coverage
Before taking attendance, check how many students have registered facial data:

```python
import requests

headers = {
    "Authorization": f"Bearer {teacher_token}"
}

response = requests.get(
    f"http://localhost:5000/api/face-data/class/123/students-with-facial-data",
    headers=headers
)

data = response.json()
print(f"Coverage: {data['coverage_percentage']}%")
print(f"{data['students_with_facial_data']}/{data['total_enrolled_students']} students ready")
```

### Step 2: Take Classroom Photo
Capture a photo with:
- ✅ Good lighting
- ✅ Clear view of students' faces
- ✅ Students looking towards camera
- ✅ Minimal obstructions (masks, hats, etc.)

### Step 3: Recognize Students
```python
import base64
import requests

# Read and encode image
with open("classroom_photo.jpg", "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode()

# Add data URL prefix
image_data = f"data:image/jpeg;base64,{base64_image}"

headers = {
    "Authorization": f"Bearer {teacher_token}",
    "Content-Type": "application/json"
}

payload = {
    "image": image_data,
    "class_id": 123,
    "recognition_threshold": 0.6
}

response = requests.post(
    "http://localhost:5000/api/face-data/recognize-from-photo",
    headers=headers,
    json=payload
)

result = response.json()

print(f"Detected {result['total_faces_detected']} faces")
print(f"Recognized {result['total_recognized']} students:")
for student in result['recognized_students']:
    print(f"  - {student['name']} (confidence: {student['confidence']:.2f})")
```

### Step 4: Mark Attendance (Optional)
Use the recognized student list to automatically mark attendance:

```python
recognized_student_ids = [s['student_id'] for s in result['recognized_students']]

# Mark attendance for recognized students
for student_id in recognized_student_ids:
    mark_attendance(
        session_id=attendance_session_id,
        student_id=student_id,
        status='present'
    )
```

---

## Technical Details

### Face Detection
- **Algorithm:** HOG (Histogram of Oriented Gradients)
- **Model:** Configurable (default: 'large' for better accuracy)
- **Processing:** All faces extracted simultaneously

### Face Recognition
- **Method:** Vector similarity search using ChromaDB
- **Encoding:** 128-dimensional face embeddings
- **Matching:** Cosine similarity with configurable threshold

### Performance Optimization
- ✅ Only compares against enrolled students (not all users)
- ✅ Vector database for fast similarity search
- ✅ Prevents duplicate recognition of same student
- ✅ Indexed database queries

### Security
- ✅ Teacher-only access
- ✅ Class ownership verification
- ✅ JWT token authentication
- ✅ Only matches within specific class

---

## Best Practices

### For Teachers

1. **Before Taking Attendance:**
   - Check facial data coverage using `/students-with-facial-data` endpoint
   - Ensure at least 70% of students have registered
   - Remind students without data to register

2. **Taking Photos:**
   - Use landscape orientation
   - Capture from slightly elevated position
   - Ensure even lighting across classroom
   - Ask students to look towards camera
   - Take multiple photos if first attempt has low recognition rate

3. **Adjusting Threshold:**
   - Start with default (0.6)
   - If too many false positives: Lower to 0.5
   - If missing obvious matches: Increase to 0.7
   - Monitor confidence scores to calibrate

4. **Handling Unrecognized Faces:**
   - Manual verification for unrecognized faces
   - Ask students to update facial data if consistently unrecognized
   - Consider environmental factors (lighting, obstructions)

### For Students

1. **Registering Facial Data:**
   - Capture 10 high-quality photos
   - Vary angles slightly (not extreme)
   - Good lighting, neutral expression
   - No obstructions (glasses OK, but remove sunglasses)

2. **During Attendance:**
   - Face camera when photo is taken
   - Remove masks/hats if possible
   - Ensure face is visible and well-lit

---

## Integration with Attendance System

This API is designed to integrate with the existing attendance system:

```python
# Complete attendance workflow
def take_photo_attendance(teacher_token, class_id, session_id, photo_path):
    """
    Complete workflow for photo-based attendance
    """
    # 1. Check coverage
    coverage = check_facial_data_coverage(teacher_token, class_id)
    if coverage['coverage_percentage'] < 50:
        print("Warning: Less than 50% students have facial data")
    
    # 2. Recognize students from photo
    recognition_result = recognize_students(
        teacher_token, 
        class_id, 
        photo_path
    )
    
    # 3. Mark attendance for recognized students
    for student in recognition_result['recognized_students']:
        mark_attendance(
            teacher_token,
            session_id,
            student['student_id'],
            status='present',
            recognition_confidence=student['confidence'],
            recognition_method='ai_face'
        )
    
    # 4. Return summary
    return {
        'total_marked': len(recognition_result['recognized_students']),
        'needs_manual_verification': recognition_result['unrecognized_faces'],
        'recognition_rate': recognition_result['recognition_rate']
    }
```

---

## Error Handling

### Common Issues

1. **"No faces detected"**
   - Solution: Ensure photo has clear faces, good lighting
   - Check: Photo resolution, blur, distance

2. **"No students with facial data"**
   - Solution: Students need to register facial data first
   - Use: `/student/upload-facial-data` endpoint

3. **Low recognition rate**
   - Solution: Adjust threshold, improve photo quality
   - Check: Lighting, angles, obstructions

4. **Vector DB errors**
   - Solution: Ensure ChromaDB is running
   - Fallback: System continues with direct comparison (slower)

---

## API Testing

### Using cURL

```bash
# Get students with facial data
curl -X GET \
  "http://localhost:5000/api/face-data/class/123/students-with-facial-data" \
  -H "Authorization: Bearer YOUR_TEACHER_TOKEN"

# Recognize from photo
curl -X POST \
  "http://localhost:5000/api/face-data/recognize-from-photo" \
  -H "Authorization: Bearer YOUR_TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQ...",
    "class_id": 123,
    "recognition_threshold": 0.6
  }'
```

### Using Postman

1. **GET Students with Facial Data:**
   - Method: GET
   - URL: `http://localhost:5000/api/face-data/class/123/students-with-facial-data`
   - Headers: 
     - `Authorization: Bearer YOUR_TEACHER_TOKEN`

2. **POST Recognize from Photo:**
   - Method: POST
   - URL: `http://localhost:5000/api/face-data/recognize-from-photo`
   - Headers:
     - `Authorization: Bearer YOUR_TEACHER_TOKEN`
     - `Content-Type: application/json`
   - Body (raw JSON):
   ```json
   {
     "image": "data:image/jpeg;base64,/9j/4AAQ...",
     "class_id": 123,
     "recognition_threshold": 0.6
   }
   ```

---

## Performance Metrics

### Expected Performance
- **Face Detection:** ~500ms for 20 faces
- **Face Recognition:** ~100ms per face (with vector DB)
- **Total Processing:** ~2-3 seconds for typical classroom (30 students)

### Accuracy
- **True Positive Rate:** 85-95% (with good quality photos)
- **False Positive Rate:** <5% (with threshold 0.6)
- **Coverage:** Depends on student registration

---

## Future Enhancements

1. **Batch Processing:** Process multiple photos simultaneously
2. **Quality Assessment:** Pre-validate photo quality before recognition
3. **Real-time Recognition:** Live camera feed processing
4. **Confidence Visualization:** Return annotated image with bounding boxes
5. **Historical Analytics:** Track recognition accuracy over time

---

## Support

For issues or questions:
1. Check this documentation
2. Review API error messages
3. Check server logs: `Backend/logs/app.log`
4. Verify vector database status
5. Contact system administrator

---

**Last Updated:** October 21, 2025
**API Version:** 1.0
**Backend Version:** Python Flask
