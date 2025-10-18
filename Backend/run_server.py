#!/usr/bin/env python3
"""
Simple startup script for the Attendly Flask backend
Uses the main app.py with proper SQLAlchemy initialization
"""

from app import create_app, db
import os

# Create the Flask app
app = create_app()

# Import models to ensure tables are created
with app.app_context():
    # Import all models so they are registered with SQLAlchemy
    from models.models import User, Class, FaceData, AttendanceSession, AttendanceRecord, ClassEnrollment
    
    # Create database tables
    db.create_all()
    print('✅ Database tables created successfully')

if __name__ == '__main__':
    print('🚀 Starting Attendly Backend Server...')
    print('=' * 50)
    
    # Print registered routes
    print('📋 Registered routes:')
    with app.app_context():
        for rule in app.url_map.iter_rules():
            print(f'  {rule.methods} {rule.rule}')
    
    print('=' * 50)
    print('🌐 Server starting on http://localhost:5000')
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)