# Testing Guide - Phase 1 Implementation

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Frontend server running (usually `http://localhost:5173`)
3. API keys configured in `.env` file in the root directory
4. Test PDF or TXT file ready to upload

## Step-by-Step Testing

### 1. Start the Backend Server

**Important: You must run uvicorn from the `backend/` directory!**

```bash
cd backend
pip install -r requirements.txt  # If not already installed

# Option 1: Using python -m (Recommended - more reliable)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using uvicorn directly (if it's in your PATH)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Using the startup script (Windows)
start_server.bat

# Option 4: Using the startup script (Linux/Mac)
chmod +x start_server.sh
./start_server.sh
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Start the Frontend Server

```bash
cd frontend
npm install  # If not already installed
npm run dev
```

### 3. Test File Upload via Frontend

1. Open your browser and navigate to `http://localhost:5173`
2. Drag and drop a PDF or TXT file, or click to select a file
3. Click "Generate Study Path" button
4. Observe:
   - Loading spinner appears
   - Success message appears
   - Automatic navigation to study path page

### 4. Test File Upload via API Directly

You can also test the API directly using curl or Postman:

```bash
curl -X POST "http://localhost:8000/api/upload-material" \
  -F "file=@/path/to/your/test.pdf"
```

Or using Python:

```python
import requests

url = "http://localhost:8000/api/upload-material"
files = {"file": open("test.pdf", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

### 5. Verify Response Structure

A successful response should look like:

```json
{
  "message": "File uploaded and processed successfully",
  "file_id": "uuid-here",
  "filename": "test.pdf",
  "saved_path": "uploads/uuid-here.pdf",
  "uploaded_at": "2024-01-01T00:00:00",
  "text_extracted": true,
  "text_length": 1234,
  "supermemory_ingested": true,
  "memory_id": "memory-id-here",
  "topics_extracted": true,
  "topics": "Extracted topics text..."
}
```

## Verifying Supermemory Integration

### Method 1: Check API Response

Look for these fields in the response:
- `supermemory_ingested`: Should be `true` if successful
- `memory_id`: Should contain a memory ID if successful
- `supermemory_error`: Will contain error message if failed

### Method 2: Check Supermemory Dashboard

1. **Log in to Supermemory Dashboard**
   - Go to [supermemory.ai](https://supermemory.ai)
   - Log in to your account
   - Navigate to your dashboard or memories section

2. **Look for your uploaded document**
   - Check for a memory with the filename you uploaded
   - Verify the metadata (file_id, content_type, uploaded_at)
   - Check the container_tag: should be "uploaded-documents"

3. **Query the memory**
   - Use Supermemory's query interface
   - Search for content from your uploaded document
   - Verify that the content is retrievable

### Method 3: Test Supermemory Query via API

You can test if Supermemory is working by making a direct query:

```python
import asyncio
from services.supermemory_service import SupermemoryService

async def test_query():
    service = SupermemoryService()
    # Query for content from your uploaded document
    result = await service.query(
        query="What are the main topics in this document?",
        container_tag="uploaded-documents",
        top_k=5
    )
    print(result)

asyncio.run(test_query())
```

### Method 4: Check Backend Logs

When you upload a file, check the backend console for:
- Success messages from Supermemory API
- Any error messages
- Memory ID in the response

## Verifying Claude Integration

### Method 1: Check API Response

Look for these fields in the response:
- `topics_extracted`: Should be `true` if successful
- `topics`: Should contain extracted topics text
- `topics_error`: Will contain error message if failed

### Method 2: Check Topics Quality

1. Review the extracted topics in the response
2. Verify they make sense for your document
3. Check if topics are ordered by learning importance
4. Verify subtopics are included if applicable

### Method 3: Test Claude Service Directly

```python
import asyncio
from services.claude_service import ClaudeService

async def test_claude():
    service = ClaudeService()
    result = await service.extract_topics(
        document_content="Your test document content here..."
    )
    print(result["topics_text"])

asyncio.run(test_claude())
```

## Troubleshooting

### Supermemory Not Working

**Symptoms:**
- `supermemory_ingested: false`
- `supermemory_error` in response

**Solutions:**
1. Verify `SUPERMEMORY_API_KEY` is correct in `.env` (root directory)
2. Check Supermemory API documentation for correct endpoint structure
3. Verify your Supermemory account has sufficient credits
4. Check network connectivity
5. Review backend logs for detailed error messages

### Claude Not Working

**Symptoms:**
- `topics_extracted: false`
- `topics_error` in response

**Solutions:**
1. Verify `ANTHROPIC_API_KEY` is correct in `.env` (root directory)
2. Check Anthropic API documentation for any changes
3. Verify your Anthropic account has sufficient credits
4. Check network connectivity
5. Review backend logs for detailed error messages

### File Upload Fails

**Symptoms:**
- Error message in frontend
- 400 or 500 error in response

**Solutions:**
1. Verify file type is PDF or TXT
2. Check file size limits
3. Verify backend server is running
4. Check CORS settings if accessing from different origin
5. Review backend logs for detailed error messages

### Text Extraction Fails

**Symptoms:**
- `text_extracted: false`
- Empty text in response

**Solutions:**
1. Verify PDF is not scanned (image-based PDFs won't work)
2. Check if PDF is password protected
3. Verify file contains readable text
4. Try with a different PDF file
5. Check PyPDF2 version compatibility

## Expected Behavior

### Successful Flow

1. ✅ File uploads successfully
2. ✅ File saved to `uploads/` directory
3. ✅ Text extracted from file
4. ✅ Content ingested to Supermemory (if API key configured)
5. ✅ Memory ID returned from Supermemory
6. ✅ Topics extracted using Claude (if API key configured)
7. ✅ Topics text returned in response
8. ✅ Frontend displays success and navigates to study path

### Graceful Degradation

If API keys are missing:
- File upload still works
- Text extraction still works
- Supermemory step is skipped (with message)
- Claude step is skipped (with message)
- Response still returns successfully

## Next Steps After Testing

Once Phase 1 is verified working:
1. Proceed to Phase 2: Topic parsing and study path generation
2. Enhance error handling based on test results
3. Optimize API calls based on response times
4. Add more comprehensive logging

## Additional Resources

- [Supermemory API Documentation](https://supermemory.ai/docs)
- [Anthropic Claude API Documentation](https://docs.anthropic.com)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- Backend logs: Check console output for detailed information


