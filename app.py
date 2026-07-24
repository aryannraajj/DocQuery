"""FastAPI application for RAG-based Question Answering System."""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import time
import uuid
import shutil
import logging
from datetime import datetime

from config import config
from models import (
    DocumentUploadResponse, QuestionRequest, QuestionResponse,
    DocumentListResponse, DocumentInfo, ErrorResponse, HealthResponse, SourceChunk
)
from document_processor import DocumentProcessor
from chunking import TextChunker
from embeddings import get_embedding_generator
from vector_store import get_vector_store
from llm_client import get_llm_client
from rate_limiter import get_rate_limiter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Question Answering API",
    description="Upload documents and ask questions using Retrieval-Augmented Generation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global instances
document_processor = DocumentProcessor()
chunker = TextChunker()
embedding_generator = None
vector_store = None
llm_client = None
rate_limiter = get_rate_limiter()

# Document metadata storage
documents_metadata = {}

def initialize_models():
    """Initialize models on startup (lazy loading)."""
    global embedding_generator, vector_store, llm_client
    if embedding_generator is None:
        logger.info("Initializing embedding generator...")
        embedding_generator = get_embedding_generator()
    if vector_store is None:
        logger.info("Loading vector store...")
        vector_store = get_vector_store()
    if llm_client is None:
        logger.info("Initializing LLM client...")
        llm_client = get_llm_client()

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting RAG QA API...")
    config.ensure_directories()
    initialize_models()
    logger.info("API ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Save state on shutdown."""
    logger.info("Shutting down...")
    if vector_store:
        vector_store.save()
    logger.info("Shutdown complete")

def get_client_id(request: Request) -> str:
    """Get client identifier from request."""
    return request.client.host

async def process_document_background(file_path: Path, document_id: str, filename: str):
    """Background task to process document."""
    try:
        logger.info(f"Processing document: {filename}")
        
        # Extract text
        text, metadata = document_processor.process_document(file_path)
        logger.info(f"Extracted {len(text)} characters from {filename}")
        
        # Create chunks
        chunks = chunker.create_chunks(text, filename)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        chunk_texts = [chunk['content'] for chunk in chunks]
        embeddings = embedding_generator.generate_embeddings_batch(chunk_texts)
        
        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk['embedding_index'] = i
            chunk['document_id'] = document_id
        
        # Store in vector store
        vector_store.add_embeddings(embeddings, chunks)
        vector_store.save()
        
        # Update document metadata
        documents_metadata[document_id] = {
            'filename': filename,
            'chunks_count': len(chunks),
            'upload_date': datetime.now().isoformat(),
            'file_size': file_path.stat().st_size,
            'status': 'completed'
        }
        
        logger.info(f"Document {filename} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing document {filename}: {e}")
        documents_metadata[document_id] = {
            'filename': filename,
            'status': 'failed',
            'error': str(e)
        }

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the frontend HTML."""
    html_file = Path("static/index.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return "<h1>RAG QA API</h1><p>Frontend not found. Please add static/index.html</p>"

@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...)
):
    """
    Upload a document for processing.
    
    Supports: PDF, TXT, DOCX
    """
    # Rate limiting
    client_id = get_client_id(request)
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {config.RATE_LIMIT_PER_MINUTE} requests per minute."
        )
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # Initialize models if not already done
        initialize_models()
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = config.UPLOAD_DIR / f"{document_id}{file_ext}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Add background task for processing
        background_tasks.add_task(
            process_document_background,
            file_path,
            document_id,
            file.filename
        )
        
        # Store initial metadata
        documents_metadata[document_id] = {
            'filename': file.filename,
            'status': 'processing',
            'upload_date': datetime.now().isoformat()
        }
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="processing",
            message="Document uploaded successfully. Processing in background."
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: Request, question_req: QuestionRequest):
    """
    Ask a question based on uploaded documents.
    """
    # Rate limiting
    client_id = get_client_id(request)
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {config.RATE_LIMIT_PER_MINUTE} requests per minute."
        )
    
    try:
        start_time = time.time()
        
        # Initialize models
        initialize_models()
        
        # Generate question embedding
        question_embedding = embedding_generator.generate_embedding(question_req.question)
        
        # Search vector store
        results = vector_store.search(question_embedding, top_k=question_req.top_k)
        
        if not results:
            return QuestionResponse(
                question=question_req.question,
                answer="No documents have been uploaded yet. Please upload documents first.",
                sources=[],
                processing_time=time.time() - start_time
            )
        
        # Prepare context for LLM
        context_chunks = []
        sources = []
        
        for metadata, similarity_score in results:
            if metadata.get('_deleted'):
                continue
                
            context_chunks.append({
                'content': metadata.get('content', ''),
                'document': metadata.get('document', 'Unknown'),
                'similarity_score': similarity_score
            })
            
            sources.append(SourceChunk(
                document=metadata.get('document', 'Unknown'),
                content=metadata.get('content', '')[:200] + "...",
                similarity_score=round(similarity_score, 3),
                page=metadata.get('page')
            ))
        
        # Generate answer
        answer = llm_client.generate_answer_advanced(question_req.question, context_chunks)
        
        processing_time = time.time() - start_time
        
        return QuestionResponse(
            question=question_req.question,
            answer=answer,
            sources=sources,
            processing_time=round(processing_time, 3)
        )
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """List all uploaded documents."""
    documents = []
    for doc_id, metadata in documents_metadata.items():
        if metadata.get('status') == 'completed':
            documents.append(DocumentInfo(
                document_id=doc_id,
                filename=metadata['filename'],
                upload_date=metadata['upload_date'],
                chunks_count=metadata.get('chunks_count', 0),
                file_size=metadata.get('file_size', 0)
            ))
    
    return DocumentListResponse(
        documents=documents,
        total=len(documents)
    )

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its chunks."""
    if document_id not in documents_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Remove from vector store
        filename = documents_metadata[document_id]['filename']
        removed_count = vector_store.remove_document(filename)
        vector_store.save()
        
        # Remove metadata
        del documents_metadata[document_id]
        
        # Remove file
        for ext in config.ALLOWED_EXTENSIONS:
            file_path = config.UPLOAD_DIR / f"{document_id}{ext}"
            if file_path.exists():
                file_path.unlink()
        
        return {
            "message": "Document deleted successfully",
            "chunks_removed": removed_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        documents_count=len([d for d in documents_metadata.values() if d.get('status') == 'completed']),
        vector_store_initialized=vector_store is not None and vector_store.index.ntotal > 0
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
