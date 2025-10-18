# AI-Powered Attendance System Backend Setup Guide

## Overview
This backend system provides AI-powered face recognition for attendance tracking using Flask, PostgreSQL, and vector databases.

## System Requirements
- Python 3.8+
- PostgreSQL 12+
- Git

## Quick Setup

### 1. Clone and Install Dependencies
```bash
cd "F:\Marwadi\Sem 8\Mobile App\Backend"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. PostgreSQL Database Setup

#### Install PostgreSQL (if not installed)
Download from: https://www.postgresql.org/download/windows/

#### Create Database
```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE DATABASE ai_attendance_db;
CREATE USER ai_attendance_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE ai_attendance_db TO ai_attendance_user;

-- Connect to the new database
\c ai_attendance_db;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO ai_attendance_user;
```

### 3. Environment Configuration
Create `.env` file in the Backend directory:

```env
# Database Configuration
DATABASE_URL=postgresql://ai_attendance_user:your_secure_password@localhost:5432/ai_attendance_db

# JWT Configuration
JWT_SECRET_KEY=your_super_secret_jwt_key_here_make_it_long_and_random

# Face Recognition Settings
FACE_RECOGNITION_TOLERANCE=0.6
FACE_ENCODING_MODEL=large

# Vector Database Configuration (Choose one)
VECTOR_DB_TYPE=chromadb
# VECTOR_DB_TYPE=faiss

# ChromaDB Settings (if using ChromaDB)
CHROMADB_PATH=./data/chromadb
CHROMADB_COLLECTION=face_encodings

# FAISS Settings (if using FAISS)
FAISS_INDEX_PATH=./data/faiss_index.bin
FAISS_METADATA_PATH=./data/faiss_metadata.json

# Security
BCRYPT_LOG_ROUNDS=12

# Flask Settings
FLASK_ENV=development
FLASK_DEBUG=True
```

### 4. Initialize Database
```bash
python app.py
```

The application will automatically create all database tables on first run.

### 5. Test the Setup
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "vector_db": "available",
  "vector_db_type": "chromadb"
}
```

## API Endpoints

### Authentication APIs

#### 1. User Registration
```bash
POST /auth/signup
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "password": "securepassword123",
  "role": "teacher"
}
```

#### 2. User Login
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "securepassword123"
}
```

### Class Management APIs

#### 1. Create Class (Teacher Only)
```bash
POST /classes/create
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json

{
  "name": "Computer Science 101",
  "description": "Introduction to Programming"
}
```

#### 2. Join Class (Student Only)
```bash
POST /classes/join
Authorization: Bearer <student_jwt_token>
Content-Type: application/json

{
  "join_code": "CS101ABC"
}
```

### Face Data APIs

#### 1. Upload Face Data (Student Only)
```bash
POST /face-data/upload
Authorization: Bearer <student_jwt_token>
Content-Type: application/json

{
  "images": ["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/..."]
}
```

### Attendance APIs

#### 1. Recognize Faces (Teacher Only)
```bash
POST /attendance/recognize-faces
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json

{
  "class_id": 1,
  "images": [
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/...",
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/..."
  ],
  "tolerance": 0.6
}
```

#### 2. Create Attendance Session (Teacher Only)
```bash
POST /attendance/create-session
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json

{
  "class_id": 1,
  "session_name": "Week 1 Lecture",
  "session_date": "2024-01-15"
}
```

#### 3. Mark Attendance (Teacher Only)
```bash
POST /attendance/mark-attendance
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json

{
  "session_id": 1,
  "student_ids": [2, 3, 4],
  "recognition_method": "vector_db",
  "confidence_scores": {
    "2": 0.85,
    "3": 0.92,
    "4": 0.78
  }
}
```

## Vector Database Options

### ChromaDB (Recommended)
- **Pros**: Easy setup, great for development, built-in persistence
- **Setup**: Automatic with environment variables
- **Storage**: File-based persistence

### FAISS (For Production)
- **Pros**: Highly optimized, better performance at scale
- **Setup**: Requires index management
- **Storage**: Binary index files

## Project Structure
```
Backend/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── models/
│   └── models.py         # Database models
├── routes/
│   ├── auth.py          # Authentication endpoints
│   ├── classes.py       # Class management endpoints
│   ├── face_data.py     # Face data upload endpoints
│   └── attendance.py    # Attendance endpoints
├── services/
│   └── vector_db.py     # Vector database abstraction
└── data/                # Vector database storage (auto-created)
    ├── chromadb/        # ChromaDB data
    ├── faiss_index.bin  # FAISS index
    └── faiss_metadata.json # FAISS metadata
```

## Common Issues & Solutions

### 1. PostgreSQL Connection Error
- Ensure PostgreSQL service is running
- Verify database credentials in `.env`
- Check if database exists

### 2. Face Recognition Model Download
Face recognition models will be downloaded automatically on first use. This may take a few minutes.

### 3. Vector Database Issues
- **ChromaDB**: Ensure `./data/chromadb` directory is writable
- **FAISS**: Ensure sufficient disk space for index files

### 4. Memory Issues
For large numbers of face encodings, consider:
- Using FAISS instead of ChromaDB
- Implementing batch processing
- Increasing system memory

## Development Workflow

### 1. Adding New Students
1. Student registers with email/password
2. Student uploads face images (3-5 recommended)
3. Teacher creates class and shares join code
4. Student joins class using join code

### 2. Taking Attendance
1. Teacher creates attendance session
2. Teacher captures class photos
3. System recognizes faces and suggests students
4. Teacher confirms and marks attendance

### 3. Viewing Reports
- Teachers can view all attendance records
- Students can view their own attendance
- Export functionality available via API

## Security Considerations

1. **JWT Tokens**: Use strong secret keys, implement token refresh
2. **Password Security**: Passwords are hashed with bcrypt
3. **Database Security**: Use strong PostgreSQL passwords
4. **Face Data**: Store only encodings, not actual images
5. **API Security**: Implement rate limiting in production

## Performance Optimization

1. **Database Indexing**: Already implemented for common queries
2. **Vector Search**: Use appropriate similarity thresholds
3. **Image Processing**: Resize images before processing
4. **Caching**: Consider Redis for session caching

## Production Deployment

1. **Environment**: Set `FLASK_ENV=production`
2. **Web Server**: Use Gunicorn + Nginx
3. **Database**: Use connection pooling
4. **Storage**: Consider cloud storage for vector data
5. **Monitoring**: Implement logging and monitoring

## Support

For issues or questions:
1. Check this documentation
2. Review error logs
3. Test with smaller datasets first
4. Verify environment configuration

## Version Information
- Flask: 2.3.3
- PostgreSQL: 12+
- Python: 3.8+
- Vector DB: ChromaDB 0.4.24 / FAISS 1.7.4