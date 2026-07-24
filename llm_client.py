"""LLM client for answer generation using local models or simple extractive QA."""
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    """
    Answer generator for RAG system.
    
    Uses a simple extractive approach that combines retrieved chunks
    into a coherent answer without requiring external LLM APIs.
    
    For production, this can be replaced with:
    - Local LLMs (llama.cpp, GPT4All)
    - Cloud APIs (OpenAI, Anthropic, Google)
    """
    
    def __init__(self):
        """Initialize the LLM client."""
        logger.info("Initialized extractive QA client")
    
    def generate_answer(self, question: str, context_chunks: List[Dict]) -> str:
        """
        Generate answer from question and retrieved context.
        
        Uses a simple extractive approach:
        1. Combines top chunks
        2. Provides a structured answer
        
        Args:
            question: User's question
            context_chunks: List of retrieved chunk dictionaries with 'content' and 'similarity_score'
            
        Returns:
            Generated answer string
        """
        if not context_chunks:
            return "I couldn't find relevant information to answer your question. Please try uploading more documents or rephrasing your question."
        
        # Filter chunks by similarity threshold
        relevant_chunks = [
            chunk for chunk in context_chunks 
            if chunk.get('similarity_score', 0) > 0.3
        ]
        
        if not relevant_chunks:
            return "I found some potentially related content, but it doesn't seem directly relevant to your question. Could you please rephrase or provide more context?"
        
        # Build answer from top chunks
        answer_parts = []
        answer_parts.append(f"Based on the uploaded documents, here's what I found:\n")
        
        # Use top 3 most relevant chunks
        for i, chunk in enumerate(relevant_chunks[:3], 1):
            content = chunk.get('content', '')
            doc_name = chunk.get('document', 'Unknown')
            
            # Extract most relevant sentences (first 2-3 sentences)
            sentences = content.split('.')[:3]
            excerpt = '. '.join(s.strip() for s in sentences if s.strip()) + '.'
            
            answer_parts.append(f"\n{i}. {excerpt}")
            
        # Add source summary
        unique_docs = set(chunk.get('document', 'Unknown') for chunk in relevant_chunks)
        if len(unique_docs) == 1:
            answer_parts.append(f"\n\n(Source: {list(unique_docs)[0]})")
        else:
            answer_parts.append(f"\n\n(Sources: {', '.join(sorted(unique_docs))})")
        
        return ''.join(answer_parts)
    
    def generate_answer_advanced(self, question: str, context_chunks: List[Dict]) -> str:
        """
        Advanced answer generation using question-type detection.
        
        This method provides better answers by detecting question type
        and formatting responses accordingly.
        
        Args:
            question: User's question
            context_chunks: Retrieved context chunks
            
        Returns:
            Formatted answer
        """
        if not context_chunks:
            return "No relevant information found."
        
        # Detect question type
        question_lower = question.lower()
        
        # What/Who questions - extract specific information
        if question_lower.startswith(('what', 'who', 'which')):
            return self._answer_what_question(question, context_chunks)
        
        # Why/How questions - provide explanation
        elif question_lower.startswith(('why', 'how')):
            return self._answer_explanation_question(question, context_chunks)
        
        # When/Where questions - extract temporal/location info
        elif question_lower.startswith(('when', 'where')):
            return self._answer_factual_question(question, context_chunks)
        
        # Default: general answer
        else:
            return self.generate_answer(question, context_chunks)
    
    def _answer_what_question(self, question: str, chunks: List[Dict]) -> str:
        """Answer 'what/who/which' questions."""
        top_chunk = chunks[0]
        content = top_chunk.get('content', '')
        
        # Extract first few sentences as answer
        sentences = [s.strip() + '.' for s in content.split('.')[:2] if s.strip()]
        answer = ' '.join(sentences)
        
        if len(chunks) > 1:
            answer += f"\n\nAdditional context: {chunks[1].get('content', '')[:200]}..."
        
        return answer
    
    def _answer_explanation_question(self, question: str, chunks: List[Dict]) -> str:
        """Answer 'why/how' questions with explanatory context."""
        # Combine top chunks for full context
        combined_text = '\n\n'.join([
            chunk.get('content', '')[:300] 
            for chunk in chunks[:2]
        ])
        
        return f"Here's the explanation:\n\n{combined_text}"
    
    def _answer_factual_question(self, question: str, chunks: List[Dict]) -> str:
        """Answer 'when/where' questions."""
        # Look for specific information in top chunk
        content = chunks[0].get('content', '')
        return content[:400] + ("..." if len(content) > 400 else "")

# Global instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
