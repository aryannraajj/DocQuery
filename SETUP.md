# Quick Setup Guide

## Installation Steps

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note**: First installation will download the embedding model (~80-100MB). This may take 5-10 minutes depending on your internet connection.

### 4. Configure Environment (Optional)

The system works with default settings, but you can customize:

```bash
copy .env.example .env  # Windows
# OR
cp .env.example .env    # Linux/Mac
```

Edit `.env` to change settings like chunk size, rate limits, etc.

### 5. Run the Application

**Option A - Using Python directly:**
```bash
python app.py
```

**Option B - Using start script (Windows):**
```bash
start.bat
```

**Option C - Using uvicorn:**
```bash
uvicorn app:app --reload
```

### 6. Access the Application

Open your browser and navigate to:
- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Troubleshooting

### Installation Issues

**Problem**: Dependencies fail to install
**Solution**:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Problem**: torch installation is slow
**Solution**: Use CPU-only version which is smaller:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Problem**: Import errors after installation
**Solution**: Make sure virtual environment is activated:
```bash
# Check if venv is active (should show (venv) in prompt)
where python  # Windows
which python  # Linux/Mac
```

### Runtime Issues

**Problem**: "Model not found" error
**Solution**: The model will download automatically on first run. Wait for the download to complete.

**Problem**: Port 8000 already in use
**Solution**: Change port in `config.py` or run:
```bash
uvicorn app:app --port 8001
```

**Problem**: FAISS index errors
**Solution**: Delete the vector store and restart:
```bash
rm -rf data/vector_store/*  # Linux/Mac
del /s data\vector_store\*  # Windows
```

## Testing the System

### 1. Upload Sample Documents

Two sample documents are provided in `sample_documents/`:
- `test_document.txt`: General RAG system info
- `ml_healthcare.txt`: Machine learning in healthcare

Upload these through the web interface to test the system.

### 2. Try Sample Questions

After uploading, try these questions:
- "What is this document about?"
- "What are the key features?"
- "How does the chunking strategy work?"
- "What are the benefits of ML in healthcare?"
- "What are the performance metrics?"

### 3. Verify Functionality

- ✅ Document upload works
- ✅ Documents appear in list
- ✅ Questions return answers
- ✅ Source citations are shown
- ✅ Similarity scores are displayed

## System Requirements

### Minimum
- Python 3.8+
- 4GB RAM
- 2GB free disk space
- Windows/Linux/Mac

### Recommended
- Python 3.10+
- 8GB RAM
- 4GB free disk space
- SSD for faster file operations

## Next Steps

1. **Customize**: Edit `config.py` or `.env` for your needs
2. **Add Documents**: Upload your own PDFs, TXTs, or DOCX files
3. **Ask Questions**: Query your documents
4. **Integrate**: Use the API endpoints in your applications
5. **Deploy**: Consider Docker deployment for production

## API Usage Examples

### Upload Document (curl)

```bash
curl -X POST -F "file=@document.pdf" http://localhost:8000/upload
```

### Ask Question (curl)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic?"}'
```

### List Documents (curl)

```bash
curl http://localhost:8000/documents
```

### Python Example

```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload',
        files={'file': f}
    )
    print(response.json())

# Ask question
response = requests.post(
    'http://localhost:8000/ask',
    json={'question': 'What is this about?'}
)
print(response.json())
```

## Additional Resources

- **README.md**: Full project documentation
- **ARCHITECTURE.md**: System design and diagrams
- **TECHNICAL_EXPLANATION.md**: Chunking strategy, metrics, failure cases
- **API Docs**: http://localhost:8000/docs (when running)

## Support

For issues:
1. Check this setup guide
2. Review troubleshooting section
3. Check the README.md
4. Verify system requirements
5. Ensure all dependencies are installed

---

**Ready to start!** Follow the steps above and you'll have the system running in minutes.
