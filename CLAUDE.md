# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **FastAPI-based complaint processing system** that accepts document uploads (PDF, images, DOC, XLS), extracts text using OCR, and generates AI-powered summaries. The system uses **async processing** via Celery workers to handle document extraction and OpenAI summarization in parallel.

## Essential Commands

### Environment Setup
```bash
# Copy environment template and configure
cp .env.example .env
# MUST set OPENAI_API_KEY in .env before running

# Start all services (API, Worker, DB, Redis, Flower)
docker-compose up --build

# Run database migrations
docker-compose exec api alembic upgrade head
```

### Development
```bash
# Run tests
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/unit/test_document_processors.py

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback migration
docker-compose exec api alembic downgrade -1

# View logs
docker-compose logs -f          # All services
docker-compose logs -f worker   # Celery worker only
docker-compose logs -f api      # API only
```

### Accessing Services
- API Swagger Docs: http://localhost:8000/api/v1/docs
- Flower (Celery monitoring): http://localhost:5555
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Architecture

### Async Processing Pipeline

The core workflow uses **Celery chords** to orchestrate parallel document processing:

```
POST /complaints/{id}/process
    ↓
process_complaint_documents (Celery task)
    ↓
┌────────────────────────────────────────────────────────┐
│  Celery Chord (parallel execution, then combine)       │
└────────────────────────────────────────────────────────┘
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   Document 1    │   Document 2    │   Document N    │
│  chain:         │  chain:         │  chain:         │
│  extract_text → │  extract_text → │  extract_text → │
│  summarize      │  summarize      │  summarize      │
└─────────────────┴─────────────────┴─────────────────┘
    ↓ (all complete)
generate_overall_summary (combines all doc summaries)
    ↓
Complaint status = COMPLETED
```

**Key insight**: Each document is processed by a **chain** (extract → summarize), all chains run in **parallel** via a **group**, and when all complete, the **chord callback** generates the overall summary.

### Database Architecture

**Two database engines** are configured:
- **Async engine** (`AsyncSession`) for FastAPI endpoints
- **Sync engine** (`SessionLocal`) for Celery workers

Both connect to the same PostgreSQL database but use different drivers:
- FastAPI: `postgresql+asyncpg://...`
- Celery: `postgresql://...` (psycopg2)

**Schema**: 3 core tables with cascade deletes:
- `complaints` → `documents` → `summaries`
- `complaints` can also have an `overall` summary linked directly

**Status tracking**:
- Complaint: `pending → processing → summarizing → completed/failed`
- Document: `pending → extracting → extracted → summarizing → completed/failed`

### Document Processing

**ProcessorFactory pattern** routes file types to specialized processors:
- `PDFProcessor`: PyMuPDF for direct text extraction, falls back to Tesseract OCR for scanned pages
- `ImageProcessor`: Tesseract OCR with image preprocessing (grayscale, contrast, sharpening, binarization)
- `DocxProcessor`: python-docx for paragraphs and tables
- `ExcelProcessor`: pandas to convert DataFrames to readable text

Each processor returns an `ExtractionResult` with text, page count, metadata, and warnings.

### Service Layer Pattern

**Services encapsulate business logic** and are instantiated per-request with a DB session:
- `ComplaintService`: CRUD, pagination, status tracking
- `DocumentService`: Upload handling, file type detection, storage abstraction
- `SummaryService`: Retrieves and triggers regeneration of summaries
- `StorageService`: File I/O abstraction (currently local filesystem, extensible to S3/GCS)

**Pattern**: Endpoints → Services → Models. Services return Pydantic schemas, not SQLAlchemy models.

### LLM Integration

**OpenAIClient** uses lazy initialization of sync/async clients:
- `complete()`: Sync method for Celery tasks
- `complete_async()`: Async method for FastAPI endpoints

**Summarizer** handles two types of summaries:
1. **Document summary**: Structured format with Overview, Key Points, Dates, Parties, Issues
2. **Overall summary**: Executive Summary, Combined Facts, Timeline, Core Issues, Evidence, Recommended Actions

Content is **truncated** to `MAX_CONTENT_LENGTH` (15,000 chars) before sending to LLM to avoid token limits.

## Configuration

**Settings** (app/core/config.py) use Pydantic BaseSettings with `.env` file loading:
- Database URLs must be provided for both async and sync engines
- `OPENAI_API_KEY` is required
- `UPLOAD_DIR` defaults to `./uploads` (must be mounted in Docker volumes)

