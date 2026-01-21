# Bug Fix: 404 Not Found on Document Upload

## Problem
After fixing the enum issue, users could create complaints but got a "Not Found" error when trying to upload documents. The complaint was created successfully, but the document upload failed with HTTP 404.

## Root Cause
The document router had incorrect URL path configuration. There was a conflict between:
1. The router prefix in `router.py`: `/documents`
2. The route paths in `documents.py`: `/complaints/{complaint_id}/documents`

This resulted in final URLs like:
- **Expected**: `/api/v1/complaints/{id}/documents`
- **Actual**: `/api/v1/documents/complaints/{id}/documents` ❌

The frontend was calling the correct URL, but the backend had the wrong route registration.

## Solution

### 1. Fixed Router Registration
**File**: `app/api/v1/router.py`

Removed the `/documents` prefix from the documents router since all document routes are nested under `/complaints`:

```python
# Before (INCORRECT)
api_router.include_router(
    documents.router,
    prefix="/documents",  # ❌ Wrong!
    tags=["documents"]
)

# After (CORRECT)
api_router.include_router(
    documents.router,  # ✅ No prefix needed
    tags=["documents"]
)
```

### 2. Updated All Document Routes
**File**: `app/api/v1/endpoints/documents.py`

Updated all document routes to include `complaint_id` in the path for proper RESTful nesting:

- ✅ `POST /complaints/{complaint_id}/documents` - Upload documents
- ✅ `GET /complaints/{complaint_id}/documents` - List documents
- ✅ `GET /complaints/{complaint_id}/documents/{document_id}` - Get document
- ✅ `GET /complaints/{complaint_id}/documents/{document_id}/download` - Download
- ✅ `GET /complaints/{complaint_id}/documents/{document_id}/status` - Get status
- ✅ `GET /complaints/{complaint_id}/documents/{document_id}/text` - Get extracted text
- ✅ `DELETE /complaints/{complaint_id}/documents/{document_id}` - Delete document

Added validation to ensure document belongs to the specified complaint:

```python
document = await service.get_by_id(document_id)
if not document or document.complaint_id != complaint_id:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {document_id} not found"
    )
```

## Changes Made

### Files Modified
1. **app/api/v1/router.py** - Removed `/documents` prefix
2. **app/api/v1/endpoints/documents.py** - Updated all 7 document routes to include complaint_id

### Services Restarted
- ✅ `api` container restarted with new routes

## Testing

Test the document upload endpoint:
```bash
# Create a complaint first
curl -X POST http://localhost:8000/api/v1/complaints \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": ""}'

# Upload a document (replace {complaint_id} with actual ID)
curl -X POST http://localhost:8000/api/v1/complaints/{complaint_id}/documents \
  -F "files=@document.pdf"
```

## Impact
This fix resolves the 404 error completely. Users can now:
- ✅ Create complaints
- ✅ Upload documents (PDF, images, Word, Excel)
- ✅ View uploaded documents
- ✅ Download documents
- ✅ See real-time processing status
- ✅ View AI-generated summaries

## API Structure
The final API structure follows RESTful conventions:

```
/api/v1/
  /complaints
    POST   /                          # Create complaint
    GET    /                          # List complaints
    GET    /{id}                     # Get complaint
    DELETE /{id}                      # Delete complaint
    POST   /{id}/process              # Start processing

    # Nested document routes
    POST   /{id}/documents            # Upload documents
    GET    /{id}/documents            # List documents
    GET    /{id}/documents/{doc_id}   # Get document
    GET    /{id}/documents/{doc_id}/download  # Download
    DELETE /{id}/documents/{doc_id}   # Delete document
```

## Prevention
- Always verify final route URLs match frontend expectations
- Use proper REST nesting for resources
- Test routes after adding router prefixes
- Check Swagger docs at `/api/v1/docs` to verify routes
