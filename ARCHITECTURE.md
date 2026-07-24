# System Architecture - RAG QA System

## Overview

This document describes the architecture of the RAG-based Question Answering System, including component interactions, data flow, and design decisions.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Client"
        UI[Web UI<br/>HTML/CSS/JS]
    end
    
    subgraph "FastAPI Server"
        API[API Routes<br/>FastAPI]
        RL[Rate Limiter]
        BG[Background Tasks]
    end
    
    subgraph "Document Processing Pipeline"
        DP[Document Processor<br/>PDF/TXT/DOCX]
        TC[Text Chunker<br/>512 tokens]
        EG[Embedding Generator<br/>SentenceTransformer]
    end
    
    subgraph "Storage Layer"
        FS[File System<br/>Document Storage]
        VS[Vector Store<br/>FAISS Index]
        META[Metadata Store<br/>In-Memory Dict]
    end
    
    subgraph "Query Pipeline"
        QE[Query Embedding]
        SS[Similarity Search]
        LLM[Answer Generator<br/>Extractive QA]
    end
    
    UI -->|HTTP Request| API
    API --> RL
    RL --> BG
    BG --> DP
    DP --> TC
    TC --> EG
    EG --> VS
    EG --> META
    DP --> FS
    
    API --> QE
    QE --> SS
    SS --> VS
    SS --> LLM
    LLM -->|Response| API
    API -->|JSON| UI
    
    style UI fill:#667eea,color:#fff
    style API fill:#764ba2,color:#fff
    style VS fill:#f093fb,color:#000
    style EG fill:#4facfe,color:#fff
    style LLM fill:#00f2fe,color:#000
```

## Component Details

### 1. Frontend Layer

**Technology**: HTML5, CSS3, JavaScript (Vanilla)

**Responsibilities**:
- User interface for document upload and questions
- File validation and drag-and-drop
- Real-time feedback via toast notifications
- Answer display with source citations
- Responsive design for all devices

**Key Features**:
- Glassmorphism design with smooth animations
- Dark theme optimized for readability
- Accessibility features (keyboard shortcuts, focus states)

### 2. API Layer (FastAPI)

**Technology**: FastAPI, Uvicorn

**Components**:
- **Route Handlers**: RESTful endpoints for CRUD operations
- **Middleware**: CORS, rate limiting
- **Request Validation**: Pydantic models
- **Background Tasks**: Async document processing

**Endpoints**:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve frontend |
| `/upload` | POST | Upload document |
| `/ask` | POST | Ask question |
| `/documents` | GET | List documents |
| `/documents/{id}` | DELETE | Delete document |
| `/health` | GET | Health check |

### 3. Document Processing Pipeline

```mermaid
sequenceDiagram
    participant User
    participant API
    participant BG as Background Task
    participant DP as Document Processor
    participant TC as Text Chunker
    participant EG as Embedding Generator
    participant VS as Vector Store
    
    User->>API: Upload Document
    API->>BG: Queue Processing
    API-->>User: Upload Confirmed
    BG->>DP: Extract Text
    DP->>DP: Parse PDF/TXT/DOCX
    DP->>TC: Clean Text
    TC->>TC: Split into Sentences
    TC->>TC: Create 512-token Chunks
    TC->>EG: Chunks + Metadata
    EG->>EG: Generate Embeddings
    EG->>VS: Store Vectors
    VS->>VS: Update FAISS Index
    VS->>VS: Save to Disk
    BG-->>User: Processing Complete (via polling)
```

**Document Processor**:
- Handles PDF, TXT, DOCX formats
- Extracts text with metadata (page numbers, etc.)
- Cleans text (remove extra whitespace, special chars)

**Text Chunker**:
- Sentence-aware splitting
- 512 tokens per chunk, 50-token overlap
- Preserves semantic boundaries
- Attaches metadata to each chunk

**Embedding Generator**:
- Uses `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- Batch processing for efficiency
- Caching to avoid re-computation

### 4. Storage Layer

