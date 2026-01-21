# Complaint Intelligence Platform

An AI-powered complaint processing system that automatically extracts, analyzes, and summarizes complaint documents using advanced OCR and Large Language Models (LLMs). Built with FastAPI, React, and Celery for scalable async processing.

## 🌟 Features

### Core Capabilities
- **📄 Multi-Format Document Processing**: Supports PDF, images (PNG, JPG, TIFF), Word documents (DOC/DOCX), and Excel spreadsheets (XLS/XLSX)
- **🔍 Advanced OCR**: Automatic text extraction using Tesseract OCR with intelligent preprocessing
- **🤖 AI-Powered Summarization**: OpenAI GPT-based analysis generating structured insights
- **⚡ Async Processing**: Celery-based parallel document processing for optimal performance
- **📊 Real-Time Status Updates**: Live progress tracking with polling mechanism
- **💾 Persistent Storage**: PostgreSQL database with async SQLAlchemy ORM

### AI Summary Features
- **📋 Structured JSON Output**: Category, sentiment, severity, and responsible team classification
- **📌 Collapsible Sections**: Executive summary, key facts, timeline, core issues, parties involved, evidence, and recommended actions
- **🎨 Markdown Rendering**: Beautiful formatting with support for headings, lists, and emphasis
- **🏷️ Smart Categorization**: Automatic complaint categorization (Billing, Product Defect, Service Issue, etc.)
- **📈 Severity Assessment**: Four-level severity rating (Low, Medium, High, Critical)
- **💭 Sentiment Analysis**: Tracks complaint sentiment (Negative, Neutral, Critical)
- **👥 Team Assignment**: AI suggests responsible team based on complaint content

### Workflow Management
- **🔄 Status Tracking**: 8 distinct workflow states from pending to completed
- **⏳ Pending Action State**: Complaints marked for team action after AI processing
- **🔁 Regeneration**: Ability to regenerate summaries with updated prompts
- **📥 Document Download**: Download original uploaded documents
- **🗑️ Bulk Operations**: Delete complaints and associated documents

## 🏗️ Architecture

### Tech Stack

**Backend:**
- **FastAPI** - Modern, high-performance web framework
- **SQLAlchemy** - Async ORM with PostgreSQL
- **Celery** - Distributed task queue for async processing
- **Redis** - Message broker and result backend
- **OpenAI API** - GPT-based text summarization
- **Tesseract OCR** - Text extraction from images
- **PyMuPDF** - PDF text extraction
- **python-docx** - Word document processing
- **pandas** - Excel data extraction

**Frontend:**
- **React 19** - Modern UI library
- **Vite 7** - Fast build tool and dev server
- **React Router 7** - Client-side routing
- **Axios** - HTTP client
- **react-markdown** - Markdown rendering
- **Nginx** - Production web server

**Infrastructure:**
- **Docker & Docker Compose** - Containerization
- **PostgreSQL 15** - Relational database
- **Redis 7** - In-memory data store
- **Alembic** - Database migrations

### System Architecture

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

### Processing Pipeline

