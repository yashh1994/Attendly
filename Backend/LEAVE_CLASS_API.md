# Leave Class API Documentation

## Overview
This document describes the API endpoints for students to leave (unenroll from) classes and check their enrollment status.

---

## Endpoints

### 1. Leave Class
**Endpoint:** `POST /api/classes/<class_id>/leave`

**Description:** Allows a student to leave (unenroll from) a class. This is a soft delete - the enrollment record is preserved but marked as inactive.

**Authentication:** Required (JWT Bearer Token)

**Authorization:** Student role only

**URL Parameters:**
- `class_id` (integer, required) - The ID of the class to leave

**Request Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "message": "Successfully left the class",
  "class_id": 123,
  "class_name": "Mathematics 101"
}
```

**Error Responses:**

- **404 Not Found** - User not found
```json
{
  "error": "User not found"
}
```

- **403 Forbidden** - Non-student user trying to leave
```json
{
  "error": "Only students can leave classes"
}
```

- **404 Not Found** - Not enrolled in class
```json
{
  "error": "Not enrolled in this class"
}
```

- **500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "details": "Error message"
}
```

**Example Usage (Python):**
```python
import requests

headers = {
    'Authorization': 'Bearer your_jwt_token_here',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://localhost:5000/api/classes/123/leave',
    headers=headers
)

print(response.json())
```

**Example Usage (Flutter/Dart):**
```dart
final response = await apiService.leaveClass(classId: 123);
print(response['message']);
```

---

### 2. Get Enrollment Status
**Endpoint:** `GET /api/classes/<class_id>/enrollment-status`

**Description:** Gets the enrollment status and history for a student in a specific class.

**Authentication:** Required (JWT Bearer Token)

**Authorization:** Student role only

**URL Parameters:**
- `class_id` (integer, required) - The ID of the class to check

**Request Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "class_id": 123,
  "class_name": "Mathematics 101",
  "is_enrolled": true,
  "can_rejoin": true,
  "enrollment_history": [
    {
      "id": 456,
      "joined_at": "2025-10-15T10:30:00",
      "left_at": "2025-10-18T14:20:00",
      "is_active": false
    },
    {
      "id": 789,
      "joined_at": "2025-10-19T09:00:00",
      "left_at": null,
      "is_active": true
    }
  ],
  "total_enrollments": 2
}
```

**Response Fields:**
- `class_id` - The class ID
- `class_name` - The name of the class
- `is_enrolled` - Boolean indicating if currently enrolled (active)
- `can_rejoin` - Boolean indicating if student can rejoin (always true)
- `enrollment_history` - Array of all enrollment records (current and past)
  - `id` - Enrollment record ID
  - `joined_at` - ISO timestamp when joined
  - `left_at` - ISO timestamp when left (null if still active)
  - `is_active` - Boolean indicating if enrollment is active
- `total_enrollments` - Total number of times enrolled in this class

**Error Responses:**

- **404 Not Found** - User not found
```json
{
  "error": "User not found"
}
```

- **403 Forbidden** - Non-student user
```json
{
  "error": "Only students can check enrollment status"
}
```

- **404 Not Found** - Class not found
```json
{
  "error": "Class not found"
}
```

- **500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "details": "Error message"
}
```

---

## Features

### Soft Delete
- When a student leaves a class, the enrollment is not deleted from the database
- The `is_active` flag is set to `False`
- The `updated_at` timestamp is updated
- This preserves:
  - Attendance history
  - Enrollment records
  - Analytics data

### Re-enrollment
- Students can rejoin a class they previously left
- Simply use the join code again
- Creates a new enrollment record
- Previous enrollment history is preserved

### Security
- JWT authentication required for all endpoints
- Role-based access control (student only)
- Authorization checks on every request
- Validates enrollment before allowing leave

### Logging
- All leave actions are logged to console
- Includes user email, class name, and timestamp
- Errors are logged with full details

---

## Database Schema

### ClassEnrollment Table
```python
class ClassEnrollment(db.Model):
    __tablename__ = 'class_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
```

**Key Fields:**
- `is_active` - Set to False when student leaves
- `updated_at` - Updated when student leaves
- `created_at` - Original enrollment date (never changes)

---

## Testing

### Test Leave Class API

**1. Enroll in a class first:**
```bash
curl -X POST http://localhost:5000/api/classes/join \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"join_code": "ABC123"}'
```

**2. Leave the class:**
```bash
curl -X POST http://localhost:5000/api/classes/123/leave \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**3. Check enrollment status:**
```bash
curl -X GET http://localhost:5000/api/classes/123/enrollment-status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**4. Rejoin the class:**
```bash
curl -X POST http://localhost:5000/api/classes/join \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"join_code": "ABC123"}'
```

---

## Error Handling

### Common Issues

**Issue 1: "Not enrolled in this class"**
- **Cause:** Student is not currently enrolled or already left
- **Solution:** Check enrollment status first, or rejoin with join code

**Issue 2: "Only students can leave classes"**
- **Cause:** Teacher or admin user trying to use student endpoint
- **Solution:** Use correct user role (student)

**Issue 3: 401 Unauthorized**
- **Cause:** Missing or invalid JWT token
- **Solution:** Login again to get fresh token

---

## Integration with Flutter

### API Service Method
```dart
Future<Map<String, dynamic>> leaveClass({required int classId}) async {
  print('🔥 FLUTTER: Leaving class with ID: $classId');
  print('🔥 FLUTTER: URL: $baseUrl/api/classes/$classId/leave');
  
  final response = await http.post(
    Uri.parse('$baseUrl/api/classes/$classId/leave'),
    headers: headers,
  );

  print('🔥 FLUTTER: Leave class response code: ${response.statusCode}');
  print('🔥 FLUTTER: Leave class response body: ${response.body}');
  
  return _handleResponse(response);
}
```

### Usage Example
```dart
try {
  final result = await apiService.leaveClass(classId: classModel.id);
  
  // Update UI
  setState(() {
    enrolledClasses.removeWhere((c) => c.id == classModel.id);
  });
  
  // Show success message
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(result['message']),
      backgroundColor: Colors.green,
    ),
  );
} catch (e) {
  // Handle error
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text('Failed to leave class: $e'),
      backgroundColor: Colors.red,
    ),
  );
}
```

---

## Notes

1. **Data Preservation**: Leaving a class does NOT delete attendance records or enrollment history
2. **Re-enrollment**: Students can rejoin classes they previously left using the join code
3. **Teacher Notifications**: Teachers are NOT notified when students leave (consider adding webhook/notification in future)
4. **Analytics**: Enrollment history is preserved for analytics and reporting purposes
5. **Soft Delete**: All leaves are soft deletes (is_active = False) for data integrity

---

## Future Enhancements

Potential improvements for this API:

1. **Leave Reason**: Add optional reason field for why student is leaving
2. **Teacher Notification**: Notify teacher when student leaves
3. **Leave Confirmation**: Add confirmation token to prevent accidental leaves
4. **Leave Statistics**: Track leave rates per class
5. **Prevent Rejoining**: Add option for teachers to prevent rejoining after leaving
6. **Grace Period**: Add grace period where leave can be undone
7. **Bulk Leave**: Allow leaving multiple classes at once

---

## Support

For issues or questions about the Leave Class API:
- Check the logs for detailed error messages
- Verify JWT token is valid
- Ensure user has student role
- Confirm class ID exists and user is enrolled

---

**Last Updated:** October 20, 2025
**API Version:** 1.0
**Backend Framework:** Flask
**Database:** PostgreSQL
