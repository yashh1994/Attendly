"""
Test Face Recognition System
Verifies the entire face recognition pipeline
"""

from app import create_app
from models.models import FaceData, User, Class, ClassEnrollment
from services.vector_db import get_vector_db_service
from services.arcface_service import extract_arcface_embedding
import numpy as np

def test_face_recognition():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Face Recognition System Test")
        print("=" * 60)
        
        # 1. Check stored facial data
        print("\n1. Checking stored facial data...")
        face_data = FaceData.query.filter_by(is_active=True).all()
        print(f"   Total active FaceData records: {len(face_data)}")
        
        for fd in face_data:
            user = User.query.get(fd.user_id)
            print(f"   - User: {user.first_name} {user.last_name} (ID: {user.id})")
            print(f"     Vector ID: {fd.vector_db_id}")
            print(f"     Encoding Version: {fd.encoding_version}")
            
            # Check metadata
            if fd.encoding_metadata:
                dim = fd.encoding_metadata.get('embedding_dimension', 'Unknown')
                print(f"     Embedding Dimension: {dim}")
        
        # 2. Check Vector DB
        print("\n2. Checking Vector DB...")
        vdb = get_vector_db_service()
        stats = vdb.get_stats()
        print(f"   DB Type: {stats['db_type']}")
        print(f"   Total Encodings: {stats['total_encodings']}")
        print(f"   Dimension: {stats['encoding_dimension']}D")
        
        # 3. Test retrieval of embeddings
        print("\n3. Testing embedding retrieval...")
        for fd in face_data:
            result = vdb.get_face_encoding(fd.user_id)
            if result:
                encoding = result['encoding']
                print(f"   User {fd.user_id}:")
                print(f"     Retrieved encoding shape: {encoding.shape}")
                print(f"     Encoding norm: {np.linalg.norm(encoding):.4f}")
                print(f"     First 5 values: {encoding[:5]}")
            else:
                print(f"   User {fd.user_id}: ❌ Could not retrieve encoding")
        
        # 4. Test similarity search with stored embedding
        print("\n4. Testing similarity search...")
        if face_data:
            test_user_id = face_data[0].user_id
            result = vdb.get_face_encoding(test_user_id)
            
            if result:
                test_encoding = result['encoding']
                print(f"   Using User {test_user_id}'s encoding for test search...")
                
                # Search for similar faces
                matches = vdb.find_similar_faces(
                    encoding=test_encoding,
                    top_k=5,
                    threshold=0.5
                )
                
                print(f"   Found {len(matches)} matches:")
                for match in matches:
                    print(f"     - User {match['user_id']}: Similarity {match['similarity']:.4f}")
                
                if matches and matches[0]['user_id'] == test_user_id:
                    print(f"   ✅ Self-match successful with {matches[0]['similarity']:.4f} similarity")
                else:
                    print(f"   ❌ Self-match failed!")
        
        # 5. Check class enrollments
        print("\n5. Checking class enrollments...")
        enrollments = ClassEnrollment.query.filter_by(is_active=True).all()
        print(f"   Total active enrollments: {len(enrollments)}")
        
        for enroll in enrollments:
            student = User.query.get(enroll.student_id)
            class_obj = Class.query.get(enroll.class_id)
            has_face = FaceData.query.filter_by(
                user_id=enroll.student_id, 
                is_active=True
            ).first() is not None
            
            print(f"   - {student.first_name} {student.last_name} in {class_obj.name}")
            print(f"     Has facial data: {'✅' if has_face else '❌'}")
        
        print("\n" + "=" * 60)
        print("Test Complete")
        print("=" * 60)

if __name__ == '__main__':
    test_face_recognition()