```
POST /complaints/{id}/process
    ↓
┌────────────────────────────────────────────────────────────┐
│          Celery Chord (Parallel + Callback)                │
└────────────────────────────────────────────────────────────┘
    ↓
┌───────────────┬───────────────┬───────────────┐
│   Document 1  │   Document 2  │   Document N  │
│   Chain:      │   Chain:      │   Chain:      │
│   extract →   │   extract →   │   extract →   │
│   summarize   │   summarize   │   summarize   │
└───────────────┴───────────────┴───────────────┘
    ↓ (all parallel chains complete)
generate_overall_summary (chord callback)
    ↓
Complaint status → PENDING_ACTION
```

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** 20.10+ and Docker Compose v2.0+
- **OpenAI API Key** - Get one from [platform.openai.com](https://platform.openai.com)
- **8GB RAM** minimum (for document processing)
- **Modern Browser** (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/aswithabukka/Complaint-Intelligence-Platform.git
cd Complaint-Intelligence-Platform
```

2. **Configure environment:**
```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

3. **Start all services:**
```bash
docker-compose up --build
```

This will start 6 containers:
- **API** (FastAPI) - http://localhost:8000
- **Frontend** (React/Nginx) - http://localhost:3000
- **Worker** (Celery) - Background processing
- **Flower** (Celery Monitoring) - http://localhost:5555
- **PostgreSQL** - Port 5432
- **Redis** - Port 6379

4. **Run database migrations:**
```bash
docker-compose exec api alembic upgrade head
```

5. **Access the application:**
- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/v1/docs
- **Flower Dashboard**: http://localhost:5555

## 📖 Usage Guide

### Creating a Complaint

1. Navigate to http://localhost:3000
2. Click **"+ New Complaint"**
3. Enter a title and optional description
4. Drag & drop documents or click to upload
   - Supported: PDF, PNG, JPG, TIFF, DOC, DOCX, XLS, XLSX
   - Max size: 50MB per file
5. Click **"Create & Upload"**
6. Click **"Start Processing"** to trigger AI analysis

### Monitoring Progress

The complaint detail page shows real-time status:
- **PENDING** - Initial state
- **PROCESSING** - Documents being extracted
- **SUMMARIZING** - AI generating summary
- **PENDING ACTION** ⚠️ - Summary ready, awaiting team action
- **IN PROGRESS** - Team is working on it
- **RESOLVED** ✅ - Issue resolved
- **COMPLETED** ✅ - Fully closed
- **FAILED** ❌ - Processing error

### Understanding AI Summaries

Each summary includes:

**Metadata Header:**
- **Category**: Billing, Product Defect, Service Issue, etc.
- **Sentiment**: Negative, Neutral, or Critical
- **Severity**: Low, Medium, High, or Critical
- **Responsible Team**: Suggested department

**Collapsible Sections:**
- **Executive Summary**: 2-3 sentence overview
- **Key Facts**: Bullet points of important information
- **Timeline**: Chronological sequence of events
- **Core Issues**: Primary complaints identified
- **Parties Involved**: People and organizations mentioned
- **Evidence**: Supporting documentation referenced
- **Recommended Actions**: Next steps (highlighted)

## 🔧 Configuration

### Environment Variables

Create a `.env` file with these required settings:

```env
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini

# Database URLs
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/complaints
DATABASE_URL_SYNC=postgresql://postgres:postgres@db:5432/complaints

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=52428800  # 50MB

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Complaint Processor
```

### Modifying AI Prompts

Edit `app/llm/prompts.py` to customize:
- Summary structure and formatting
- Category classifications
- Severity criteria
- Team assignment rules

After modifying prompts:
```bash
docker-compose restart worker api
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/unit/test_document_processors.py

# Run with coverage
docker-compose exec api pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback one migration
docker-compose exec api alembic downgrade -1
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f frontend
```

### Development Workflow

For backend development (hot reload enabled):
```bash
# Edit files in app/
# Changes auto-reload in FastAPI
docker-compose restart api worker
```

For frontend development:
```bash
# Option 1: Rebuild container
docker-compose up -d --build frontend

# Option 2: Run locally (faster)
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

## 📁 Project Structure

```
complaint-processor/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/          # API route handlers
│   │       │   ├── complaints.py
│   │       │   ├── documents.py
│   │       │   └── summaries.py
│   │       ├── schemas/            # Pydantic models
│   │       └── router.py           # Route registration
│   ├── core/
│   │   └── config.py               # Settings & configuration
│   ├── db/
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── complaint.py
│   │   │   ├── document.py
│   │   │   └── summary.py
│   │   └── session.py              # DB connection
│   ├── document_processors/        # File type processors
│   │   ├── pdf_processor.py
│   │   ├── image_processor.py
│   │   ├── docx_processor.py
│   │   └── excel_processor.py
│   ├── llm/
│   │   ├── openai_client.py        # OpenAI integration
│   │   ├── summarizer.py           # Summary generation
│   │   └── prompts.py              # LLM prompts
│   ├── services/                   # Business logic
│   │   ├── complaint_service.py
│   │   ├── document_service.py
│   │   ├── summary_service.py
│   │   └── storage_service.py
│   ├── workers/
│   │   ├── celery_app.py           # Celery configuration
│   │   └── tasks/
│   │       ├── document_tasks.py
│   │       └── summary_tasks.py
│   └── main.py                     # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SummaryCard.jsx     # AI summary display
│   │   │   └── SummaryCard.css
│   │   ├── hooks/
│   │   │   └── useComplaintPolling.js
│   │   ├── pages/
│   │   │   ├── ComplaintList.jsx
│   │   │   ├── CreateComplaint.jsx
│   │   │   └── ComplaintDetail.jsx
│   │   ├── services/
│   │   │   └── api.js              # API client
│   │   └── App.jsx
│   ├── Dockerfile                  # Multi-stage build
│   └── nginx.conf
├── alembic/                        # Database migrations
├── docker/
│   ├── Dockerfile                  # API image
│   └── Dockerfile.worker           # Worker image
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 🔌 API Reference

### Complaints

```http
GET    /api/v1/complaints              # List all complaints
POST   /api/v1/complaints              # Create new complaint
GET    /api/v1/complaints/{id}         # Get complaint details
DELETE /api/v1/complaints/{id}         # Delete complaint
POST   /api/v1/complaints/{id}/process # Start processing
```

### Documents

```http
POST   /api/v1/complaints/{id}/documents              # Upload documents
GET    /api/v1/complaints/{id}/documents              # List documents
GET    /api/v1/complaints/{id}/documents/{doc_id}     # Get document
DELETE /api/v1/complaints/{id}/documents/{doc_id}     # Delete document
GET    /api/v1/complaints/{id}/documents/{doc_id}/download  # Download
GET    /api/v1/complaints/{id}/documents/{doc_id}/status    # Get status
GET    /api/v1/complaints/{id}/documents/{doc_id}/text      # Get extracted text
```

### Summaries

```http
GET    /api/v1/complaints/{id}/summary                # Get overall summary
POST   /api/v1/complaints/{id}/regenerate-summary     # Regenerate summaries
```

Full API documentation: http://localhost:8000/api/v1/docs

## 🐛 Troubleshooting

### Common Issues

**1. "Network Error" when creating complaint**
- Ensure OpenAI API key is set in `.env`
- Check API container logs: `docker-compose logs api`
- Verify database migration ran: `docker-compose exec api alembic current`

**2. Documents stuck in "Processing" state**
- Check worker logs: `docker-compose logs worker`
- Verify Redis is running: `docker-compose ps redis`
- Restart worker: `docker-compose restart worker`

**3. "Not Found" error on document upload**
- Check API logs for routing errors
- Ensure API container restarted after code changes
- Verify route configuration in `app/api/v1/router.py`

**4. Frontend not showing summaries**
- Check browser console for errors
- Verify API is returning data: `curl http://localhost:8000/api/v1/complaints`
- Clear browser cache and reload

**5. Database connection errors**
- Wait for PostgreSQL to be healthy: `docker-compose ps db`
- Check database credentials in `.env`
- Recreate database: `docker-compose down -v && docker-compose up -d`

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `docker-compose exec api pytest`
5. Commit with clear messages: `git commit -m "Add: feature description"`
6. Push to your fork: `git push origin feature/your-feature`
7. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **JavaScript**: ESLint with React best practices
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **OpenAI** - GPT models for summarization
- **Tesseract OCR** - Open-source text extraction
- **FastAPI** - Modern Python web framework
- **React Team** - UI library and ecosystem
- **Celery** - Distributed task queue
- **PostgreSQL** - Robust database system

## 🗺️ Roadmap

- [ ] Multi-tenant support
- [ ] Email integration for complaint submission
- [ ] Advanced search and filtering
- [ ] Export to PDF/Excel
- [ ] Dashboard analytics
- [ ] Mobile app (React Native)
- [ ] Multiple LLM providers (Claude, Llama)
- [ ] Custom workflow automation
- [ ] Webhook notifications
- [ ] API rate limiting

---

**Built with ❤️ using FastAPI, React, and AI**

⭐ Star this repository if you find it helpful!