**Docker Compose** runs 5 services:
- `api`: FastAPI with uvicorn --reload for development
- `worker`: Celery worker processing documents and summaries queues
- `flower`: Celery monitoring dashboard
- `db`: PostgreSQL 15 with health check
- `redis`: Redis 7 for Celery broker and result backend

## Adding New Document Types

1. Create new processor in `app/document_processors/` extending `BaseDocumentProcessor`
2. Add file type to `DocumentType` enum in `app/db/models/document.py`
3. Register processor in `ProcessorFactory._processors` dict
4. Add MIME type mapping in `DocumentService.MIME_TYPE_MAPPING`
5. Add file extension to `ALLOWED_EXTENSIONS` in documents endpoint

## Modifying LLM Prompts

Prompts are in `app/llm/prompts.py`:
- `DOCUMENT_SUMMARY_SYSTEM_PROMPT` / `DOCUMENT_SUMMARY_USER_PROMPT`: Individual document summarization
- `OVERALL_SUMMARY_SYSTEM_PROMPT` / `OVERALL_SUMMARY_USER_PROMPT`: Combined complaint summary

User prompts use `.format()` with variables like `{filename}`, `{content}`, `{complaint_title}`, `{document_summaries}`.

## Celery Task Structure

**Task routing**:
- `documents` queue: `process_document_task`, `process_complaint_documents`
- `summaries` queue: `summarize_document_task`, `generate_overall_summary_task`
- `default` queue: fallback

**Task chaining pattern**:
```python
# Single document
chain(
    process_document_task.s(doc_id),
    summarize_document_task.s()
)

# All documents in parallel, then combine
chord(
    group([doc_chains...]),
    generate_overall_summary_task.s(complaint_id)
)
```

**Error handling**: Tasks have `max_retries=3` with exponential backoff. Failed tasks update document status to `FAILED` with error message.

## API Design Patterns

**Endpoints** follow RESTful conventions:
- Use UUID path parameters, not integers
- Return Pydantic schemas, not SQLAlchemy models
- Use `HTTPException` with appropriate status codes
- `ComplaintResponse` includes computed fields like `documents_count`

**Bulk upload** returns both successful and failed uploads in single response.

**File download** uses `FileResponse` with original filename and MIME type.

## Database Migrations with Alembic

Migrations are in `alembic/versions/`. Initial migration (`001_initial_schema.py`) creates all tables and enums.

**Important**: `alembic/env.py` imports all models to enable autogenerate:
```python
from app.db.models import Complaint, Document, Summary
```

When adding new models, import them in `env.py` for autogenerate to detect them.

## Testing Strategy

Tests should be organized as:
- `tests/unit/`: Document processors, services (with mocked DB)
- `tests/integration/`: API endpoints (with test database)
- `tests/fixtures/`: Sample files (sample.pdf, sample.png, etc.)

Use `pytest-asyncio` for async tests and `httpx` for API testing.

1. First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md. 2. The plan should have a list of todo items that you can check off as you complete them
 3. Before you begin working, check in with me and I will verify the plan. 
4. Then, begin working on the todo items, marking them as complete as you go.
 5. Please every step of the way just give me a high level explanation of what changes you made
 6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity. 
7. Finally, add a review section to the todo.md file with a summary of the changes you made and any other relevant information. 
8. DO NOT BE LAZY. NEVER BE LAZY. IF THERE IS A BUG FIND THE ROOT CAUSE AND FIX IT. NO TEMPORARY FIXES. YOU ARE A SENIOR DEVELOPER. NEVER BE LAZY 
9. MAKE ALL FIXES AND CODE CHANGES AS SIMPLE AS HUMANLY POSSIBLE. THEY SHOULD ONLY IMPACT NECESSARY CODE RELEVANT TO THE TASK AND NOTHING ELSE. IT SHOULD IMPACT AS LITTLE CODE AS POSSIBLE. YOUR GOAL IS TO NOT INTRODUCE ANY BUGS. IT'S ALL ABOUT SIMPLICITY 
9.  After completing a task that involves tool use, provide a quick summary of the work you've done 

CRITICAL: When debugging, you MUST trace through the ENTIRE code flow step by step. No assumptions. No shortcuts.