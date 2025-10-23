"""
Reset ChromaDB collection to use 512D ArcFace embeddings
Run this script to migrate from legacy 128D to ArcFace 512D
"""

import os
import shutil
import chromadb
from chromadb.config import Settings

def reset_chroma_to_512d():
    """Delete and recreate ChromaDB collection for 512D ArcFace embeddings"""
    
    persist_dir = os.getenv('CHROMA_PERSIST_DIRECTORY', './vector_db/chroma')
    
    print(f"🗑️  Resetting ChromaDB at: {persist_dir}")
    
    # Backup existing database
    if os.path.exists(persist_dir):
        backup_dir = persist_dir + '_backup_128d'
        if os.path.exists(backup_dir):
            print(f"⚠️  Removing old backup: {backup_dir}")
            shutil.rmtree(backup_dir)
        
        print(f"📦 Creating backup at: {backup_dir}")
        shutil.copytree(persist_dir, backup_dir)
        
        # Delete the original
        print(f"🗑️  Deleting original ChromaDB")
        shutil.rmtree(persist_dir)
    
    # Create new ChromaDB client
    print(f"✨ Creating new ChromaDB for 512D ArcFace embeddings")
    os.makedirs(persist_dir, exist_ok=True)
    
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # Create collection for 512D ArcFace encodings
    try:
        collection = client.get_or_create_collection(
            name="face_encodings",
            metadata={
                "description": "Face recognition encodings using ArcFace",
                "encoding_dimension": 512,
                "model_type": "arcface_buffalo_l",
                "distance_function": "cosine"
            }
        )
        print(f"✅ Collection created: {collection.name}")
        print(f"   Dimension: 512D (ArcFace)")
        print(f"   Model: buffalo_l")
        print(f"   Count: {collection.count()} encodings")
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return False
    
    print("\n✅ ChromaDB reset complete!")
    print("\n⚠️  Important:")
    print("   - All students need to re-register their facial data with ArcFace")
    print("   - The 128D backup is saved at:", backup_dir if os.path.exists(persist_dir + '_backup_128d') else "N/A")
    print("   - Restart your Flask server to pick up the new database")
    print("   - ArcFace 512D provides superior accuracy compared to 128D!")
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("ChromaDB ArcFace 512D Migration Tool")
    print("=" * 60)
    print("\nThis will:")
    print("1. Backup existing ChromaDB (if any)")
    print("2. Delete the current database")
    print("3. Create new ChromaDB for 512D ArcFace embeddings")
    print("\n⚠️  All students will need to re-register their faces!")
    print("✅  ArcFace 512D provides much better accuracy!")
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response == 'yes':
        reset_chroma_to_512d()
    else:
        print("❌ Operation cancelled")
