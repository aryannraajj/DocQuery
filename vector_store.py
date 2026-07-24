"""Vector store implementation using FAISS for similarity search."""
import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    """
    FAISS-based vector store for efficient similarity search.
    
    Uses IndexFlatL2 for exact nearest neighbor search with L2 distance.
    Stores metadata separately for retrieved chunks.
    """
    
    def __init__(self, dimension: int = 384):
        """
        Initialize vector store.
        
        Args:
            dimension: Dimension of embedding vectors
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata: List[Dict] = []
        self.document_chunks: Dict[str, List[int]] = {}  # doc_id -> chunk indices
        logger.info(f"Initialized FAISS index with dimension: {dimension}")
    
    def add_embeddings(self, embeddings: np.ndarray, metadata: List[Dict]):
        """
        Add embeddings and metadata to the store.
        
        Args:
            embeddings: Numpy array of shape [n, dimension]
            metadata: List of metadata dicts (one per embedding)
        """
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings must match metadata length")
        
        # Ensure embeddings are float32 (FAISS requirement)
        embeddings = embeddings.astype('float32')
        
        # Add to FAISS index
        start_idx = self.index.ntotal
        self.index.add(embeddings)
        
        # Store metadata
        for i, meta in enumerate(metadata):
            self.metadata.append(meta)
            doc_id = meta.get('document', 'unknown')
            if doc_id not in self.document_chunks:
                self.document_chunks[doc_id] = []
            self.document_chunks[doc_id].append(start_idx + i)
        
        logger.info(f"Added {len(embeddings)} embeddings. Total: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of (metadata, similarity_score) tuples
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Ensure query is 2D array and float32
        query = query_embedding.reshape(1, -1).astype('float32')
        
        # Search
        top_k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query, top_k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                # Convert L2 distance to similarity score (0 to 1)
                # Lower distance = higher similarity
                similarity = 1 / (1 + distance)
                results.append((self.metadata[idx], float(similarity)))
        
        return results
    
    def remove_document(self, document_id: str) -> int:
        """
        Remove all chunks for a document.
        
        Note: FAISS doesn't support efficient deletion, so we mark as deleted
        and rebuild index periodically.
        
        Args:
            document_id: Document ID to remove
            
        Returns:
            Number of chunks removed
        """
        if document_id not in self.document_chunks:
            return 0
        
        indices_to_remove = self.document_chunks[document_id]
        
        # Mark metadata as deleted
        for idx in indices_to_remove:
            if idx < len(self.metadata):
                self.metadata[idx]['_deleted'] = True
        
        del self.document_chunks[document_id]
        logger.info(f"Marked {len(indices_to_remove)} chunks as deleted for {document_id}")
        
        return len(indices_to_remove)
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        active_chunks = sum(1 for m in self.metadata if not m.get('_deleted', False))
        return {
            'total_chunks': self.index.ntotal,
            'active_chunks': active_chunks,
            'deleted_chunks': self.index.ntotal - active_chunks,
            'documents': len(self.document_chunks),
            'dimension': self.dimension
        }
    
    def save(self, path: Optional[Path] = None):
        """
        Save index and metadata to disk.
        
        Args:
            path: Directory to save to (uses config default if not provided)
        """
        save_path = path or config.VECTOR_STORE_PATH
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = save_path / "index.faiss"
        faiss.write_index(self.index, str(index_file))
        
        # Save metadata
        metadata_file = save_path / "metadata.pkl"
        with open(metadata_file, 'wb') as f:
            pickle.dump({
                'metadata': self.metadata,
                'document_chunks': self.document_chunks,
                'dimension': self.dimension
            }, f)
        
        logger.info(f"Saved vector store to {save_path}")
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'VectorStore':
        """
        Load index and metadata from disk.
        
        Args:
            path: Directory to load from
            
        Returns:
            Loaded VectorStore instance
        """
        load_path = path or config.VECTOR_STORE_PATH
        index_file = load_path / "index.faiss"
        metadata_file = load_path / "metadata.pkl"
        
        if not index_file.exists() or not metadata_file.exists():
            logger.warning("No saved vector store found, creating new one")
            return cls()
        
        # Load FAISS index
        index = faiss.read_index(str(index_file))
        
        # Load metadata
        with open(metadata_file, 'rb') as f:
            data = pickle.load(f)
        
        # Create instance
        store = cls(dimension=data['dimension'])
        store.index = index
        store.metadata = data['metadata']
        store.document_chunks = data['document_chunks']
        
        logger.info(f"Loaded vector store from {load_path}")
        logger.info(f"Total chunks: {store.index.ntotal}")
        
        return store

# Global instance
_vector_store = None

def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        try:
            _vector_store = VectorStore.load()
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            _vector_store = VectorStore()
    return _vector_store
