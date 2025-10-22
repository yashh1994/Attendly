"""
ArcFace Upgrade Migration Script
Migrates existing face encodings from 128D (face_recognition) to 512D (ArcFace)

IMPORTANT: This is a ONE-TIME migration. Students will need to re-register their facial data
to benefit from the improved 512D embeddings.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

def get_database_connection():
    """Get database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return engine, Session()

def check_arcface_availability():
    """Check if ArcFace is installed and working"""
    try:
        from services.arcface_service import initialize_arcface, get_model_info
        
        logger.info("Initializing ArcFace model...")
        initialize_arcface()
        
        info = get_model_info()
        if info['status'] == 'loaded':
            logger.info(f"✅ ArcFace loaded: {info['model_name']}, {info['embedding_dimension']}D")
            return True
        else:
            logger.error("❌ ArcFace failed to load")
            return False
            
    except ImportError as e:
        logger.error(f"❌ ArcFace not available: {e}")
        logger.error("   Please install: pip install insightface onnxruntime")
        return False

def migrate_encoding_versions(session):
    """
    Update encoding_version field for all existing face data
    Mark them as legacy to differentiate from new ArcFace encodings
    """
    try:
        logger.info("Updating encoding versions for existing face data...")
        
        # Update all existing records to mark as legacy
        result = session.execute(
            text("""
                UPDATE face_data 
                SET encoding_version = 'v1.0_legacy_128d'
                WHERE encoding_version = 'v1.0' 
                   OR encoding_version LIKE 'v2%'
                   OR encoding_version LIKE 'v3%'
            """)
        )
        
        session.commit()
        
        logger.info(f"✅ Updated {result.rowcount} face_data records to legacy version")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate encoding versions: {e}")
        session.rollback()
        return False

def get_migration_stats(session):
    """Get statistics about current face data"""
    try:
        # Count total face data records
        result = session.execute(text("SELECT COUNT(*) FROM face_data WHERE is_active = TRUE"))
        total_count = result.scalar()
        
        # Count by encoding version
        result = session.execute(
            text("""
                SELECT encoding_version, COUNT(*) as count 
                FROM face_data 
                WHERE is_active = TRUE 
                GROUP BY encoding_version
            """)
        )
        
        version_counts = {row[0]: row[1] for row in result}
        
        return {
            'total_active': total_count,
            'by_version': version_counts
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return None

def main():
    """Main migration process"""
    logger.info("=" * 80)
    logger.info("ARCFACE 512D UPGRADE MIGRATION")
    logger.info("=" * 80)
    
    # Step 1: Check ArcFace availability
    logger.info("\n📦 Step 1: Checking ArcFace availability...")
    if not check_arcface_availability():
        logger.error("\n❌ Migration aborted: ArcFace not available")
        logger.info("\nTo install ArcFace:")
        logger.info("   pip install -r requirements.txt")
        return False
    
    # Step 2: Connect to database
    logger.info("\n🔌 Step 2: Connecting to database...")
    try:
        engine, session = get_database_connection()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    
    # Step 3: Get current statistics
    logger.info("\n📊 Step 3: Getting current statistics...")
    stats_before = get_migration_stats(session)
    if stats_before:
        logger.info(f"   Total active face data: {stats_before['total_active']}")
        logger.info(f"   By version: {stats_before['by_version']}")
    
    # Step 4: Migrate encoding versions
    logger.info("\n🔄 Step 4: Migrating encoding versions...")
    if not migrate_encoding_versions(session):
        logger.error("❌ Migration failed")
        return False
    
    # Step 5: Get final statistics
    logger.info("\n📊 Step 5: Final statistics...")
    stats_after = get_migration_stats(session)
    if stats_after:
        logger.info(f"   Total active face data: {stats_after['total_active']}")
        logger.info(f"   By version: {stats_after['by_version']}")
    
    # Step 6: Summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info("\n📝 NEXT STEPS:")
    logger.info("   1. Existing face data is marked as 'v1.0_legacy_128d'")
    logger.info("   2. Students should re-register facial data for ArcFace 512D")
    logger.info("   3. New registrations will use 'v4.0_arcface_512d'")
    logger.info("   4. System will continue to work with both old and new encodings")
    logger.info("\n⚠️  IMPORTANT:")
    logger.info("   - Legacy 128D encodings will still work but with lower accuracy")
    logger.info("   - Recommend all students re-register for best recognition")
    logger.info("   - Vector database will handle both 128D and 512D embeddings")
    logger.info("\n🚀 ArcFace 512D is now active for all new registrations!")
    
    session.close()
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
