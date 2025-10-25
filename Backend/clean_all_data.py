"""
Clean All Data - Complete database and vector storage reset
NO BACKUP - Use with caution!
"""

import os
import shutil
import chromadb
from chromadb.config import Settings

def clean_all_data():
    """
    Complete clean of all facial data - NO BACKUP
    """
    print("=" * 60)
    print("⚠️  COMPLETE DATA WIPE - NO BACKUP")
    print("=" * 60)
    print("\nThis will permanently delete:")
    print("1. All ChromaDB vector embeddings")
    print("2. All uploaded face images")
    print("3. PostgreSQL FaceData table records")
    print("\n⚠️  THIS CANNOT BE UNDONE!")
    
    response = input("\nType 'DELETE EVERYTHING' to proceed: ").strip()
    
    if response != 'DELETE EVERYTHING':
        print("❌ Operation cancelled")
        return False
    
    print("\n🗑️  Starting complete data wipe...\n")
    
    # 1. Delete ChromaDB
    persist_dir = os.getenv('CHROMA_PERSIST_DIRECTORY', './vector_db/chroma')
    if os.path.exists(persist_dir):
        print(f"🗑️  Deleting ChromaDB: {persist_dir}")
        shutil.rmtree(persist_dir)
        print("   ✅ ChromaDB deleted")
    
    # 2. Delete uploaded face images
    uploads_dir = './uploads/face_images'
    if os.path.exists(uploads_dir):
        print(f"🗑️  Deleting face images: {uploads_dir}")
        shutil.rmtree(uploads_dir)
        os.makedirs(uploads_dir, exist_ok=True)
        print("   ✅ Face images deleted")
    
    # 3. Create fresh ChromaDB for 512D
    print(f"✨ Creating fresh ChromaDB for 512D ArcFace embeddings")
    os.makedirs(persist_dir, exist_ok=True)
    
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    collection = client.get_or_create_collection(
        name="face_encodings",
        metadata={
            "description": "Face recognition encodings using ArcFace 512D",
            "encoding_dimension": 512,
            "model_type": "arcface_buffalo_l",
            "distance_function": "cosine"
        }
    )
    
    print(f"   ✅ New ChromaDB collection created")
    print(f"   Collection: {collection.name}")
    print(f"   Dimension: 512D (ArcFace)")
    print(f"   Encodings: {collection.count()}")
    
    # 4. Clear PostgreSQL FaceData table
    print(f"\n🗑️  Clearing PostgreSQL FaceData table...")
    try:
        from app import create_app
        from models.models import db, FaceData
        
        app = create_app()
        with app.app_context():
            deleted_count = FaceData.query.delete()
            db.session.commit()
            print(f"   ✅ Deleted {deleted_count} FaceData records")
    except Exception as e:
        print(f"   ⚠️  Could not clear FaceData table: {e}")
        print(f"   You may need to manually delete FaceData records")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE DATA WIPE FINISHED")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("1. Restart your Flask server")
    print("2. All students must re-register their faces")
    print("3. System will now use ArcFace 512D embeddings")
    print("4. Expect ~99% recognition accuracy")
    
    return True

if __name__ == '__main__':
    clean_all_data()
