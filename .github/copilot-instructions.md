# Attendly - AI-Powered Attendance System

## Architecture Overview

Attendly is a **dual-architecture** system: Flask backend with ArcFace ML + Flutter mobile frontend. The system uses **512-dimensional ArcFace embeddings** for facial recognition (upgraded from 128D face_recognition library).

**Core Components:**
- **Backend** (`Backend/`): Flask REST API with JWT auth, PostgreSQL/SQLite, ArcFace ML service
- **Frontend** (`Frontend/attendly/`): Flutter mobile app with Provider state management  
- **ML Pipeline**: ArcFace (InsightFace) → Vector DB (ChromaDB/FAISS) → Similarity matching

## Key Development Patterns

### Backend Flask Architecture
- **App Factory Pattern**: `app.py` creates Flask app with extension initialization
- **Blueprint Organization**: Routes split by domain (`auth.py`, `classes.py`, `face_data.py`, `attendance.py`)
- **Service Layer**: AI/ML logic isolated in `services/` (ArcFace, vector DB)
- **Model Layer**: SQLAlchemy models with optimized relationships and indexing

### Face Recognition System
```python
# ArcFace service pattern - services/arcface_service.py
def extract_arcface_embedding(image_data) -> np.ndarray:
    # Returns 512D embedding using InsightFace buffalo_l model
```
- **Version Migration**: System supports both legacy 128D and new 512D encodings
- **Fallback Strategy**: Graceful degradation to face_recognition if ArcFace unavailable
- **Encoding Versioning**: `v4.0_arcface_512d` vs `v1.0_legacy_128d` tracked in DB

### Database Patterns
- **Computed Fields**: `full_name` field for search optimization
- **Soft Deletes**: `is_active` flags instead of hard deletes
- **Cached Counts**: `student_count` field to avoid expensive JOINs
- **Index Strategy**: Heavy indexing on search fields (`email`, `role`, `join_code`)

## Critical Workflows

### Development Setup
```bash
# Backend
cd Backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py

# Frontend  
cd Frontend/attendly
flutter pub get
flutter run
```

### Face Data Upload Flow
1. **Flutter**: Camera capture → Base64 encoding → API call
2. **Backend**: ArcFace embedding extraction → Vector DB storage
3. **Recognition**: Image → Embedding → Cosine similarity search

### Database Migration for ArcFace
- Run `migrate_to_arcface.py` to upgrade existing 128D → 512D encodings
- System maintains backward compatibility during transition

## Project-Specific Conventions

### API Response Format
```python
# Standard success response
return jsonify({
    'success': True,
    'message': 'Operation completed',
    'data': result
}), 200

# Standard error response  
return jsonify({
    'success': False,
    'message': 'Error description',
    'error': 'ERROR_CODE'
}), 400
```

### Flutter State Management
- **Provider Pattern**: AuthProvider for user state, ThemeProvider for UI
- **API Service**: Centralized HTTP client in `services/api_service.dart`
- **Route Management**: Named routes defined in `utils/routes.dart`

### Authentication Flow
- **JWT Tokens**: No expiration (`JWT_ACCESS_TOKEN_EXPIRES = False`)
- **Role-based Access**: Teacher vs Student permissions in routes
- **Persistent Login**: SharedPreferences stores auth state

## Integration Points

### External Dependencies
- **InsightFace**: ArcFace model (buffalo_l) for 512D embeddings
- **ChromaDB/FAISS**: Vector databases for similarity search
- **PostgreSQL/SQLite**: Primary data storage (configurable via DATABASE_URL)
- **OpenCV/PIL**: Image processing pipeline

### API Endpoints Structure
```
/api/auth/*          - Authentication (signup, login, profile)
/api/classes/*       - Class management (create, join, update)  
/api/face-data/*     - Face data upload/management
/api/attendance/*    - Attendance sessions and marking
```

### Mobile-Backend Communication
- **Base URL**: `http://10.0.2.2:5000` (Android emulator)
- **Image Format**: Base64 strings for face data transmission
- **Error Handling**: Standardized error codes with user-friendly messages

## File Location Reference

**Key Backend Files:**
- `app.py` - Flask app factory and configuration
- `models/models.py` - SQLAlchemy database models
- `services/arcface_service.py` - 512D face recognition service
- `services/vector_db.py` - ChromaDB/FAISS abstraction layer
- `routes/face_data.py` - Face upload and recognition endpoints

**Key Frontend Files:**
- `lib/main.dart` - App initialization with Provider setup
- `lib/providers/auth_provider.dart` - Authentication state management
- `lib/services/api_service.dart` - HTTP client and API abstraction
- `lib/screens/*/` - Feature-based screen organization

**Migration/Setup Scripts:**
- `migrate_to_arcface.py` - Upgrade 128D→512D encodings
- `reset_to_arcface_512d.py` - Fresh setup with ArcFace
- `test_face_recognition.py` - Validation script for ML pipeline