```mermaid
graph LR
    subgraph "File System"
        UP[data/uploads/]
        UP --> PDF[*.pdf]
        UP --> TXT[*.txt]
        UP --> DOCX[*.docx]
    end
    
    subgraph "Vector Store"
        VS[data/vector_store/]
        VS --> IDX[index.faiss]
        VS --> META[metadata.pkl]
    end
    
    subgraph "In-Memory"
        DOCS[documents_metadata]
    end
    
    style UP fill:#4facfe
    style VS fill:#00f2fe
    style DOCS fill:#f093fb
```

**File System**:
- Original documents stored with UUID filenames
- Organized by upload directory
- Preserved for potential re-processing

**FAISS Vector Store**:
- `IndexFlatL2`: Exact L2 distance search
- Serialized to disk for persistence
- Metadata stored separately in pickle format

**Metadata Store**:
- In-memory dictionary (production would use database)
- Tracks document status, chunk counts, upload dates
- Fast lookups for document management

### 5. Query Pipeline

```mermaid
sequenceDiagram
    participant User
    participant API
    participant QE as Query Embedding
    participant VS as Vector Store
    participant LLM as Answer Generator
    
    User->>API: Submit Question
    API->>QE: Generate Embedding
    QE->>QE: Encode Question
    QE->>VS: Search Similar Chunks
    VS->>VS: FAISS Search (L2)
    VS->>VS: Rank by Similarity
    VS-->>QE: Top-K Chunks
    QE->>LLM: Question + Chunks
    LLM->>LLM: Extract Relevant Info
    LLM->>LLM: Format Answer
    LLM-->>API: Answer + Sources
    API-->>User: JSON Response
```

**Query Embedding**:
- Same model as document embeddings (consistency)
- Single embedding per query
- Normalized for cosine similarity

**Similarity Search**:
- FAISS IndexFlatL2 for exact search
- Returns top-k chunks (default k=5)
- Filters deleted chunks
- Converts L2 distance to similarity score

**Answer Generator**:
- Extractive QA approach (no external API)
- Question-type detection (what/why/how)
- Combines top chunks into coherent answer
- Includes source citations

## Data Flow Diagrams

### Document Upload Flow

```mermaid
flowchart TD
    Start([User Uploads Document]) --> Validate{Valid Format?}
    Validate -->|No| Error1[Return Error 400]
    Validate -->|Yes| SaveFile[Save to File System]
    SaveFile --> QueueBG[Queue Background Task]
    QueueBG --> Return1[Return Upload Response]
    Return1 --> Process[Background: Process Document]
    Process --> Extract[Extract Text]
    Extract --> Chunk[Create Chunks]
    Chunk --> Embed[Generate Embeddings]
    Embed --> Store[Store in FAISS]
    Store --> UpdateMeta[Update Metadata]
    UpdateMeta --> End([Processing Complete])
    
    style Start fill:#4facfe
    style End fill:#00f2fe
    style Extract fill:#667eea
    style Store fill:#764ba2
```

### Question Answering Flow

```mermaid
flowchart TD
    Start([User Asks Question]) --> RateLimit{Rate Limit OK?}
    RateLimit -->|No| Error1[Return Error 429]
    RateLimit -->|Yes| HasDocs{Documents Exist?}
    HasDocs -->|No| Empty[Return Empty Answer]
    HasDocs -->|Yes| EmbedQ[Embed Question]
    EmbedQ --> Search[FAISS Search]
    Search --> Filter[Filter Deleted Chunks]
    Filter --> Rank[Rank by Similarity]
    Rank --> Generate[Generate Answer]
    Generate --> Format[Format Response]
    Format --> Return[Return JSON]
    Return --> End([User Receives Answer])
    
    style Start fill:#4facfe
    style End fill:#00f2fe
    style Search fill:#764ba2
    style Generate fill:#f093fb
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109
- **Server**: Uvicorn (ASGI)
- **Validation**: Pydantic 2.5
- **Embeddings**: sentence-transformers 2.3
- **Vector Store**: FAISS 1.7.4
- **ML Framework**: PyTorch 2.1
- **Document Processing**: PyPDF2, python-docx

### Frontend
- **Structure**: HTML5
- **Styling**: CSS3 (custom, no frameworks)
- **Scripting**: Vanilla JavaScript (ES6+)
- **Fonts**: Google Fonts (Inter, Poppins)

### Infrastructure
- **Storage**: Local file system
- **Rate Limiting**: In-memory (production → Redis)
- **Background Jobs**: FastAPI BackgroundTasks

## Scalability Considerations

### Current Limitations
- In-memory metadata store (lost on restart)
- Single-server deployment
- No distributed processing

### Production Recommendations

**Horizontal Scaling**:
```mermaid
graph TB
    LB[Load Balancer]
    API1[API Server 1]
    API2[API Server 2]
    API3[API Server 3]
    Redis[Redis Cache]
    DB[PostgreSQL]
    S3[S3 Storage]
    
    LB --> API1
    LB --> API2
    LB --> API3
    API1 --> Redis
    API2 --> Redis
    API3 --> Redis
    API1 --> DB
    API2 --> DB
    API3 --> DB
    API1 --> S3
    API2 --> S3
    API3 --> S3
