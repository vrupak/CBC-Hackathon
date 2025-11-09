# AI Study Buddy - Backend

FastAPI backend for the AI Study Buddy application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the **root directory** (project root, same level as `backend/` and `frontend/`):
```bash
# From the project root directory
touch .env
```

3. Add your API keys to `.env`:
- `SUPERMEMORY_API_KEY`: Your Supermemory API key
- `ANTHROPIC_API_KEY`: Your Anthropic (Claude) API key

**Note:** The `.env` file should be in the root directory, not inside the `backend/` directory.

## Running the Server

**Important: You must run the server from the `backend/` directory!**

```bash
# Make sure you're in the backend directory
cd backend

# Option 1: Using python -m (Recommended - most reliable)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Using Python directly
python main.py

# Option 4: Using startup script (Windows)
start_server.bat

# Option 5: Using startup script (Linux/Mac)
chmod +x start_server.sh && ./start_server.sh
```

**Troubleshooting:**
- If you get "Could not import module 'main'", make sure you're running the command from the `backend/` directory
- Use `python -m uvicorn` instead of just `uvicorn` for better reliability

The API will be available at `http://localhost:8000`

## API Endpoints

### `POST /api/upload-material`
Upload a study material file (PDF or TXT) and process it.

**Request:**
- `file`: Multipart file upload (PDF or TXT)

**Response:**
```json
{
  "message": "File uploaded and processed successfully",
  "file_id": "uuid",
  "filename": "document.pdf",
  "saved_path": "uploads/uuid.pdf",
  "uploaded_at": "2024-01-01T00:00:00",
  "text_extracted": true,
  "text_length": 1234,
  "supermemory_ingested": true,
  "memory_id": "memory_id",
  "topics_extracted": true,
  "topics": "Extracted topics text..."
}
```

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── services/
│   ├── supermemory_service.py  # Supermemory RAG integration
│   └── openai_service.py       # OpenAI LLM integration
└── utils/
    └── file_processor.py       # File text extraction utilities
```

## Phase 1 Implementation

This backend implements Phase 1 of the project:

1. **File Upload**: Receives and saves uploaded files to `uploads/` directory
2. **Text Extraction**: Extracts text from PDF and TXT files
3. **Supermemory Integration**: Ingests document content into Supermemory for RAG
4. **Topic Extraction**: Uses OpenAI LLM with Supermemory RAG context to extract topics


