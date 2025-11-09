# Troubleshooting Guide

## Issue 1: Chrome DevTools Error (Harmless)

**Error:** `No route matches URL "/.well-known/appspecific/com.chrome.devtools.json"`

**Status:** ✅ This is a **harmless error** that can be ignored.

**Explanation:** Chrome DevTools automatically requests this path to check for DevTools-specific configuration. This doesn't affect your application functionality.

**Solution:** No action needed. This error can be safely ignored.

## Issue 2: Supermemory Dashboard Not Showing Documents

If you're getting a 200 status code after uploading but documents aren't appearing in the Supermemory dashboard, follow these steps:

### Step 1: Check Backend Logs

After uploading a PDF, check your backend console for debug messages. You should see:

```
[DEBUG] Attempting to ingest document to Supermemory: filename.pdf
[DEBUG] Supermemory API URL: https://api.supermemory.ai/v1/memories/add
[DEBUG] Supermemory response status: 200
[DEBUG] Successfully ingested to Supermemory. Memory ID: <id>
```

Or if there's an error:

```
[ERROR] Supermemory HTTP error: HTTP 404: {"error": "Endpoint not found"}
```

### Step 2: Check Frontend Console

Open your browser's developer console (F12) and look for:

```javascript
Upload response: { ... }
Supermemory ingested: true/false
Memory ID: <id or undefined>
```

If `supermemory_ingested` is `false`, check the `supermemory_error` field.

### Step 3: Verify API Key

1. Check that `SUPERMEMORY_API_KEY` is set in `.env` file in the **root directory** (same level as `backend/` and `frontend/`)
2. Verify the API key is valid and active
3. Check if the API key has the correct permissions

### Step 4: Check API Response

Look at the full API response in the browser console. It should include:

```json
{
  "supermemory_ingested": true,
  "memory_id": "some-id-here",
  "supermemory_response": { ... }
}
```

If `supermemory_ingested` is `false`, check the `supermemory_error` field for details.

### Step 5: Verify Supermemory API Endpoint

The current implementation uses:
- **Endpoint:** `https://api.supermemory.ai/v1/memories/add`
- **Method:** POST
- **Payload:** JSON with `content`, `container_tag`, and `metadata`

**If this endpoint is incorrect**, you may need to:
1. Check the official Supermemory API documentation
2. Update the endpoint in `backend/services/supermemory_service.py`
3. Verify the payload structure matches Supermemory's requirements

### Step 6: Check Supermemory Dashboard

1. **Wait a few minutes**: Processing can take time
2. **Refresh the dashboard**: Sometimes it needs a manual refresh
3. **Check the correct container**: Documents are stored with `container_tag: "uploaded-documents"`
4. **Search by filename**: Try searching for your uploaded filename
5. **Check memory ID**: If you got a `memory_id` in the response, search for it

### Common Issues

#### Issue: `supermemory_ingested: false` with error "SUPERMEMORY_API_KEY not configured"

**Solution:** 
- Make sure `.env` file exists in the **root directory** (same level as `backend/` and `frontend/`)
- Add `SUPERMEMORY_API_KEY=your_key_here`
- Restart the backend server

#### Issue: HTTP 404 or 401 error

**Possible causes:**
- Wrong API endpoint
- Invalid API key
- Wrong API version (currently using v1)

**Solution:**
- Verify API key is correct
- Check Supermemory API documentation for correct endpoint
- Try updating `SUPERMEMORY_API_URL` in `.env` if needed

#### Issue: HTTP 400 error

**Possible causes:**
- Wrong payload structure
- Missing required fields
- Invalid content format

**Solution:**
- Check the error message in backend logs
- Verify payload structure matches Supermemory API requirements
- Check Supermemory API documentation

### Next Steps

1. **Upload a test file** and check both backend and frontend logs
2. **Look for the debug messages** we added - they show exactly what's happening
3. **Share the error messages** if you see any, and we can help fix the API integration
4. **Check Supermemory API docs** to verify the correct endpoint and payload structure

## Debugging Tips

### Enable More Logging

The code now includes detailed logging. Check:

1. **Backend console**: Look for `[DEBUG]` and `[ERROR]` messages
2. **Frontend console**: Look for `console.log` messages with upload response
3. **Network tab**: Check the actual API request/response in browser DevTools

### Test Supermemory API Directly

You can test the Supermemory API directly using curl:

```bash
curl -X POST "https://api.supermemory.ai/v1/memories/add" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test content",
    "container_tag": "uploaded-documents",
    "metadata": {
      "filename": "test.txt"
    }
  }'
```

Replace `YOUR_API_KEY` with your actual API key.

### Check API Documentation

Refer to the official Supermemory API documentation:
- Website: https://supermemory.ai
- API Docs: Check their documentation for the correct endpoints and payload structure

## Getting Help

If you're still having issues:

1. **Check the logs**: Both backend and frontend console logs
2. **Share error messages**: Include the exact error message from logs
3. **Check API status**: Verify Supermemory API is working
4. **Verify API key**: Make sure it's valid and has proper permissions

