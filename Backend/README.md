# Attendly - AI-Powered Attendance System Backend

## Overview
Attendly is an AI-powered attendance tracking system that uses facial recognition technology to automatically identify and mark attendance for students in classes. The system supports role-based access for teachers and students with comprehensive class management and attendance tracking features.

## Features

### Authentication
- **User Registration**: Teachers and students can sign up with role-based accounts
- **JWT Authentication**: Secure login with JWT tokens
- **Profile Management**: Update profile information and change passwords

### Class Management
- **Create Classes**: Teachers can create classes with unique join codes
- **Join Classes**: Students can join classes using 6-digit codes
- **Class Administration**: Update class details, regenerate join codes

### Face Recognition System
- **Face Data Upload**: Students can upload facial data for AI recognition
- **Multiple Image Support**: Upload 2-5 images for better accuracy
- **Advanced Recognition**: Uses face_recognition library with confidence scoring

### Attendance Tracking
- **Session Management**: Create attendance sessions for specific dates
- **AI Recognition**: Process images to automatically identify students
- **Manual Marking**: Teachers can manually mark attendance
- **Attendance History**: View detailed attendance records and statistics

## Technical Stack

- **Backend Framework**: Flask (Python)
- **Database**: SQLAlchemy ORM with SQLite (easily configurable for PostgreSQL/MySQL)
- **Authentication**: JWT tokens with Flask-JWT-Extended
- **AI/ML**: face_recognition library (based on dlib)
- **Image Processing**: OpenCV, PIL (Pillow)
- **Data Processing**: NumPy, scikit-learn

## Project Structure

```
Backend/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
├── models/
│   └── models.py         # Database models
├── routes/
│   ├── auth.py           # Authentication endpoints
│   ├── classes.py        # Class management endpoints
│   ├── face_data.py      # Face data management endpoints
│   └── attendance.py     # Attendance tracking endpoints
└── uploads/
    └── face_images/      # Stored face images (created automatically)
```

## Installation and Setup

### 1. Clone and Navigate
```bash
cd Backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Update `.env` file with your configuration:
```env
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URL=sqlite:///attendly.db
```

### 5. Run the Application
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Documentation

### Base URL
`http://localhost:5000/api`

### Authentication Endpoints

#### POST /auth/signup
Register a new user (teacher or student)
```json
{
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student"  // or "teacher"
}
```

#### POST /auth/login
Login user
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

#### GET /auth/profile
Get current user profile (requires JWT token)

#### PUT /auth/profile
Update user profile (requires JWT token)

#### POST /auth/change-password
Change user password (requires JWT token)

### Class Management Endpoints

#### POST /classes/create
Create a new class (Teacher only)
```json
{
    "name": "Mathematics 101",
    "description": "Basic mathematics course"
}
```

#### GET /classes/my-classes
Get user's classes (created classes for teachers, enrolled classes for students)

#### GET /classes/{class_id}
Get specific class details

#### POST /classes/join
Join a class using join code (Student only)
```json
{
    "join_code": "ABC123"
}
```

#### POST /classes/{class_id}/leave
Leave a class (Student only)

#### PUT /classes/{class_id}/update
Update class details (Teacher only)

#### POST /classes/{class_id}/regenerate-code
Regenerate join code (Teacher only)

### Face Data Endpoints

#### POST /face-data/upload
Upload face data for recognition (Student only)
```json
{
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
}
```

#### POST /face-data/multiple-upload
Upload multiple images for better accuracy (Student only)
```json
{
    "images": [
        "data:image/jpeg;base64,...",
        "data:image/jpeg;base64,...",
        "data:image/jpeg;base64,..."
    ]
}
```

#### GET /face-data/my-data
Get current user's face data

#### DELETE /face-data/delete
Delete face data

### Attendance Endpoints

#### POST /attendance/recognize-faces
Process images and identify students (Teacher only)
```json
{
    "class_id": 1,
    "images": [
        "data:image/jpeg;base64,...",
        "data:image/jpeg;base64,..."
    ]
}
```

#### POST /attendance/create-session
Create attendance session (Teacher only)
```json
{
    "class_id": 1,
    "session_name": "Morning Lecture",
    "session_date": "2024-03-15"  // optional, defaults to today
}
```

