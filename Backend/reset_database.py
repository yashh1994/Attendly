"""
Database Reset Script
This script will completely reset the database by:
1. Dropping all existing tables
2. Recreating the database schema
3. Clearing the ChromaDB vector database
4. Optionally creating sample test data

WARNING: This will DELETE ALL DATA in the database!
"""

import os
import sys
from flask import Flask
from models.models import db, User, Class, ClassEnrollment, FaceData, AttendanceSession, AttendanceRecord
from services.vector_db import get_vector_db_service
from dotenv import load_dotenv
import shutil

# Load environment variables
load_dotenv()

def reset_database(create_sample_data=False):
    """Reset the database to a clean state"""
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:12345678@localhost:5432/attendly')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        print("=" * 60)
        print("DATABASE RESET SCRIPT")
        print("=" * 60)
        print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
        print("This includes:")
        print("  - All users (teachers and students)")
        print("  - All classes and enrollments")
        print("  - All facial data")
        print("  - All attendance records")
        print("  - All vector database embeddings")
        print("\n" + "=" * 60)
        
        # Get confirmation
        confirm = input("\nType 'YES' to proceed with database reset: ")
        if confirm != 'YES':
            print("❌ Database reset cancelled.")
            return
        
        print("\n🔄 Starting database reset...\n")
        
        # Step 1: Drop all tables
        print("1️⃣  Dropping all tables...")
        try:
            db.drop_all()
            print("   ✅ All tables dropped successfully")
        except Exception as e:
            print(f"   ⚠️  Error dropping tables: {e}")
        
        # Step 2: Recreate all tables
        print("\n2️⃣  Creating fresh database schema...")
        try:
            db.create_all()
            print("   ✅ Database schema created successfully")
        except Exception as e:
            print(f"   ❌ Error creating schema: {e}")
            return
        
        # Step 3: Clear ChromaDB vector database
        print("\n3️⃣  Clearing vector database...")
        try:
            # Delete the ChromaDB directory
            chroma_path = os.path.join(os.path.dirname(__file__), 'vector_db', 'chroma')
            if os.path.exists(chroma_path):
                shutil.rmtree(chroma_path)
                print(f"   ✅ ChromaDB directory deleted: {chroma_path}")
            
            # Recreate the collection
            vector_db = get_vector_db_service()
            print("   ✅ Vector database collection recreated")
        except Exception as e:
            print(f"   ⚠️  Error clearing vector database: {e}")
        
        # Step 4: Create sample data (optional)
        if create_sample_data:
            print("\n4️⃣  Creating sample test data...")
            try:
                create_test_data()
                print("   ✅ Sample data created successfully")
            except Exception as e:
                print(f"   ❌ Error creating sample data: {e}")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 60)
        print("\nThe database is now empty and ready for fresh data.")
        if create_sample_data:
            print("\n📋 Sample data created:")
            print("   - 1 Teacher: yash@gmail.com / 12345678")
            print("   - 3 Students: student1@test.com / password123")
            print("                 student2@test.com / password123")
            print("                 student3@test.com / password123")
            print("   - 1 Class: Test Class 101")
        print("\n")


def create_test_data():
    """Create sample test data for testing"""
    from werkzeug.security import generate_password_hash
    import random
    import string
    
    # Create teacher
    teacher = User(
        first_name='Yash',
        last_name='Teacher',
        email='yash@gmail.com',
        password_hash=generate_password_hash('12345678'),
        role='teacher'
    )
    db.session.add(teacher)
    db.session.flush()  # Get teacher ID
    
    # Create students
    students = []
    for i in range(1, 4):
        student = User(
            first_name=f'Student',
            last_name=f'{i}',
            email=f'student{i}@test.com',
            password_hash=generate_password_hash('password123'),
            role='student'
        )
        db.session.add(student)
        students.append(student)
    
    db.session.flush()  # Get student IDs
    
    # Create a class
    join_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    test_class = Class(
        name='Test Class 101',
        description='Sample class for testing attendance',
        teacher_id=teacher.id,
        join_code=join_code
    )
    db.session.add(test_class)
    db.session.flush()  # Get class ID
    
    # Enroll students in class
    for student in students:
        enrollment = ClassEnrollment(
            user_id=student.id,
            class_id=test_class.id
        )
        db.session.add(enrollment)
    
    db.session.commit()
    
    print(f"\n   👨‍🏫 Teacher created: {teacher.email}")
    print(f"   👨‍🎓 Students created: {len(students)}")
    print(f"   📚 Class created: {test_class.name} (Code: {join_code})")
    print(f"   ✅ All students enrolled in class")


def reset_with_confirmation():
    """Reset database with user choice for sample data"""
    print("\n" + "=" * 60)
    print("Database Reset Options:")
    print("=" * 60)
    print("1. Reset database only (empty)")
    print("2. Reset database + create sample test data")
    print("3. Cancel")
    print("=" * 60)
    
    choice = input("\nEnter your choice (1, 2, or 3): ").strip()
    
    if choice == '1':
        reset_database(create_sample_data=False)
    elif choice == '2':
        reset_database(create_sample_data=True)
    elif choice == '3':
        print("\n❌ Database reset cancelled.")
    else:
        print("\n❌ Invalid choice. Database reset cancelled.")


if __name__ == '__main__':
    reset_with_confirmation()