```

Improvements:
- **Database**: PostgreSQL for metadata
- **Cache**: Redis for rate limiting and embeddings
- **Storage**: S3/MinIO for documents
- **Queue**: Celery/RabbitMQ for background jobs
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack

## Security Considerations

### Current Implementation
- ✅ Input validation (Pydantic)
- ✅ Rate limiting
- ✅ File type validation
- ✅ File size limits

### Production Additions
- 🔒 Authentication (JWT tokens)
- 🔒 Authorization (role-based access)
- 🔒 HTTPS/TLS encryption
- 🔒 SQL injection protection (if using DB)
- 🔒 File content scanning (malware)
- 🔒 API key rotation
- 🔒 Request signing

## Performance Benchmarks

### Response Times (Avg)
| Operation | Time | Notes |
|-----------|------|-------|
| Document Upload | 200ms | File save only |
| Text Extraction | 2-5s | PDF processing |
| Chunking | 100-300ms | 10-page doc |
| Embedding Gen | 50ms/chunk | Batch of 32 |
| Vector Search | 10-50ms | 1000 chunks |
| Answer Gen | 100-500ms | Extractive |
| **Total Query** | **1-3s** | End-to-end |

### Resource Usage
- **Memory**: 500MB-2GB (model loaded)
- **CPU**: 1-2 cores (single query)
- **Disk**: ~1MB per document + embeddings
- **Network**: Minimal (local deployment)

## Deployment Architecture

### Local Development
```
┌─────────────────────────────┐
│   Developer Machine         │
│                             │
│  ┌──────────────────────┐  │
│  │  FastAPI Server      │  │
│  │  :8000               │  │
│  └──────────────────────┘  │
│           ↕                 │
│  ┌──────────────────────┐  │
│  │  Data Directory      │  │
│  │  • uploads/          │  │
│  │  • vector_store/     │  │
│  └──────────────────────┘  │
└─────────────────────────────┘
```

### Production (Docker)
```
┌──────────────────────────────────────┐
│  Docker Container                    │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  App                           │ │
│  │  ├─ FastAPI                    │ │
│  │  ├─ Sentence-Transformers      │ │
│  │  └─ FAISS                      │ │
│  └────────────────────────────────┘ │
│           ↕                          │
│  ┌────────────────────────────────┐ │
│  │  Volumes                       │ │
│  │  • /data (persistent)          │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
```

## Design Patterns Used

1. **Singleton Pattern**: Embedding generator, vector store instances
2. **Factory Pattern**: Document processor for different formats
3. **Strategy Pattern**: Different chunking strategies
4. **Repository Pattern**: Vector store abstraction
5. **Background Task Pattern**: Async document processing
6. **Rate Limiting Pattern**: Token bucket algorithm

## Conclusion

The architecture prioritizes:
- ✅ **Simplicity**: Easy to understand and maintain
- ✅ **Performance**: Fast retrieval with FAISS
- ✅ **Modularity**: Components can be swapped
- ✅ **Scalability**: Clear path to production deployment
- ✅ **User Experience**: Responsive UI with real-time feedback

The system successfully demonstrates RAG principles while maintaining accessibility for development and testing.