#### POST /attendance/mark-attendance
Mark attendance for students (Teacher only)
```json
{
    "session_id": 1,
    "student_ids": [1, 2, 3, 4, 5]
}
```

#### GET /attendance/sessions/{class_id}
Get all attendance sessions for a class

#### GET /attendance/session/{session_id}/records
Get attendance records for a specific session

## Database Schema

### Users Table
- id (Primary Key)
- email (Unique)
- password_hash
- first_name, last_name
- role (teacher/student)
- created_at, is_active

### Classes Table
- id (Primary Key)
- name, description
- join_code (Unique 6-character)
- teacher_id (Foreign Key)
- created_at, is_active

### Class Enrollments Table
- id (Primary Key)
- student_id, class_id (Foreign Keys)
- enrolled_at, is_active
- Unique constraint on (student_id, class_id)

### Face Data Table
- id (Primary Key)
- user_id (Foreign Key)
- face_encoding (JSON string)
- image_path (optional)
- created_at, is_active

### Attendance Sessions Table
- id (Primary Key)
- class_id (Foreign Key)
- session_name, session_date
- created_by (Foreign Key)
- created_at, is_active

### Attendance Records Table
- id (Primary Key)
- session_id, student_id (Foreign Keys)
- status (present/absent/late)
- marked_at, marked_by
- Unique constraint on (session_id, student_id)

## Face Recognition System

### How It Works
1. **Face Data Upload**: Students upload clear face images
2. **Encoding Generation**: System extracts 128-dimensional face encodings
3. **Storage**: Encodings stored as JSON in database
4. **Recognition Process**: 
   - Teacher uploads class images
   - System extracts faces from images
   - Compares with enrolled students' encodings
   - Returns matched students with confidence scores

### Best Practices
- Upload 2-5 clear face images for better accuracy
- Ensure good lighting in uploaded images
- Use front-facing photos without obstructions
- Recognition tolerance can be adjusted (default: 0.6)

## Security Features

- **Password Hashing**: Werkzeug security for password hashing
- **JWT Tokens**: Secure authentication with JWT
- **Role-Based Access**: Strict role validation for all endpoints
- **Input Validation**: Comprehensive input validation and sanitization
- **Error Handling**: Secure error responses without sensitive information

## Error Handling

All endpoints return consistent error responses:
```json
{
    "error": "Error message",
    "details": "Additional details (only in debug mode)"
}
```

Common HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 409: Conflict
- 500: Internal Server Error

## Development and Testing

### Adding New Features
1. Create new route in appropriate blueprint
2. Add necessary database models
3. Implement proper error handling
4. Add authentication and authorization
5. Test with various scenarios

### Database Migrations
```bash
# Initialize migrations (first time)
flask db init

# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

## Deployment Considerations

### Production Settings
- Use PostgreSQL or MySQL instead of SQLite
- Set strong secret keys
- Enable HTTPS
- Configure CORS properly
- Use environment variables for all secrets
- Set up proper logging
- Consider using Redis for session storage

### Environment Variables
```env
FLASK_ENV=production
SECRET_KEY=very-strong-secret-key
JWT_SECRET_KEY=very-strong-jwt-key
DATABASE_URL=postgresql://user:password@host:port/database
```

## Performance Optimization

- **Database Indexing**: Add indexes on frequently queried columns
- **Image Optimization**: Compress images before processing
- **Caching**: Implement Redis caching for frequently accessed data
- **Background Tasks**: Use Celery for time-consuming face recognition tasks
- **CDN**: Use CDN for static assets

## Troubleshooting

### Common Issues

1. **Face Recognition Not Working**
   - Ensure face_recognition library is properly installed
   - Check image quality and lighting
   - Verify face encodings are properly stored

2. **Database Connection Issues**
   - Check DATABASE_URL in .env
   - Ensure database is created and accessible
   - Run migrations if needed

3. **JWT Token Issues**
   - Verify JWT_SECRET_KEY is set
   - Check token expiration settings
   - Ensure proper header format: `Authorization: Bearer <token>`

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit pull request

## License

This project is licensed under the MIT License.