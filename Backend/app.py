from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Database Configuration
    database_url = os.getenv('DATABASE_URL', 'sqlite:///attendly.db')
    
    # PostgreSQL specific configurations
    if database_url.startswith('postgresql://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 120,
            'pool_pre_ping': True,
            'max_overflow': 20
        }
        print("🐘 Using PostgreSQL database")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print("📁 Using SQLite database")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-string')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
    
    # File upload configurations
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Initialize vector database
    try:
        from services.vector_db import get_vector_db_service
        vector_db = get_vector_db_service()
        app.vector_db = vector_db
        print(f"🔍 Vector database initialized: {vector_db.db_type}")
        
        # Get stats
        stats = vector_db.get_stats()
        print(f"📊 Vector DB stats: {stats}")
        
    except Exception as e:
        print(f"⚠️  Warning: Vector database initialization failed: {e}")
        print("   Face recognition will use fallback method")
        app.vector_db = None
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.classes import classes_bp
    from routes.face_data import face_data_bp
    from routes.attendance import attendance_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(classes_bp, url_prefix='/api/classes')
    app.register_blueprint(face_data_bp, url_prefix='/api/face-data')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    
    # Debug: Print all registered routes
    print("🔥 REGISTERED ROUTES:")
    for rule in app.url_map.iter_rules():
        print(f"🔥 {rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Check database connection
            db.session.execute('SELECT 1')
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Check vector database
        vector_db_status = "not_initialized"
        if hasattr(app, 'vector_db') and app.vector_db:
            try:
                stats = app.vector_db.get_stats()
                vector_db_status = f"connected ({stats['db_type']})"
            except Exception as e:
                vector_db_status = f"error: {str(e)}"
        
        return {
            'status': 'healthy',
            'database': db_status,
            'vector_database': vector_db_status,
            'face_recognition': 'available'
        }
    
    # Create upload directories
    upload_dirs = ['uploads', 'uploads/face_images', 'vector_db']
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            if 'postgresql' in str(e).lower():
                print("💡 Make sure PostgreSQL is running and database exists")
                print("   Create database with: CREATE DATABASE attendly_db;")
    
    return app

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        ('flask', 'Flask'),
        ('face_recognition', 'face_recognition'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('PIL', 'Pillow')
    ]
    
    missing_packages = []
    
    for package, pip_name in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print("   pip install " + " ".join(missing_packages))
        return False
    
    return True

if __name__ == '__main__':
    print("🚀 Starting Attendly Backend Server...")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Cannot start server due to missing dependencies")
        sys.exit(1)
    
    # Create and run app
    app = create_app()
    
    print("=" * 50)
    print("🎉 Server is ready!")
    print("📍 API Base URL: http://localhost:5000/api")
    print("🏥 Health Check: http://localhost:5000/health")
    print("📚 Documentation: See README.md")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)