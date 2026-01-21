# Technical Documentation

Detailed technical reference for the Complaint Intelligence Platform.

## Table of Contents
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Processing Pipeline](#processing-pipeline)
- [Document Processors](#document-processors)
- [LLM Integration](#llm-integration)
- [Celery Tasks](#celery-tasks)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  - Drag & Drop Upload  - Real-time Polling  - Summary Display   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────┴────────────────────────────────────┐
│                      FastAPI Backend                             │
│  - Async Endpoints  - File Upload  - Business Logic             │
└──────┬────────────────────────────────────────┬─────────────────┘
       │                                        │
       │ Async I/O                             │ Task Queue
       ▼                                        ▼
┌─────────────────┐                    ┌──────────────────────────┐
│  PostgreSQL DB  │                    │   Celery Workers (3x)    │
│  - Complaints   │◄───────────────────│  - Document Processing   │
│  - Documents    │   Sync I/O         │  - Text Extraction       │
│  - Summaries    │                    │  - AI Summarization      │
└─────────────────┘                    └──────────┬───────────────┘
                                                  │
                                                  │ Chord/Group
                                                  ▼
                                          ┌───────────────┐
                                          │  OpenAI API   │
                                          │  GPT-4o-mini  │
                                          └───────────────┘
```

### Tech Stack Details

**Backend:**
- **FastAPI 0.110+** - ASGI web framework with automatic OpenAPI docs
- **SQLAlchemy 2.0+** - Async ORM with PostgreSQL asyncpg driver
- **Celery 5.3+** - Distributed task queue with Redis broker
- **Redis 7+** - Message broker and result backend
- **OpenAI Python SDK** - GPT API client
- **Tesseract 5.3+** - OCR engine
- **PyMuPDF (fitz)** - PDF parsing
- **python-docx** - Word document parser
- **pandas + openpyxl** - Excel processing
- **Pillow** - Image preprocessing
- **Alembic** - Database migration tool

**Frontend:**
- **React 19** - UI library with hooks
- **Vite 7** - Build tool and dev server
- **React Router 7** - Client-side routing
- **Axios** - HTTP client
- **react-markdown** - Markdown renderer
- **Nginx** - Static file server

**Infrastructure:**
- **Docker 20.10+** - Containerization
- **Docker Compose v2** - Multi-container orchestration
- **PostgreSQL 15-alpine** - Relational database
- **Redis 7-alpine** - In-memory data store

## Database Schema

### Tables

**complaints**
```sql
CREATE TABLE complaints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    external_ref VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    overall_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**documents**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    original_filename VARCHAR(500) NOT NULL,
    stored_filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**summaries**
```sql
CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID REFERENCES complaints(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(50) NOT NULL,  -- 'document' or 'overall'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_refs CHECK (
        (complaint_id IS NOT NULL AND document_id IS NULL) OR
        (complaint_id IS NULL AND document_id IS NOT NULL)
    )
);
```

### Status Flow

**Complaint Status:**
`pending` → `processing` → `summarizing` → `pending_action` → `in_progress` → `resolved`/`completed`

**Document Status:**
`pending` → `extracting` → `extracted` → `summarizing` → `completed`

### Indexes

```sql
CREATE INDEX idx_complaints_status ON complaints(status);
CREATE INDEX idx_complaints_created_at ON complaints(created_at DESC);
CREATE INDEX idx_documents_complaint_id ON documents(complaint_id);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_summaries_complaint_id ON summaries(complaint_id);
CREATE INDEX idx_summaries_document_id ON summaries(document_id);
```

## API Reference

### Base URL
`http://localhost:8000/api/v1`

### Complaints Endpoints

#### List Complaints
```http
GET /complaints?page=1&page_size=50
```

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string",
      "status": "pending_action",
      "documents_count": 3,
      "created_at": "2026-01-21T10:00:00",
      "updated_at": "2026-01-21T10:05:00"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

#### Create Complaint
```http
POST /complaints
Content-Type: application/json

{
  "title": "Product Quality Issue",
  "description": "Customer reports defective product",
  "external_ref": "TICKET-12345"
}
```

#### Get Complaint Details
```http
GET /complaints/{complaint_id}
```

#### Start Processing
```http
POST /complaints/{complaint_id}/process
```

### Documents Endpoints

#### Upload Documents
```http
POST /complaints/{complaint_id}/documents
Content-Type: multipart/form-data

files: [File, File, ...]
```

#### Download Document
```http
GET /complaints/{complaint_id}/documents/{document_id}/download
```

#### Get Extracted Text
```http
GET /complaints/{complaint_id}/documents/{document_id}/text
```

### Summaries Endpoints

#### Get Overall Summary
```http
GET /complaints/{complaint_id}/summary
```

Response:
```json
{
  "category": "Product Defect",
  "sentiment": "negative",
  "severity": "high",
  "responsible_team": "Quality Control",
  "executive_summary": "...",
  "key_facts": [
    {
      "fact": "Product delivered damaged",
      "source": "complaint_letter.pdf",
      "context": "Box arrived with visible dents..."
    }
  ],
  "timeline": [...],
  "core_issues": [...],
  "parties_involved": [...],
  "evidence": [...],
  "recommended_actions": [...]
}
```

#### Regenerate Summary
```http
POST /complaints/{complaint_id}/regenerate-summary
```

## Processing Pipeline

### Async Processing Flow

```
User uploads documents → POST /complaints/{id}/documents
                              ↓
                      Files saved to storage
                              ↓
User clicks "Process" → POST /complaints/{id}/process
                              ↓
                      FastAPI endpoint returns immediately
                              ↓
                      Celery task: process_complaint_documents
                              ↓
        ┌────────────────────────────────────────────┐
        │ Celery Chord (parallel execution + callback)│
        └────────────────────────────────────────────┘
                              ↓
        ┌──────────┬──────────┬──────────┬──────────┐
        │  Doc 1   │  Doc 2   │  Doc 3   │  Doc N   │
        └──────────┴──────────┴──────────┴──────────┘
             │          │          │          │
             │ Chain 1  │ Chain 2  │ Chain 3  │ Chain N
             ↓          ↓          ↓          ↓
        extract     extract     extract     extract
             ↓          ↓          ↓          ↓
        summarize   summarize   summarize   summarize
             │          │          │          │
        └──────────┴──────────┴──────────┴──────────┘
                              ↓
                 All chains complete (group result)
                              ↓
              generate_overall_summary (chord callback)
                              ↓
                    Complaint status → PENDING_ACTION
```

### Task Queues

- **documents** queue: Document extraction tasks
- **summaries** queue: AI summarization tasks
- **default** queue: Fallback for other tasks

### Error Handling

- Tasks have `max_retries=3` with exponential backoff
- Failed tasks update status to `FAILED` with error message
- Database transactions ensure consistency

## Document Processors

### Base Processor Interface

```python
class BaseDocumentProcessor(ABC):
    @abstractmethod
    def extract_text(self, file_path: str) -> ExtractionResult:
        pass
```

### PDF Processor

**Class:** `PDFProcessor`
**Strategy:** Direct text extraction, OCR fallback for scanned pages

```python
# Try direct text extraction first
pages = doc.load_page(page_num)
text = page.get_text()

# If page is image/scanned, use OCR
if len(text.strip()) < 50:
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(img)
```

### Image Processor

**Class:** `ImageProcessor`
**Preprocessing Pipeline:**
1. Grayscale conversion
2. Contrast enhancement (CLAHE)
3. Sharpening filter
4. Binary thresholding
5. Tesseract OCR with `--psm 3` (auto page segmentation)

### Word Processor

**Class:** `DocxProcessor`
**Extracts:**
- Paragraphs
- Tables (converted to readable text format)

### Excel Processor

**Class:** `ExcelProcessor`
**Extracts:**
- All sheets as DataFrames
- Converts to formatted text with sheet names

## LLM Integration

### OpenAI Client

**File:** `app/llm/openai_client.py`

**Features:**
- Lazy initialization (sync + async clients)
- Configurable model (`OPENAI_MODEL` env var)
- Error handling with retries

**Methods:**
```python
def complete(prompt: str) -> str  # Sync for Celery
async def complete_async(prompt: str) -> str  # Async for FastAPI
```

### Summarizer

**File:** `app/llm/summarizer.py`

**Document Summary:**
```python
summary = {
    "overview": "...",
    "key_points": [...],
    "dates": [...],
    "parties": [...],
    "issues": [...]
}
```

**Overall Summary (JSON):**
```python
summary = {
    "category": "string",
    "sentiment": "negative|neutral|critical",
    "severity": "low|medium|high|critical",
    "responsible_team": "string",
    "executive_summary": "string",
    "key_facts": [{"fact": "", "source": "", "context": ""}],
    "timeline": [{"event": "", "source": "", "context": ""}],
    "core_issues": [{"issue": "", "source": "", "context": ""}],
    "parties_involved": ["string"],
    "evidence": ["string"],
    "recommended_actions": ["string"]
}
```

### Content Truncation

Max content length: **15,000 characters** (prevents token limit errors)

### Prompts

**Location:** `app/llm/prompts.py`

Variables available:
- `{filename}` - Document name
- `{file_type}` - Document type
- `{content}` - Extracted text
- `{complaint_title}` - Complaint title
- `{complaint_description}` - Description
- `{document_summaries}` - Combined doc summaries
- `{document_count}` - Number of docs

## Celery Tasks

### Task Configuration

**Broker:** Redis (`redis://redis:6379/1`)
**Result Backend:** Redis (`redis://redis:6379/2`)
**Serializer:** JSON
**Task Track Started:** True
**Task Time Limit:** 300 seconds (5 minutes)

### Key Tasks

**process_document_task**
```python
@celery_app.task(name="process_document", bind=True, max_retries=3)
def process_document_task(self, document_id: str):
    # 1. Load document from DB
    # 2. Select appropriate processor
    # 3. Extract text
    # 4. Update status to 'extracted'
    # 5. Return extracted text
```

**summarize_document_task**
```python
@celery_app.task(name="summarize_document", bind=True, max_retries=3)
def summarize_document_task(self, extracted_text: str, document_id: str):
    # 1. Generate summary with OpenAI
    # 2. Store summary in DB
    # 3. Update document status to 'completed'
```

**process_complaint_documents**
```python
@celery_app.task(name="process_complaint_documents")
def process_complaint_documents(complaint_id: str):
    # 1. Get all documents for complaint
    # 2. Create chain for each doc: extract → summarize
    # 3. Group chains in parallel
    # 4. Chord with generate_overall_summary callback
```

**generate_overall_summary_task**
```python
@celery_app.task(name="generate_overall_summary")
def generate_overall_summary_task(results: list, complaint_id: str):
    # 1. Combine all document summaries
    # 2. Generate overall JSON summary
    # 3. Store in DB
    # 4. Update complaint status to 'pending_action'
```

## Development

### Local Development (without Docker)

**Backend:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://localhost/complaints"
export OPENAI_API_KEY="sk-..."

# Run migrations
alembic upgrade head

# Start FastAPI
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker -l info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

### Database Migrations

**Create Migration:**
```bash
docker-compose exec api alembic revision --autogenerate -m "Add new column"
```

**Apply Migrations:**
```bash
docker-compose exec api alembic upgrade head
```

**Rollback:**
```bash
docker-compose exec api alembic downgrade -1
```

**View Current Version:**
```bash
docker-compose exec api alembic current
```

### Adding New Document Type

1. **Create Processor:**
```python
# app/document_processors/my_processor.py
class MyProcessor(BaseDocumentProcessor):
    def extract_text(self, file_path: str) -> ExtractionResult:
        # Implementation
        pass
```

2. **Add to Factory:**
```python
# app/document_processors/__init__.py
ProcessorFactory._processors = {
    'mytype': MyProcessor,
    ...
}
```

3. **Update Enum:**
```python
# app/db/models/document.py
class DocumentType(str, Enum):
    MYTYPE = "mytype"
```

4. **Add MIME Type:**
```python
# app/services/document_service.py
MIME_TYPE_MAPPING = {
    'application/mytype': 'mytype',
    ...
}
```

## Testing

### Run Tests

```bash
# All tests
docker-compose exec api pytest

# Specific test file
docker-compose exec api pytest tests/unit/test_document_processors.py

# With coverage
docker-compose exec api pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Structure

```
tests/
├── unit/
│   ├── test_document_processors.py
│   ├── test_summarizer.py
│   └── test_services.py
├── integration/
│   ├── test_api_complaints.py
│   ├── test_api_documents.py
│   └── test_celery_tasks.py
├── fixtures/
│   ├── sample.pdf
│   ├── sample.png
│   └── sample.docx
└── conftest.py
```

### Writing Tests

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_complaint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/complaints",
            json={"title": "Test", "description": "Test"}
        )
        assert response.status_code == 201
```

## Deployment

### Production Checklist

- [ ] Set strong PostgreSQL password
- [ ] Use production OpenAI API key
- [ ] Set `DEBUG=False`
- [ ] Configure CORS for production domain
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up monitoring (Sentry, Datadog, etc.)
- [ ] Configure log aggregation
- [ ] Set resource limits in docker-compose
- [ ] Enable Redis persistence
- [ ] Set up health check endpoints

### Environment Variables (Production)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/complaints
DATABASE_URL_SYNC=postgresql://user:password@host:5432/complaints

# Security
SECRET_KEY=generate-secure-random-key
ALLOWED_HOSTS=yourdomain.com

# OpenAI
OPENAI_API_KEY=sk-prod-key
OPENAI_MODEL=gpt-4o

# Monitoring
SENTRY_DSN=https://...
```

### Docker Compose Production

```yaml
services:
  api:
    image: your-registry/complaint-processor-api:latest
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  worker:
    image: your-registry/complaint-processor-worker:latest
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_db(),
        "redis": await check_redis()
    }
```

---

For more information, see the main [README.md](./README.md) or open an issue on GitHub.
