from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
import aiofiles
from pathlib import Path
from typing import Optional, Annotated
import uuid
from datetime import datetime
import json
import asyncio

from utils.file_processor import extract_text_from_file
from services.supermemory_service import SupermemoryService
from services.claude_service import ClaudeService
# --- NEW IMPORTS ---
from services.db_service import DBService
from models import init_db, SessionLocal, User, Course, Module

app = FastAPI(title="AI Study Buddy API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize services
_supermemory_service: Optional[SupermemoryService] = None
_claude_service: Optional[ClaudeService] = None
# Initialize ORM database service
_db_service: Optional[DBService] = None


# --- DEPENDENCY INJECTION: Get DB Session ---
def get_db():
    """Dependency to get a SQLAlchemy session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# The database session will be injected into route handlers using this type
DBSession = Annotated[SessionLocal, Depends(get_db)]


def get_supermemory_service() -> Optional[SupermemoryService]:
    """Get or initialize Supermemory service"""
    global _supermemory_service
    if _supermemory_service is None:
        try:
            _supermemory_service = SupermemoryService()
        except ValueError as e:
            print(f"[WARN] Supermemory service not available: {e}")
    return _supermemory_service

def get_claude_service() -> Optional[ClaudeService]:
    """Get or initialize Claude service"""
    global _claude_service
    if _claude_service is None:
        try:
            _claude_service = ClaudeService()
        except ValueError as e:
            print(f"[WARN] Claude service not available: {e}")
    return _claude_service

def get_db_service() -> Optional[DBService]:
    """Get or initialize DB Service logic helper"""
    global _db_service
    if _db_service is None:
        _db_service = DBService()
    return _db_service


# --- STARTUP/SHUTDOWN EVENTS ---
@app.on_event("startup")
def startup_event():
    # Initialize the database and create all tables
    print("[INFO] Initializing SQLAlchemy database...")
    init_db()
    # Initialize DBService helper
    get_db_service()


# --- API ROUTES ---

@app.get("/")
async def root():
    return {"message": "AI Study Buddy API", "version": "1.0.0"}

@app.get("/health")
async def health(db: DBSession):
    """Health check endpoint"""
    # Test DB connection by querying the User table
    db_status = "unconfigured"
    try:
        db.query(User).first() # Simple test query
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "healthy",
        "supermemory_configured": get_supermemory_service() is not None,
        "claude_configured": get_claude_service() is not None,
        "database_status": db_status
    }

@app.get("/api/user/courses")
async def get_user_courses(db: DBSession):
    db_service = get_db_service()
    # Assume a user ID for demo purposes
    user = db_service.ensure_user(db, user_id="demo_user_1", api_key=os.getenv("ANTHROPIC_API_KEY", "DUMMY_KEY"))

    # Use ORM relationships to fetch data efficiently
    courses = db.query(Course).filter_by(user_id=user.id).all()

    # Transform ORM objects into a simple list/dict structure
    response_courses = []
    for course in courses:
        # Fetch modules related to this course
        modules = db.query(Module).filter_by(course_id=course.id).all()

        # NOTE: In a real app, the `topics` field needed by the frontend
        # must be reconstructed from the `Module` list and other linked Document tables.
        # For simplicity in this step, we return the course list.
        response_courses.append({
            "courseName": course.name,
            "courseId": course.id, # Using ORM PK as ID for now
            "progress": course.progress,
            "total_modules": course.total_modules,
            "module_count": len(modules),
            "last_upload_filename": "N/A" # Placeholder until you add Document table
        })

    return {"courses": response_courses}

@app.post("/api/upload-material")
async def upload_material(
    db: DBSession,
    file: UploadFile = File(...),
    courseId: str = Form("TEMP_ID"),
    courseName: str = Form("New Uploaded Material")
):
    """
    Upload study material and process it

    Returns format expected by frontend:
    {
        "success": boolean,
        "materialId": string,
        "message": string (optional)
    }
    """
    file_id = None
    file_path = None
    db_service = get_db_service()

    # Initialize processing_data
    processing_data = {"topics_extracted": False}

    # TEMPORARY USER FOR DEMO
    user = db_service.ensure_user(db, user_id="demo_user_1", api_key=os.getenv("ANTHROPIC_API_KEY", "DUMMY_KEY"))

    # TEMPORARY COURSE LINKING
    course_record = db_service.create_course(db, user.id, courseName)

    try:
        print(f"[INFO] Received upload request for file: {file.filename}")
        print(f"[INFO] Content type: {file.content_type}")

        # Validate file type
        allowed_types = ["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not supported. Please upload PDF, TXT, or DOCX files."
            )

        # Generate unique ID
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        saved_filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename

        print(f"[INFO] Saving file to: {file_path}")

        # Save file to disk
        file_content_bytes = await file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content_bytes)

        print(f"[INFO] File saved successfully. Size: {len(file_content_bytes)} bytes")

        # Extract text from file
        print("[INFO] Extracting text from file...")
        extracted_text = await extract_text_from_file(file_path, file.content_type)

        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from file. Please ensure the file contains readable text."
            )

        print(f"[INFO] Text extracted successfully. Length: {len(extracted_text)} characters")

        # Initialize response data (backend format for logging)
        processing_data = {
            "file_id": file_id,
            "filename": file.filename,
            "saved_path": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "text_length": len(extracted_text)
        }

        # Try to ingest to Supermemory
        supermemory_service = get_supermemory_service()
        memory_response = None
        if supermemory_service:
            try:
                print(f"[INFO] Ingesting document to Supermemory...")
                memory_response = await supermemory_service.ingest_document(
                    content=extracted_text,
                    filename=file.filename,
                    metadata={
                        "file_id": file_id,
                        "content_type": file.content_type,
                        "uploaded_at": datetime.utcnow().isoformat()
                    }
                )
                print(f"[INFO] Supermemory ingestion successful: {memory_response}")
                processing_data["supermemory_ingested"] = True
                processing_data["memory_id"] = memory_response.get("id")
                processing_data["memory_status"] = memory_response.get("status", "unknown")
            except Exception as e:
                print(f"[ERROR] Supermemory ingestion failed: {e}")
                processing_data["supermemory_ingested"] = False
                processing_data["supermemory_error"] = str(e)
                memory_response = None
        else:
            print("[WARN] Supermemory service not configured")
            processing_data["supermemory_ingested"] = False

        # Try to extract topics with Claude
        claude_service = get_claude_service()
        if claude_service:
            try:
                print("[INFO] Extracting topics with Claude...")
                # Check if document is ready for RAG search (not queued)
                memory_status = memory_response.get("status") if memory_response else None
                use_rag = (
                    supermemory_service
                    and processing_data.get("supermemory_ingested")
                    and memory_status == "completed"  # Only use RAG if document is fully processed
                )

                if use_rag:
                    try:
                        print("[INFO] Attempting to extract topics with RAG...")
                        topics_response = await claude_service.extract_topics_with_rag(
                            query="Extract all main topics and subtopics from this document in order of learning importance",
                            supermemory_service=supermemory_service
                        )
                    except Exception as rag_error:
                        print(f"[WARN] RAG search failed (document may still be processing): {rag_error}")
                        print("[INFO] Falling back to direct text extraction...")
                        # Fall back to direct text extraction if RAG fails
                        topics_response = await claude_service.extract_topics(extracted_text)
                else:
                    if memory_status == "queued":
                        print("[INFO] Document is still queued in Supermemory, using direct text extraction...")
                    # Use direct text extraction (faster and more reliable for immediate processing)
                    topics_response = await claude_service.extract_topics(extracted_text)

                print(f"[INFO] Topics extracted successfully")
                processing_data["topics_extracted"] = True
                processing_data["topics"] = topics_response.get("topics_text")
            except Exception as e:
                print(f"[ERROR] Topic extraction failed: {e}")
                processing_data["topics_extracted"] = False
                processing_data["topics_error"] = str(e)
        else:
            print("[WARN] Claude service not configured")
            processing_data["topics_extracted"] = False

        # Return response in format expected by frontend
        return JSONResponse({
            "success": True,
            "message": "File uploaded and processed successfully",
            "file_id": file_id,
            "filename": file.filename,
            "saved_path": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "text_extracted": True,
            "text_length": len(extracted_text),
            "supermemory_ingested": processing_data.get("supermemory_ingested", False),
            "memory_id": processing_data.get("memory_id"),
            "supermemory_error": processing_data.get("supermemory_error"),
            "topics_extracted": processing_data.get("topics_extracted", False),
            "topics": processing_data.get("topics"),
            "topics_error": processing_data.get("topics_error")
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Upload failed: {str(e)}")
        # Clean up file on error
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as cleanup_error:
                print(f"[ERROR] Failed to cleanup file: {cleanup_error}")

        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.post("/api/chat/stream")
async def chat_stream(message: dict):
    """
    Chat endpoint with streaming response

    Request format:
    {
        "message": "User question",
        "conversation_id": "optional-id"
    }

    Response: Server-Sent Events (SSE) stream with character-by-character text
    """
    user_message = message.get("message", "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conversation_id = message.get("conversation_id", str(uuid.uuid4()))

    def generate():
        try:
            # Get services
            supermemory_service = get_supermemory_service()
            claude_service = get_claude_service()

            if not claude_service:
                yield f"data: {json.dumps({'error': 'Claude service not configured'})}\n\n"
                return

            print(f"[INFO] Chat request: {user_message}")
            print(f"[INFO] Conversation ID: {conversation_id}")

            # Step 1: Search Supermemory for relevant context
            supermemory_context = ""
            if supermemory_service:
                try:
                    print(f"[INFO] Searching Supermemory for context...")
                    search_results = asyncio.run(supermemory_service.query(
                        query=user_message,
                        container_tag="uploaded-documents",
                        limit=5
                    ))

                    # Extract context from search results
                    if isinstance(search_results, dict):
                        if "results" in search_results:
                            supermemory_context = "\n\n".join([
                                str(result.get("content", result.get("text", "")))
                                for result in search_results["results"]
                            ])
                        elif "data" in search_results and isinstance(search_results["data"], list):
                            supermemory_context = "\n\n".join([
                                str(item.get("content", item.get("text", "")))
                                for item in search_results["data"]
                            ])

                    if supermemory_context:
                        print(f"[INFO] Found Supermemory context: {len(supermemory_context)} characters")
                        # Yield context indicator
                        yield f"data: {json.dumps({'type': 'context', 'found': True})}\n\n"
                    else:
                        print("[INFO] No Supermemory context found, will use general knowledge")
                        yield f"data: {json.dumps({'type': 'context', 'found': False})}\n\n"

                except Exception as e:
                    print(f"[WARN] Supermemory search failed: {e}")
                    yield f"data: {json.dumps({'type': 'context', 'found': False, 'error': str(e)})}\n\n"

            # Step 2: Build system prompt with context if available
            system_prompt = """You are an expert AI Study Buddy helping students learn.
Your role is to:
1. Answer questions clearly and concisely
2. Provide examples when helpful
3. Adapt explanations to the student's level
4. Encourage deeper understanding
5. Be encouraging and supportive

IMPORTANT: Do NOT use markdown formatting. Respond in plain text format only:
- Do NOT use # for headings
- Do NOT use ** for bold
- Do NOT use - for bullet points
- Do NOT use ``` for code blocks
- Do NOT use any other markdown syntax

Instead, use:
- Line breaks and natural text organization
- Numbers (1. 2. 3.) for lists if needed
- Plain text emphasis using CAPS if needed
- Clear spacing between sections

If relevant study materials are provided, use them as the primary source of information.

IMPORTANT: When answering questions based on general knowledge (not from study materials), include relevant sources and a YouTube video at the end of your response in this format:

Sources:
1. https://example.com - Brief description
2. https://example2.com - Brief description
3. https://example3.com - Brief description

Recommended YouTube Video:
https://www.youtube.com/watch?v=example - Title of the most relevant educational video on this topic

IMPORTANT: Always include actual URLs (starting with https://) so they can be clicked. For YouTube videos, use real video URLs. For example:
1. https://www.wikipedia.org/wiki/Economics - Comprehensive encyclopedia of economic concepts
2. https://www.khanacademy.org/economics - Free educational videos on economics
3. https://www.investopedia.com - Financial and investment definitions

Recommended YouTube Video:
https://www.youtube.com/watch?v=kITQ1iZWb4E - Khan Academy Economics Introduction (or another relevant educational video)"""

            # Build user message with context
            if supermemory_context:
                full_message = f"""Based on the student's study materials:

{supermemory_context}

---

Student question: {user_message}"""
            else:
                full_message = user_message

            # Step 3: Stream response from Claude using streaming API
            print(f"[INFO] Streaming response from Claude...")

            with claude_service.client.messages.stream(
                model=claude_service.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_message}
                ]
            ) as stream:
                # Yield start event
                yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id})}\n\n"

                # If no context found, add acknowledgment at the beginning
                if not supermemory_context:
                    acknowledgment = "Note: I didn't find this information in your uploaded study materials, so I'm providing an answer based on general knowledge.\n\n"
                    for char in acknowledgment:
                        event_data = json.dumps({"type": "text", "content": char})
                        yield f"data: {event_data}\n\n"

                # Stream each character as it arrives
                for text in stream.text_stream:
                    # Use JSON serialization for proper escaping
                    event_data = json.dumps({"type": "text", "content": text})
                    yield f"data: {event_data}\n\n"

                # Get the final message for storage
                final_message = stream.get_final_message()

            # Step 4: Store conversation in Supermemory
            if supermemory_service:
                try:
                    print(f"[INFO] Storing conversation in Supermemory...")

                    # Get the full response text
                    response_text = final_message.content[0].text if final_message.content else ""

                    # Store the user message
                    asyncio.run(supermemory_service.ingest_document(
                        content=f"User Question: {user_message}",
                        filename=f"conversation-user-{conversation_id[:8]}",
                        metadata={
                            "type": "conversation",
                            "role": "user",
                            "conversation_id": conversation_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ))

                    # Store the AI response
                    asyncio.run(supermemory_service.ingest_document(
                        content=f"AI Response: {response_text}",
                        filename=f"conversation-ai-{conversation_id[:8]}",
                        metadata={
                            "type": "conversation",
                            "role": "assistant",
                            "conversation_id": conversation_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ))

                    print(f"[INFO] Conversation stored in Supermemory")
                except Exception as e:
                    print(f"[WARN] Failed to store conversation in Supermemory: {e}")

            # Yield end event
            yield f"data: {json.dumps({'type': 'end', 'conversation_id': conversation_id})}\n\n"

        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
