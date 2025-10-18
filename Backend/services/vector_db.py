"""
Vector Database Service for Face Encodings
Supports both ChromaDB and FAISS for storing and querying face encodings
"""

import os
import numpy as np
import json
import pickle
from typing import List, Dict, Optional, Tuple
import uuid
from abc import ABC, abstractmethod

class VectorDBInterface(ABC):
    """Abstract interface for vector database operations"""
    
    @abstractmethod
    def add_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> str:
        """Add face encoding to vector database"""
        pass
    
    @abstractmethod
    def search_similar(self, encoding: np.ndarray, top_k: int = 10, threshold: float = 0.6) -> List[Dict]:
        """Search for similar face encodings"""
        pass
    
    @abstractmethod
    def update_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> bool:
        """Update existing face encoding"""
        pass
    
    @abstractmethod
    def delete_encoding(self, user_id: int) -> bool:
        """Delete face encoding"""
        pass
    
    @abstractmethod
    def get_encoding(self, user_id: int) -> Optional[Dict]:
        """Get face encoding by user ID"""
        pass

class ChromaVectorDB(VectorDBInterface):
    """ChromaDB implementation for vector storage"""
    
    def __init__(self, persist_directory: str = "./vector_db/chroma"):
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.persist_directory = persist_directory
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection for face encodings
            self.collection = self.client.get_or_create_collection(
                name="face_encodings",
                metadata={"description": "Student face encodings for attendance"}
            )
            
        except ImportError:
            raise ImportError("ChromaDB not installed. Install with: pip install chromadb")
    
    def add_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> str:
        """Add face encoding to ChromaDB"""
        try:
            doc_id = f"user_{user_id}"
            
            # Convert numpy array to list for storage
            encoding_list = encoding.tolist()
            
            # Prepare metadata
            meta = {
                "user_id": user_id,
                "encoding_dimension": len(encoding),
                "created_at": str(np.datetime64('now')),
                **(metadata or {})
            }
            
            # Add to collection
            self.collection.add(
                embeddings=[encoding_list],
                documents=[json.dumps(meta)],
                metadatas=[meta],
                ids=[doc_id]
            )
            
            return doc_id
            
        except Exception as e:
            raise ValueError(f"Failed to add encoding to ChromaDB: {str(e)}")
    
    def search_similar(self, encoding: np.ndarray, top_k: int = 10, threshold: float = 0.6) -> List[Dict]:
        """Search for similar face encodings in ChromaDB"""
        try:
            # Convert threshold to distance (ChromaDB uses cosine distance)
            # Lower distance = higher similarity
            max_distance = 1 - threshold
            
            results = self.collection.query(
                query_embeddings=[encoding.tolist()],
                n_results=top_k,
                include=["metadatas", "distances", "embeddings"]
            )
            
            matches = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # Convert distance back to similarity
                    
                    if similarity >= threshold:
                        metadata = results['metadatas'][0][i]
                        matches.append({
                            'user_id': metadata['user_id'],
                            'similarity': similarity,
                            'distance': distance,
                            'metadata': metadata
                        })
            
            return sorted(matches, key=lambda x: x['similarity'], reverse=True)
            
        except Exception as e:
            raise ValueError(f"Failed to search in ChromaDB: {str(e)}")
    
    def update_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> bool:
        """Update existing face encoding in ChromaDB"""
        try:
            doc_id = f"user_{user_id}"
            
            # Check if encoding exists
            existing = self.collection.get(ids=[doc_id])
            if not existing['ids']:
                return False
            
            # Update encoding
            encoding_list = encoding.tolist()
            meta = {
                "user_id": user_id,
                "encoding_dimension": len(encoding),
                "updated_at": str(np.datetime64('now')),
                **(metadata or {})
            }
            
            self.collection.update(
                ids=[doc_id],
                embeddings=[encoding_list],
                documents=[json.dumps(meta)],
                metadatas=[meta]
            )
            
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to update encoding in ChromaDB: {str(e)}")
    
    def delete_encoding(self, user_id: int) -> bool:
        """Delete face encoding from ChromaDB"""
        try:
            doc_id = f"user_{user_id}"
            
            # Check if exists
            existing = self.collection.get(ids=[doc_id])
            if not existing['ids']:
                return False
            
            self.collection.delete(ids=[doc_id])
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to delete encoding from ChromaDB: {str(e)}")
    
    def get_encoding(self, user_id: int) -> Optional[Dict]:
        """Get face encoding by user ID from ChromaDB"""
        try:
            doc_id = f"user_{user_id}"
            
            result = self.collection.get(
                ids=[doc_id],
                include=["metadatas", "embeddings"]
            )
            
            if result['ids']:
                return {
                    'user_id': user_id,
                    'encoding': np.array(result['embeddings'][0]),
                    'metadata': result['metadatas'][0]
                }
            
            return None
            
        except Exception as e:
            raise ValueError(f"Failed to get encoding from ChromaDB: {str(e)}")

