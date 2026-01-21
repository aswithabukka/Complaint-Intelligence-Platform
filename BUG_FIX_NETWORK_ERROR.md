# Bug Fix: Network Error on Complaint Creation

## Problem
When creating a new complaint through the web UI, users encountered a "Network Error" after uploading documents. The complaint creation failed with a database error.

## Root Cause
The SQLAlchemy enum columns were not properly configured to use the enum **values** (lowercase strings) instead of enum **names** (uppercase).

When inserting data, SQLAlchemy was trying to insert `"PENDING"` (the Python enum name) instead of `"pending"` (the database enum value), causing a PostgreSQL error:

```
invalid input value for enum complaintstatus: "PENDING"
```

The PostgreSQL enums were correctly defined with lowercase values:
- `complaintstatus`: 'pending', 'processing', 'summarizing', 'completed', 'failed'
- `processingstatus`: 'pending', 'uploading', 'extracting', 'extracted', 'summarizing', 'completed', 'failed'
- `documenttype`: 'pdf', 'image', 'docx', 'doc', 'xls', 'xlsx'
- `summarytype`: 'document', 'overall'

But the SQLAlchemy models were not configured to use the `.value` property of the enums.

## Solution
Updated all enum column definitions in the SQLAlchemy models to explicitly use enum values:

### Files Changed

1. **app/db/models/complaint.py**
   - Fixed `ComplaintStatus` enum column

2. **app/db/models/document.py**
   - Fixed `DocumentType` enum column
   - Fixed `ProcessingStatus` enum column

3. **app/db/models/summary.py**
   - Fixed `SummaryType` enum column

### Change Pattern
```python
# Before (INCORRECT)
status = Column(
    Enum(ComplaintStatus),
    default=ComplaintStatus.PENDING,
    nullable=False
)

# After (CORRECT)
status = Column(
    Enum(ComplaintStatus, values_callable=lambda x: [e.value for e in x]),
    default=ComplaintStatus.PENDING,
    nullable=False
)
```

The `values_callable` parameter tells SQLAlchemy to extract the actual values ('pending', 'processing', etc.) instead of using the enum names ('PENDING', 'PROCESSING', etc.).

## Testing
After restarting the API and worker services, the complaint creation now works correctly:
- Frontend can successfully create complaints
- Documents upload properly
- Database accepts the enum values
- No more "Network Error"

## Services Restarted
- `api` - Applied model changes
- `worker` - Applied model changes for background processing

## Verification
✅ API responds correctly to GET /api/v1/complaints
✅ No database errors in logs
✅ Enum values match database schema

## Impact
This fix resolves the network error completely. Users can now:
- Create complaints successfully
- Upload documents without errors
- See real-time processing status
- View AI-generated summaries when complete

## Prevention
In the future, when adding new enum columns:
1. Always use `values_callable=lambda x: [e.value for e in x]` parameter
2. Test with actual data before deploying
3. Ensure enum values in database match enum values in Python code (case-sensitive)
