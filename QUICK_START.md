# Quick Start Guide - Phase 1 Implementation

## ✅ What's Been Updated

1. **Switched from OpenAI to Claude (Anthropic)**
   - Updated `backend/services/claude_service.py` to use Claude API
   - Updated `backend/main.py` to use `ClaudeService` instead of `OpenAIService`
   - Updated `backend/requirements.txt` to use `anthropic` instead of `openai`

## 🔑 Required API Keys

Create a `.env` file in the **root directory** (project root, same level as `backend/` and `frontend/`) with these two API keys:

### 1. Supermemory API Key
```env
SUPERMEMORY_API_KEY=your_supermemory_api_key_here
```
**Get it from:** [supermemory.ai](https://supermemory.ai) → API Keys section

### 2. Anthropic (Claude) API Key
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```
**Get it from:** [console.anthropic.com](https://console.anthropic.com) → API Keys section

### Optional
```env
SUPERMEMORY_API_URL=https://api.supermemory.ai
```
(Defaults to the above if not specified. Do not include `/v1` in the URL)

### Complete .env Example
```env
# Supermemory API
SUPERMEMORY_API_KEY=sk-sm-your-key-here
SUPERMEMORY_API_URL=https://api.supermemory.ai

# Anthropic (Claude) API
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## 🧪 How to Test

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Start Backend Server

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Start Frontend Server

```bash
cd frontend
npm install
npm run dev
```

### Step 4: Upload a Test File

1. Open browser to `http://localhost:5173`
2. Upload a PDF or TXT file
3. Click "Generate Study Path"
4. Check the response

### Step 5: Check the API Response

The response will include:
```json
{
  "supermemory_ingested": true,    // ✅ Success if true
  "memory_id": "memory-id-here",   // ✅ Memory ID from Supermemory
  "topics_extracted": true,        // ✅ Success if true
  "topics": "Extracted topics..."  // ✅ Topics from Claude
}
```

## 🔍 How to Verify Supermemory Integration

### Method 1: Check API Response (Easiest)

After uploading a file, check the response:
- `supermemory_ingested: true` = ✅ Success
- `memory_id` = The ID of the memory in Supermemory
- `supermemory_error` = Will show error if something went wrong

### Method 2: Check Supermemory Dashboard

1. **Log in to Supermemory**
   - Go to [supermemory.ai](https://supermemory.ai)
   - Log in to your account

2. **Navigate to Your Memories/Documents**
   - Look for a section like "Memories", "Documents", or "Uploads"
   - Search for your uploaded filename
   - Check the metadata (file_id, uploaded_at, etc.)

3. **Verify the Content**
   - Open the memory/document
   - Verify the text content matches your uploaded PDF
   - Check that it's in the "uploaded-documents" container

4. **Test Query (if available)**
   - Use Supermemory's query/search feature
   - Search for content from your uploaded document
   - Verify results are returned

### Method 3: Test via API (Advanced)

You can test Supermemory directly:

```python
import asyncio
import os
from dotenv import load_dotenv
from services.supermemory_service import SupermemoryService

load_dotenv()

async def test_supermemory():
    service = SupermemoryService()
    
    # Test query
    result = await service.query(
        query="What topics are in this document?",
        container_tag="uploaded-documents",
        top_k=5
    )
    print("Query result:", result)

asyncio.run(test_supermemory())
```

### Method 4: Check Backend Logs

When you upload a file, watch the backend console:
- Look for success messages
- Check for any error messages
- Note the memory_id if successful

## 🐛 Troubleshooting

### Supermemory Not Working?

**Check:**
1. ✅ Is `SUPERMEMORY_API_KEY` in your `.env` file?
2. ✅ Is the API key correct? (No extra spaces)
3. ✅ Does your Supermemory account have credits?
4. ✅ Check backend logs for error messages
5. ✅ Verify Supermemory API endpoint is correct

**Common Errors:**
- `SUPERMEMORY_API_KEY not configured` → Add key to .env
- `401 Unauthorized` → Invalid API key
- `403 Forbidden` → Check account permissions
- `404 Not Found` → Check API endpoint URL

### Claude Not Working?

**Check:**
1. ✅ Is `ANTHROPIC_API_KEY` in your `.env` file?
2. ✅ Is the API key correct? (No extra spaces)
3. ✅ Does your Anthropic account have credits?
4. ✅ Check backend logs for error messages

**Common Errors:**
- `ANTHROPIC_API_KEY not configured` → Add key to .env
- `401 Unauthorized` → Invalid API key
- `429 Too Many Requests` → Rate limit exceeded
- `500 Internal Server Error` → Check API status

### File Upload Issues?

**Check:**
1. ✅ Is the file a PDF or TXT?
2. ✅ Is the file too large?
3. ✅ Does the PDF have readable text? (Not scanned images)
4. ✅ Is the backend server running?
5. ✅ Check CORS settings if accessing from different origin

## 📊 Expected Flow

### Successful Upload Flow:

1. ✅ User uploads PDF/TXT file
2. ✅ File saved to `backend/uploads/` directory
3. ✅ Text extracted from file
4. ✅ Content sent to Supermemory API
5. ✅ Supermemory returns memory_id
6. ✅ Content queried from Supermemory (RAG)
7. ✅ Claude extracts topics using RAG context
8. ✅ Topics returned in response
9. ✅ Frontend displays success and navigates

### What Gets Stored in Supermemory:

- **Content**: Full text from your PDF/TXT
- **Metadata**:
  - `filename`: Original filename
  - `file_id`: Unique ID for the file
  - `content_type`: File type (PDF/TXT)
  - `uploaded_at`: Timestamp
- **Container**: "uploaded-documents"
- **Processing**: Supermemory automatically chunks, embeds, and indexes the content

## 📝 Next Steps

1. **Test with a real PDF** - Upload a study material PDF
2. **Verify in Supermemory** - Check the dashboard to see your content
3. **Test topic extraction** - Verify topics are extracted correctly
4. **Check response quality** - Review the extracted topics
5. **Proceed to Phase 2** - Topic parsing and study path generation

## 📚 Additional Resources

- **Backend Documentation**: See `backend/README.md`
- **Environment Setup**: See `backend/ENV_SETUP.md`
- **Testing Guide**: See `backend/TESTING_GUIDE.md`
- **Supermemory Docs**: [supermemory.ai/docs](https://supermemory.ai/docs)
- **Claude Docs**: [docs.anthropic.com](https://docs.anthropic.com)

## 🆘 Need Help?

1. Check the `backend/TESTING_GUIDE.md` for detailed testing steps
2. Review backend console logs for error messages
3. Verify API keys are correct in `.env` file
4. Check API service status pages
5. Review the response JSON for error details

---

**Remember:** The system works with graceful degradation - if API keys are missing, file upload and text extraction still work, but Supermemory and Claude steps will be skipped.