class FAISSVectorDB(VectorDBInterface):
    """FAISS implementation for vector storage"""
    
    def __init__(self, index_path: str = "./vector_db/faiss_index.pkl"):
        try:
            import faiss
            
            self.index_path = index_path
            self.metadata_path = index_path.replace('.pkl', '_metadata.json')
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # Load or create index
            self.dimension = 128  # Face encoding dimension
            self.index = None
            self.metadata = {}
            self.user_id_to_index = {}
            
            self._load_index()
            
        except ImportError:
            raise ImportError("FAISS not installed. Install with: pip install faiss-cpu")
    
    def _load_index(self):
        """Load FAISS index and metadata from disk"""
        try:
            import faiss
            
            if os.path.exists(self.index_path):
                with open(self.index_path, 'rb') as f:
                    data = pickle.load(f)
                    self.index = data['index']
                    self.user_id_to_index = data['user_id_to_index']
            else:
                # Create new index
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product for cosine similarity
                
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                    
        except Exception as e:
            print(f"Warning: Could not load FAISS index: {e}")
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = {}
            self.user_id_to_index = {}
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            # Save index
            with open(self.index_path, 'wb') as f:
                pickle.dump({
                    'index': self.index,
                    'user_id_to_index': self.user_id_to_index
                }, f)
            
            # Save metadata
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save FAISS index: {e}")
    
    def add_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> str:
        """Add face encoding to FAISS index"""
        try:
            # Normalize encoding for cosine similarity
            encoding_normalized = encoding / np.linalg.norm(encoding)
            encoding_normalized = encoding_normalized.reshape(1, -1).astype('float32')
            
            # Add to index
            index_id = self.index.ntotal
            self.index.add(encoding_normalized)
            
            # Store mapping
            self.user_id_to_index[user_id] = index_id
            
            # Store metadata
            self.metadata[str(user_id)] = {
                "user_id": user_id,
                "index_id": index_id,
                "encoding_dimension": len(encoding),
                "created_at": str(np.datetime64('now')),
                **(metadata or {})
            }
            
            self._save_index()
            return str(index_id)
            
        except Exception as e:
            raise ValueError(f"Failed to add encoding to FAISS: {str(e)}")
    
    def search_similar(self, encoding: np.ndarray, top_k: int = 10, threshold: float = 0.6) -> List[Dict]:
        """Search for similar face encodings in FAISS"""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Normalize query encoding
            encoding_normalized = encoding / np.linalg.norm(encoding)
            encoding_normalized = encoding_normalized.reshape(1, -1).astype('float32')
            
            # Search
            similarities, indices = self.index.search(encoding_normalized, min(top_k, self.index.ntotal))
            
            matches = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if similarity >= threshold and idx != -1:
                    # Find user_id for this index
                    user_id = None
                    for uid, index_id in self.user_id_to_index.items():
                        if index_id == idx:
                            user_id = uid
                            break
                    
                    if user_id is not None:
                        metadata = self.metadata.get(str(user_id), {})
                        matches.append({
                            'user_id': user_id,
                            'similarity': float(similarity),
                            'index_id': int(idx),
                            'metadata': metadata
                        })
            
            return sorted(matches, key=lambda x: x['similarity'], reverse=True)
            
        except Exception as e:
            raise ValueError(f"Failed to search in FAISS: {str(e)}")
    
    def update_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> bool:
        """Update existing face encoding in FAISS"""
        try:
            # FAISS doesn't support direct updates, so we need to rebuild
            # For now, we'll remove and add
            if user_id in self.user_id_to_index:
                self.delete_encoding(user_id)
            
            self.add_encoding(user_id, encoding, metadata)
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to update encoding in FAISS: {str(e)}")
    
    def delete_encoding(self, user_id: int) -> bool:
        """Delete face encoding from FAISS"""
        try:
            if user_id not in self.user_id_to_index:
                return False
            
            # Remove from mappings and metadata
            del self.user_id_to_index[user_id]
            if str(user_id) in self.metadata:
                del self.metadata[str(user_id)]
            
            # Note: FAISS doesn't support direct deletion
            # In production, you might want to rebuild the index periodically
            # For now, we'll just remove from our mappings
            
            self._save_index()
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to delete encoding from FAISS: {str(e)}")
    
    def get_encoding(self, user_id: int) -> Optional[Dict]:
        """Get face encoding by user ID from FAISS"""
        try:
            if user_id not in self.user_id_to_index:
                return None
            
            index_id = self.user_id_to_index[user_id]
            metadata = self.metadata.get(str(user_id), {})
            
            # FAISS doesn't easily retrieve by index, so we return metadata only
            # In production, you might want to store the actual encoding in metadata
            return {
                'user_id': user_id,
                'index_id': index_id,
                'metadata': metadata
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get encoding from FAISS: {str(e)}")

class VectorDBService:
    """Main service class for vector database operations"""
    
    def __init__(self, db_type: str = "chroma", **kwargs):
        self.db_type = db_type.lower()
        
        if self.db_type == "chroma":
            persist_dir = kwargs.get('persist_directory', os.getenv('CHROMA_PERSIST_DIRECTORY', './vector_db/chroma'))
            self.db = ChromaVectorDB(persist_directory=persist_dir)
        elif self.db_type == "faiss":
            index_path = kwargs.get('index_path', os.getenv('FAISS_INDEX_PATH', './vector_db/faiss_index.pkl'))
            self.db = FAISSVectorDB(index_path=index_path)
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
    
    def add_face_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> str:
        """Add face encoding for a user"""
        return self.db.add_encoding(user_id, encoding, metadata)
    
    def find_similar_faces(self, encoding: np.ndarray, top_k: int = 10, threshold: float = 0.6) -> List[Dict]:
        """Find similar face encodings"""
        return self.db.search_similar(encoding, top_k, threshold)
    
    def update_face_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> bool:
        """Update face encoding for a user"""
        return self.db.update_encoding(user_id, encoding, metadata)
    
    def delete_face_encoding(self, user_id: int) -> bool:
        """Delete face encoding for a user"""
        return self.db.delete_encoding(user_id)
    
    def get_face_encoding(self, user_id: int) -> Optional[Dict]:
        """Get face encoding for a user"""
        return self.db.get_encoding(user_id)
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            if self.db_type == "chroma":
                count = self.db.collection.count()
            elif self.db_type == "faiss":
                count = self.db.index.ntotal if self.db.index else 0
            else:
                count = 0
            
            return {
                'db_type': self.db_type,
                'total_encodings': count,
                'encoding_dimension': 128
            }
        except Exception as e:
            return {
                'db_type': self.db_type,
                'total_encodings': 0,
                'encoding_dimension': 128,
                'error': str(e)
            }

# Global vector database service instance
_vector_db_service = None

def get_vector_db_service() -> VectorDBService:
    """Get global vector database service instance"""
    global _vector_db_service
    
    if _vector_db_service is None:
        db_type = os.getenv('VECTOR_DB_TYPE', 'chroma')
        _vector_db_service = VectorDBService(db_type=db_type)
    
    return _vector_db_service