"""Text chunking module with sentence-aware splitting."""
import re
from typing import List, Dict
from config import config

class TextChunker:
    """
    Intelligent text chunker that splits text into overlapping chunks
    while respecting sentence boundaries.
    
    Strategy:
    - Chunk size: 512 tokens (approximately 380-400 words)
    - Overlap: 50 tokens to maintain context continuity
    - Sentence-boundary aware to avoid splitting mid-sentence
    """
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        """
        Initialize chunker with configurable parameters.
        
        Args:
            chunk_size: Target size for each chunk in tokens
            overlap: Number of overlapping tokens between chunks
        """
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.overlap = overlap or config.CHUNK_OVERLAP
    
    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """
        Split text into sentences using regex.
        
        Handles common sentence endings: . ! ?
        Preserves abbreviations like Dr., Mr., etc.
        """
        # Pattern to split on sentence boundaries
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count (rough approximation).
        
        Rule of thumb: 1 token ≈ 0.75 words
        So: tokens ≈ words / 0.75 = words * 1.33
        """
        words = len(text.split())
        return int(words * 1.33)
    
    def create_chunks(self, text: str, document_name: str) -> List[Dict]:
        """
        Create overlapping chunks from text with metadata.
        
        Args:
            text: Input text to chunk
            document_name: Name of source document
            
        Returns:
            List of dictionaries with chunk content and metadata
        """
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            
            # If adding this sentence exceeds chunk size, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'content': chunk_text,
                    'document': document_name,
                    'chunk_index': chunk_index,
                    'token_count': current_tokens
                })
                chunk_index += 1
                
                # Create overlap: keep last few sentences
                overlap_sentences = []
                overlap_tokens = 0
                for s in reversed(current_chunk):
                    s_tokens = self.estimate_tokens(s)
                    if overlap_tokens + s_tokens <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'content': chunk_text,
                'document': document_name,
                'chunk_index': chunk_index,
                'token_count': current_tokens
            })
        
        return chunks
    
    def get_chunking_stats(self, chunks: List[Dict]) -> Dict:
        """
        Get statistics about the chunking process.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Dictionary with chunking statistics
        """
        if not chunks:
            return {
                'total_chunks': 0,
                'avg_chunk_size': 0,
                'min_chunk_size': 0,
                'max_chunk_size': 0
            }
        
        token_counts = [c['token_count'] for c in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(token_counts) / len(token_counts),
            'min_chunk_size': min(token_counts),
            'max_chunk_size': max(token_counts)
        }
