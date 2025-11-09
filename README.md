# 🧠 AI Study Buddy

An AI-powered study assistant that integrates with Canvas LMS to help students learn more effectively. Upload study materials or sync Canvas courses to get AI-generated study paths, contextual tutoring, and personalized learning assistance.

## ✨ Features

- **Canvas LMS Integration**: Sync courses and modules directly from ASU Canvas
- **Smart Document Upload**: Upload PDFs, text files, and study materials
- **AI Study Path Generation**: Automatically extract topics and create optimal learning sequences
- **RAG-Powered Chat**: Context-aware AI tutor using uploaded materials
- **Streaming Responses**: Real-time AI responses with typing indicator
- **Progress Tracking**: Track completion status across topics and subtopics
- **Intelligent Source Citation**: Automatic inclusion of educational resources and YouTube videos for general knowledge questions

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│          (React + Vite + Remix Router v7)                   │
│  ┌────────────┐  ┌──────────┐  ┌───────────────┐          │
│  │   Home     │  │  Chat    │  │ Course Cards  │          │
│  │   Page     │  │  Page    │  │  & Modules    │          │
│  └────────────┘  └──────────┘  └───────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                   HTTP/SSE Streaming
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Endpoints                            │  │
│  │  /upload, /chat/stream, /courses, /canvas/*         │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────┬──────────────────┬────────────────────┐  │
│  │   Canvas     │   Claude AI      │   Supermemory      │  │
│  │   Service    │   Service        │   RAG Service      │  │
│  │              │                  │                     │  │
│  │ - Fetch      │ - Topic          │ - Ingest docs      │  │
│  │   courses    │   extraction     │ - Vector search    │  │
│  │ - Download   │ - Streaming      │ - Context          │  │
│  │   files      │   chat           │   retrieval        │  │
│  └──────────────┴──────────────────┴────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           SQLite Database                             │  │
│  │  (Courses, Modules, Uploads, Study Paths)            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
    ┌─────────────────┐       ┌─────────────────────┐
    │  Canvas LMS API │       │  Supermemory v3 API │
    │   (ASU Canvas)  │       │   (Vector Storage)  │
    └─────────────────┘       └─────────────────────┘
```

### Key Components

1. **Frontend (React + Vite)**
   - Modern React with Remix Router v7
   - Tailwind CSS for styling
   - Server-Sent Events (SSE) for streaming responses
   - Course/module management UI

2. **Backend (FastAPI)**
   - Async Python REST API
   - SQLAlchemy ORM with SQLite
   - Integration with Canvas LMS, Claude AI, and Supermemory
   - Streaming chat with context-aware responses

3. **External Services**
   - **Claude (Anthropic)**: LLM for topic extraction and chat (claude-sonnet-4-5-20250929)
   - **Supermemory v3**: RAG system for document ingestion and vector search
   - **Canvas LMS API**: Course and file synchronization

---

## 🛠️ Technology Stack

### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Remix Router v7** - File-based routing
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client
- **Fetch API** - SSE streaming

### Backend
- **Python 3.11+** - Runtime
- **FastAPI** - Async web framework
- **SQLAlchemy** - ORM
- **SQLite** - Database
- **Anthropic Python SDK** - Claude API integration
- **aiohttp** - Async HTTP client
- **python-dotenv** - Environment variable management
- **PyPDF2** - PDF text extraction

### External APIs
- **Claude Sonnet 4.5** (`claude-sonnet-4-5-20250929`)
- **Supermemory v3 API** - RAG and vector storage
- **Canvas LMS REST API** - Course/file management

---

## 📋 Prerequisites

- **Node.js 18+** and npm
- **Python 3.11+** and pip
- **Anthropic API Key** (for Claude)
- **Supermemory API Credentials** (Space ID, Token, Base URL)
- **Canvas API Token** (for Canvas integration)

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/vrupak/CBC-Hackathon.git
cd CBC-Hackathon
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Or create manually
```

**Backend Environment Variables** (`.env`):

```env
# Claude API
ANTHROPIC_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Supermemory RAG
SUPERMEMORY_API_BASE_URL=https://api.supermemory.ai
SUPERMEMORY_SPACE_ID=your_space_id
SUPERMEMORY_API_TOKEN=your_supermemory_token

# Canvas LMS
CANVAS_API_TOKEN=your_canvas_api_token
CANVAS_BASE_URL=https://canvas.asu.edu

# Database
DATABASE_URL=sqlite:///./ai_study_buddy.db
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file (if needed for frontend-specific config)
```

### 4. Database Initialization

The database will be automatically created when you first run the backend. Tables are defined in `backend/models.py`.

---

## 🚀 Running the Application

### Start Backend Server

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`

API documentation (Swagger): `http://localhost:8000/docs`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## 📡 API Endpoints

### Canvas Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/canvas/available-courses` | Fetch available Canvas courses |
| POST | `/api/canvas/add-courses` | Add selected Canvas courses to local database |
| POST | `/api/canvas/courses/{id}/sync-files` | Sync course files/modules from Canvas |
| POST | `/api/canvas/modules/{id}/download` | Download module file from Canvas |
| POST | `/api/canvas/modules/{id}/ingest` | Ingest module file into Supermemory RAG |

### Course Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/courses` | List all local courses with progress |
| GET | `/api/courses/{id}/modules` | Get modules for a specific course |

### Study Path Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/llm/modules/{id}/generate-topics` | Generate AI study path for module |
| GET | `/api/llm/modules/{id}/study-path` | Retrieve persisted study path |
| PUT | `/api/llm/modules/{id}/update-study-path` | Update study path with progress |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload-material` | Upload study material (PDF/text) |
| GET | `/api/materials/list` | List all uploaded materials |

### Chat (AI Tutor)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/stream` | Stream AI chat responses (SSE) |
| POST | `/api/chat` | Non-streaming chat endpoint |

### Study Progress

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/study-progress/save` | Save progress to Supermemory |
| GET | `/api/study-progress/load/{file_id}` | Load saved progress |

---

## 🔍 Key Features Implementation

### 1. RAG-Powered Context Retrieval

The application uses Supermemory v3 API for vector search and context retrieval:

```python
# Context relevance threshold
MIN_CONTEXT_LENGTH = 500

# Only use study materials if substantial context is found
if supermemory_context and len(supermemory_context.strip()) >= MIN_CONTEXT_LENGTH:
    # Use RAG context
    system_prompt += f"\n\nBased on the student's study materials:\n{supermemory_context}"
else:
    # Use general knowledge with mandatory sources
    supermemory_context = ""
```

### 2. Streaming Chat Responses

Chat responses stream token-by-token using Server-Sent Events (SSE):

```python
async def stream_chat():
    # Stream metadata first
    yield json.dumps({"metadata": {"context_used": True}}) + "\n"

    # Stream text tokens
    async with client.messages.stream(...) as stream:
        async for text in stream.text_stream:
            yield json.dumps({"text": text}) + "\n"

    # Signal completion
    yield json.dumps({"done": True}) + "\n"
```

### 3. Canvas LMS Integration

Synchronize courses and modules directly from Canvas:

1. Fetch available courses from Canvas API
2. Store selected courses in local database
3. Sync course files/modules
4. Download file content
5. Ingest into Supermemory for RAG

### 4. Intelligent Source Citation

When answering from general knowledge (not study materials), the AI automatically includes:
- 3+ authoritative educational sources
- 1 relevant YouTube video
- Properly formatted with working URLs

---

## 📊 Database Schema

### Tables

- **`local_courses`**: Courses synced from Canvas
  - `id`, `canvas_id`, `name`, `course_code`, `created_at`

- **`local_modules`**: Course modules/files
  - `id`, `course_id`, `name`, `canvas_file_id`, `file_url`, `is_downloaded`, `is_ingested`, `study_path_json`, `completed`

- **`uploaded_files`**: Manually uploaded materials
  - `id`, `filename`, `file_path`, `supermemory_memory_id`, `topics`, `uploaded_at`

---

## 🧪 Recent Improvements

### Context Relevance Detection
- Added 500-character minimum threshold to prevent false positives
- Only shows "using study materials" when substantial context is found

### Mandatory Educational Resources
- General knowledge responses always include sources and YouTube videos
- Explicit format requirements in system prompt

### System Prompt Refinement
- AI prevented from falsely claiming to use study materials
- Clear distinction between RAG-powered and general knowledge responses

### Bug Fixes
- Fixed Supermemory v3 API nested context extraction (`results[].chunks[].content`)
- Added empty context validation to prevent storing error messages
- Restored missing `/api/chat/stream` and `/api/llm/modules/{id}/update-study-path` endpoints

---

## 🔧 Development Workflow

### Git Branches

- **`main`**: Production-ready code
- **`development`**: Integration branch
- **`db-setup`**: Database and Canvas integration features

### Making Changes

1. Create feature branch from `development`
2. Make changes and test locally
3. Commit with descriptive messages
4. Push to remote and create pull request
5. Merge to `development` for testing
6. Merge to `main` for production

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

---

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY environment variable is required"
- Ensure `.env` file exists in `backend/` directory
- Verify `ANTHROPIC_API_KEY` is set correctly

### "No context retrieved from Supermemory"
- Document may still be processing in Supermemory
- Wait a few moments and try again
- Check `SUPERMEMORY_SPACE_ID` and `SUPERMEMORY_API_TOKEN` are correct

### Canvas API 401 Unauthorized
- Verify `CANVAS_API_TOKEN` is valid
- Check token permissions include course and file access

### Frontend build errors
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Ensure Node.js version is 18+

---

## 📝 License

This project is open-source and developed for educational purposes during a hackathon.

---

## 👥 Contributors

- **Frontend Development**: React UI, Canvas course cards, chat interface
- **Backend Development**: FastAPI, Canvas integration, RAG implementation
- **AI/LLM Integration**: Claude API, Supermemory, streaming chat

---

## 🎯 Future Enhancements

- [ ] Adaptive study planner with spaced repetition
- [ ] Auto-generated quizzes and flashcards
- [ ] Learning progress visualization dashboard
- [ ] Collaborative study sessions
- [ ] Mobile app (React Native)
- [ ] Support for more LMS platforms (Blackboard, Moodle)
- [ ] Advanced topic dependency graphs
- [ ] Integration with calendar for study scheduling

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Supermemory API](https://supermemory.ai/)
- [Canvas LMS REST API](https://canvas.instructure.com/doc/api/)
- [Remix Router](https://remix.run/)

---

