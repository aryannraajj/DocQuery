"""Embedding generation using sentence-transformers (local, no API required)."""
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """
    Generate embeddings using local sentence-transformer models.
    
    Model: all-MiniLM-L6-v2
    - Dimension: 384
    - Fast and efficient
    - Good balance between speed and quality
    - Runs entirely locally (no API calls)
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of the sentence-transformer model
        """
        self.model_name = model_name or config.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {self.model_name}")
        
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Numpy array of embeddings
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once
            
        Returns:
            Numpy array of embeddings (shape: [len(texts), embedding_dim])
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts...")
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            logger.info("Embeddings generated successfully")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.embedding_dim
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0 to 1, higher is more similar)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)

# Global instance (lazy loaded)
_embedding_generator = None

def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the global embedding generator instance."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
