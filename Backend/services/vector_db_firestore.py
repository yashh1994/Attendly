"""
Firestore-backed Vector Database for Face Encodings

This module provides a `FirestoreVectorDB` class that implements the same
methods used by the project's vector DB interface:
  - add_encoding(user_id, encoding, metadata=None)
  - search_similar(encoding, top_k=10, threshold=0.6)
  - update_encoding(user_id, encoding, metadata=None)
  - delete_encoding(user_id)
  - get_encoding(user_id)
  - get_stats()

Usage:
  - Install dependency: `pip install google-cloud-firestore`
  - Set credentials: set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON
  - Replace your DB object with an instance of `FirestoreVectorDB` (or import and
    instantiate directly where you construct the vector DB).

Notes:
  - This implementation uses a naive client-side similarity search: it fetches
    documents from Firestore and computes cosine similarity in Python. For small
    to medium datasets this is fine; for production large-scale usage consider
    Firestore's vector search features (when available) or a managed vector DB.
"""

import os
import numpy as np
import json
from typing import List, Dict, Optional

try:
    from google.cloud import firestore
except Exception:
    firestore = None


class FirestoreVectorDB:
    """Firestore-backed vector DB implementation.

    Documents are stored with id `user_{user_id}` and fields:
      - embedding: list[float]
      - metadata: dict
      - encoding_dimension: int
      - created_at / updated_at: ISO-like string
    """

    def __init__(self, collection_name: str = "face_encodings", project: Optional[str] = None):
        if firestore is None:
            raise ImportError("google-cloud-firestore not installed. Install with: pip install google-cloud-firestore")

        # Ensure GOOGLE_APPLICATION_CREDENTIALS points to an absolute path if the
        # user provided a relative path in .env. This helps when the server is
        # started from a different working directory.
        cred_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if cred_env:
            # If path is not absolute and file doesn't exist as given, try common locations
            if not os.path.isabs(cred_env) or not os.path.exists(cred_env):
                candidate_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), cred_env),
                    os.path.join(os.getcwd(), cred_env),
                ]
                for p in candidate_paths:
                    if os.path.exists(p):
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(p)
                        cred_env = os.path.abspath(p)
                        break

        # Initialize client (will use GOOGLE_APPLICATION_CREDENTIALS if set)
        if project:
            self.client = firestore.Client(project=project)
        else:
            self.client = firestore.Client()

        self.collection_name = collection_name
        self.collection = self.client.collection(collection_name)

    def _doc_id(self, user_id: int) -> str:
        return f"user_{user_id}"

    @staticmethod
    def _to_list(encoding: np.ndarray) -> List[float]:
        return encoding.tolist() if isinstance(encoding, np.ndarray) else list(encoding)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def add_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> str:
        """Add face encoding to Firestore. Returns document id."""
        try:
            doc_id = self._doc_id(user_id)
            embedding = self._to_list(encoding)
            meta = {
                "user_id": user_id,
                "encoding_dimension": len(embedding),
                "created_at": str(np.datetime64('now')),
            }
            # Merge user metadata if provided
            if metadata:
                meta.update(metadata)

            doc_ref = self.collection.document(doc_id)
            doc_ref.set({
                "embedding": embedding,
                "metadata": meta,
            })
            return doc_id
        except Exception as e:
            raise ValueError(f"Failed to add encoding to Firestore: {e}")

    def get_encoding(self, user_id: int) -> Optional[Dict]:
        """Retrieve encoding and metadata for a user id."""
        try:
            doc_id = self._doc_id(user_id)
            doc = self.collection.document(doc_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict() or {}
            embedding = data.get('embedding')
            metadata = data.get('metadata', {})
            return {
                'user_id': user_id,
                'encoding': np.array(embedding, dtype=np.float32) if embedding is not None else None,
                'metadata': metadata
            }
        except Exception as e:
            raise ValueError(f"Failed to get encoding from Firestore: {e}")

    def update_encoding(self, user_id: int, encoding: np.ndarray, metadata: Dict = None) -> bool:
        """Update an existing encoding (or create if not exists)."""
        try:
            doc_id = self._doc_id(user_id)
            embedding = self._to_list(encoding)
            meta = {
                "user_id": user_id,
                "encoding_dimension": len(embedding),
                "updated_at": str(np.datetime64('now')),
            }
            if metadata:
                meta.update(metadata)

            doc_ref = self.collection.document(doc_id)
            doc_ref.set({
                "embedding": embedding,
                "metadata": meta,
            }, merge=True)
            return True
        except Exception as e:
            raise ValueError(f"Failed to update encoding in Firestore: {e}")

    def delete_encoding(self, user_id: int) -> bool:
        """Delete a user's encoding from Firestore."""
        try:
            doc_id = self._doc_id(user_id)
            doc_ref = self.collection.document(doc_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            doc_ref.delete()
            return True
        except Exception as e:
            raise ValueError(f"Failed to delete encoding from Firestore: {e}")

    def search_similar(self, encoding: np.ndarray, top_k: int = 10, threshold: float = 0.6) -> List[Dict]:
        """Naive similarity search:

        - Fetches documents from Firestore and computes cosine similarity in Python.
        - Returns list of matches with fields: user_id, similarity, distance (1-similarity), metadata
        """
        try:
            q_vec = np.asarray(encoding, dtype=np.float32)
            # Read all documents. For large collections this is inefficient; consider
            # adding indexing or using a true vector search product.
            docs = list(self.collection.stream())

            matches = []
            for doc in docs:
                data = doc.to_dict() or {}
                emb = data.get('embedding')
                meta = data.get('metadata', {})
                if emb is None:
                    continue
                d_vec = np.asarray(emb, dtype=np.float32)
                sim = self._cosine_similarity(q_vec, d_vec)
                if sim >= threshold:
                    user_id = meta.get('user_id')
                    matches.append({
                        'user_id': user_id,
                        'similarity': float(sim),
                        'distance': float(1.0 - sim),
                        'metadata': meta
                    })

            matches = sorted(matches, key=lambda x: x['similarity'], reverse=True)
            return matches[:top_k]
        except Exception as e:
            raise ValueError(f"Failed to search in Firestore: {e}")

    def get_stats(self) -> Dict:
        """Return simple collection stats: total documents and embedding dimension (best-effort)."""
        try:
            docs = list(self.collection.stream())
            total = len(docs)
            dimension = None
            for doc in docs:
                data = doc.to_dict() or {}
                emb = data.get('embedding')
                if emb:
                    dimension = len(emb)
                    break

            return {
                'db_type': 'firestore',
                'total_encodings': total,
                'encoding_dimension': dimension or 0
            }
        except Exception as e:
            return {
                'db_type': 'firestore',
                'total_encodings': 0,
                'encoding_dimension': 0,
                'error': str(e)
            }
