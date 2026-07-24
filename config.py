"""Configuration management for the RAG QA system."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # Paths
    BASE_DIR = Path(__file__).parent
    UPLOAD_DIR = BASE_DIR / "data" / "uploads"
    VECTOR_STORE_PATH = BASE_DIR / "data" / "vector_store"
    
    # Chunking parameters
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # Embedding model
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Upload settings
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    
    # Retrieval settings
    TOP_K_CHUNKS = 5
    MIN_SIMILARITY_SCORE = 0.3
    
    # Server settings
    HOST = "0.0.0.0"
    PORT = 8000
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

config = Config()
config.ensure_directories()
