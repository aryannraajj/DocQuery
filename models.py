"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str
    filename: str
    status: str
    message: str
    chunks_created: Optional[int] = None
    
class QuestionRequest(BaseModel):
    """Request model for asking questions."""
    question: str = Field(..., min_length=3, max_length=500)
    top_k: Optional[int] = Field(default=5, ge=1, le=10)
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

class SourceChunk(BaseModel):
    """Model for source chunk information."""
    document: str
    content: str
    similarity_score: float
    page: Optional[int] = None

class QuestionResponse(BaseModel):
    """Response model for question answering."""
    question: str
    answer: str
    sources: List[SourceChunk]
    processing_time: float
    
class DocumentInfo(BaseModel):
    """Model for document information."""
    document_id: str
    filename: str
    upload_date: str
    chunks_count: int
    file_size: int

class DocumentListResponse(BaseModel):
    """Response model for document listing."""
    documents: List[DocumentInfo]
    total: int

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    documents_count: int
    vector_store_initialized: bool
