// ========================================
// RAG QA System - Interactive JavaScript
// ========================================

const API_BASE_URL = '';

// DOM Elements
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const documentsContainer = document.getElementById('documentsContainer');
const questionForm = document.getElementById('questionForm');
const questionInput = document.getElementById('questionInput');
const charCount = document.getElementById('charCount');
const answerContainer = document.getElementById('answerContainer');
const answerContent = document.getElementById('answerContent');
const sourcesList = document.getElementById('sourcesList');
const answerMeta = document.getElementById('answerMeta');
const loadingOverlay = document.getElementById('loadingOverlay');
const toastContainer = document.getElementById('toastContainer');

// State
let uploadedDocuments = [];

// ========================================
// Initialization
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadDocuments();
});

function initializeEventListeners() {
    // Upload zone events
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', handleDragOver);
    uploadZone.addEventListener('dragleave', handleDragLeave);
    uploadZone.addEventListener('drop', handleDrop);

    // Question form
    questionForm.addEventListener('submit', handleQuestionSubmit);
    questionInput.addEventListener('input', updateCharCount);
}

// ========================================
// File Upload Handling
// ========================================

function handleDragOver(e) {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files);
    uploadFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    uploadFiles(files);
    e.target.value = ''; // Reset input
}

async function uploadFiles(files) {
    if (files.length === 0) return;

    // Validate file types
    const validExtensions = ['.pdf', '.txt', '.docx'];
    const invalidFiles = files.filter(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        return !validExtensions.includes(ext);
    });

    if (invalidFiles.length > 0) {
        showToast('error', `Invalid file type(s): ${invalidFiles.map(f => f.name).join(', ')}`);
        return;
    }

    // Upload each file
    for (const file of files) {
        await uploadSingleFile(file);
    }
}

async function uploadSingleFile(file) {
    showLoading(true);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        showToast('success', `${file.name} uploaded successfully! Processing...`);

        // Wait a bit for processing, then reload documents
        setTimeout(() => loadDocuments(), 2000);

    } catch (error) {
        console.error('Upload error:', error);
        showToast('error', `Failed to upload ${file.name}: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

// ========================================
// Document Management
// ========================================

async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);

        if (!response.ok) {
            throw new Error('Failed to load documents');
        }

        const data = await response.json();
        uploadedDocuments = data.documents;
        renderDocuments();

    } catch (error) {
        console.error('Load documents error:', error);
        showToast('error', 'Failed to load documents');
    }
}

function renderDocuments() {
    if (uploadedDocuments.length === 0) {
        documentsContainer.innerHTML = '<p class="empty-state">No documents uploaded yet</p>';
        return;
    }

    const html = uploadedDocuments.map(doc => `
        <div class="document-item">
            <div class="doc-info">
                <div class="doc-name">📄 ${doc.filename}</div>
                <div class="doc-meta">
                    ${doc.chunks_count} chunks • 
                    ${formatFileSize(doc.file_size)} • 
                    ${formatDate(doc.upload_date)}
                </div>
            </div>
            <div class="doc-actions">
                <button class="btn btn-delete" onclick="deleteDocument('${doc.document_id}')">
                    Delete
                </button>
            </div>
        </div>
    `).join('');

    documentsContainer.innerHTML = html;
}

async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Delete failed');
        }

        showToast('success', 'Document deleted successfully');
        loadDocuments();

    } catch (error) {
        console.error('Delete error:', error);
        showToast('error', 'Failed to delete document');
    } finally {
        showLoading(false);
    }
}

// ========================================
// Question Answering
// ========================================

function updateCharCount() {
    const count = questionInput.value.length;
    charCount.textContent = `${count}/500`;

    if (count > 450) {
        charCount.style.color = 'var(--warning)';
    } else {
        charCount.style.color = 'var(--text-muted)';
    }
}

async function handleQuestionSubmit(e) {
    e.preventDefault();

    const question = questionInput.value.trim();

    if (!question) {
        showToast('warning', 'Please enter a question');
        return;
    }

    if (uploadedDocuments.length === 0) {
        showToast('warning', 'Please upload documents first');
        return;
    }

    showLoading(true);
    answerContainer.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                top_k: 5
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Question failed');
        }

        const data = await response.json();
        displayAnswer(data);

    } catch (error) {
        console.error('Question error:', error);
        showToast('error', `Failed to get answer: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function displayAnswer(data) {
    // Display answer
    answerContent.textContent = data.answer;

    // Display sources
    if (data.sources && data.sources.length > 0) {
        const sourcesHtml = data.sources.map((source, index) => `
            <div class="source-item">
                <div class="source-header">
                    <span class="source-doc">${source.document}</span>
                    <span class="source-score">Similarity: ${(source.similarity_score * 100).toFixed(1)}%</span>
                </div>
                <div class="source-content">"${source.content}"</div>
            </div>
        `).join('');

        sourcesList.innerHTML = sourcesHtml;
    } else {
        sourcesList.innerHTML = '<p class="empty-state">No sources found</p>';
    }

    // Display metadata
    answerMeta.innerHTML = `⏱️ Processed in ${data.processing_time}s`;

    // Show answer container
    answerContainer.style.display = 'block';

    // Smooth scroll to answer
    answerContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ========================================
// UI Helpers
// ========================================

function showLoading(show) {
    if (show) {
        loadingOverlay.classList.add('active');
    } else {
        loadingOverlay.classList.remove('active');
    }
}

function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;

    toastContainer.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;

    return date.toLocaleDateString();
}

// ========================================
// Keyboard Shortcuts
// ========================================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to submit question
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && document.activeElement === questionInput) {
        e.preventDefault();
        questionForm.dispatchEvent(new Event('submit'));
    }
});
