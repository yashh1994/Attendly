from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string
import json

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.Enum('teacher', 'student', name='user_roles'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Additional fields for PostgreSQL optimization
    full_name = db.Column(db.String(160), nullable=True, index=True)  # Computed field for search
    
    # Relationships
    created_classes = db.relationship('Class', backref='teacher', lazy=True, foreign_keys='Class.teacher_id')
    enrollments = db.relationship('ClassEnrollment', backref='student', lazy=True)
    face_data = db.relationship('FaceData', backref='user', lazy=True)
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, foreign_keys='AttendanceRecord.student_id')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self._update_full_name()
    
    def _update_full_name(self):
        """Update computed full name field"""
        if self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }

class Class(db.Model):
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    join_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Additional PostgreSQL optimizations
    student_count = db.Column(db.Integer, default=0)  # Cached count for performance
    
    # Relationships
    enrollments = db.relationship('ClassEnrollment', backref='class_ref', lazy=True, 
                                cascade='all, delete-orphan')
    attendance_sessions = db.relationship('AttendanceSession', backref='class_ref', lazy=True,
                                        cascade='all, delete-orphan')
    
    def generate_join_code(self):
        """Generate a unique 6-character alphanumeric join code"""
        max_attempts = 10
        for _ in range(max_attempts):
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if not Class.query.filter_by(join_code=code).first():
                self.join_code = code
                return
        raise ValueError("Could not generate unique join code after multiple attempts")
    
    def update_student_count(self):
        """Update cached student count"""
        self.student_count = ClassEnrollment.query.filter_by(
            class_id=self.id, 
            is_active=True
        ).count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'join_code': self.join_code,
            'teacher_id': self.teacher_id,
            'teacher_name': f"{self.teacher.first_name} {self.teacher.last_name}",
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'student_count': self.student_count or len(self.enrollments)
        }

class ClassEnrollment(db.Model):
    __tablename__ = 'class_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (
        db.UniqueConstraint('student_id', 'class_id', name='unique_student_class'),
        db.Index('idx_class_enrollment_active', 'class_id', 'is_active'),
        db.Index('idx_student_enrollment_active', 'student_id', 'is_active')
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'class_id': self.class_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}",
            'class_name': self.class_ref.name,
            'enrolled_at': self.enrolled_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }

class FaceData(db.Model):
    __tablename__ = 'face_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True, unique=True)
    # Store vector DB reference instead of actual encoding
    vector_db_id = db.Column(db.String(100), nullable=True, index=True)
    encoding_metadata = db.Column(db.JSON, nullable=True)  # Store metadata as JSON
    image_path = db.Column(db.String(255), nullable=True)  # DEPRECATED: Not used, embeddings stored in vector DB only
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Additional fields for PostgreSQL
    encoding_version = db.Column(db.String(50), default='v1.0')  # Track encoding version (increased to 50)
    confidence_score = db.Column(db.Float, nullable=True)  # Store confidence if available
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}",
            'vector_db_id': self.vector_db_id,
            'encoding_metadata': self.encoding_metadata,
            'encoding_version': self.encoding_version,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }

class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    session_name = db.Column(db.String(200), nullable=False)
    session_date = db.Column(db.Date, nullable=False, index=True, default=datetime.utcnow().date())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Additional fields for enhanced functionality
    total_students = db.Column(db.Integer, default=0)  # Cached total enrolled students
    present_count = db.Column(db.Integer, default=0)   # Cached present count
    absent_count = db.Column(db.Integer, default=0)    # Cached absent count
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy=True,
                                       cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_class_session_date', 'class_id', 'session_date'),
        db.Index('idx_session_active', 'is_active', 'session_date')
    )
    
    def update_attendance_counts(self):
        """Update cached attendance counts"""
        from sqlalchemy import func
        
        # Get attendance counts
        counts = db.session.query(
            AttendanceRecord.status,
            func.count(AttendanceRecord.id)
        ).filter_by(session_id=self.id).group_by(AttendanceRecord.status).all()
        
        self.present_count = 0
        self.absent_count = 0
        
        for status, count in counts:
            if status == 'present':
                self.present_count = count
            elif status == 'absent':
                self.absent_count = count
        
        # Get total enrolled students
        self.total_students = ClassEnrollment.query.filter_by(
            class_id=self.class_id,
            is_active=True
        ).count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'class_name': self.class_ref.name,
            'session_name': self.session_name,
            'session_date': self.session_date.isoformat(),
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}",
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'total_students': self.total_students,
            'present_count': self.present_count,
            'absent_count': self.absent_count,
            'attendance_count': len(self.attendance_records)
        }

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.Enum('present', 'absent', 'late', name='attendance_status'), 
                      nullable=False, default='present', index=True)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields for AI recognition
    recognition_confidence = db.Column(db.Float, nullable=True)  # AI confidence score
    recognition_method = db.Column(db.Enum('manual', 'ai_face', 'hybrid', name='recognition_methods'), 
                                  default='manual')
    
    # Relationships
    marker = db.relationship('User', foreign_keys=[marked_by])
    
    # Unique constraint to prevent duplicate attendance records
    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='unique_session_student'),
        db.Index('idx_session_status', 'session_id', 'status'),
        db.Index('idx_student_attendance', 'student_id', 'marked_at')
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'student_id': self.student_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}",
            'status': self.status,
            'marked_at': self.marked_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'marked_by': self.marked_by,
            'marker_name': f"{self.marker.first_name} {self.marker.last_name}",
            'recognition_confidence': self.recognition_confidence,
            'recognition_method': self.recognition_method
        }