from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import os
from pathlib import Path
from typing import Optional, Annotated, List
import httpx
from dotenv import load_dotenv
import logging
import re
import uuid
from datetime import datetime
import aiofiles

from services.supermemory_service import SupermemoryService
from services.claude_service import ClaudeService
from services.claude_client import ClaudeClient
from services.db_service import DBService
from services.canvas_service import CanvasService
from utils.file_processor import extract_text_from_file
from models import init_db, SessionLocal, Course, Module, DB_PATH

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables globally
load_dotenv()
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")

app = FastAPI(title="AI Study Buddy API (Single-User)", version="1.0.0")

# --- FILE PATH CONFIGURATION ---
# Base directory for all downloaded course files
DOWNLOAD_BASE_DIR = Path(__file__).parent / "download"
DOWNLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True) # Ensure base directory exists

# --- SCHEMA FOR ADDING COURSES ---
class CourseSelection(BaseModel):
    # Expects a list of strings, where each string is the Canvas Course ID (e.g., "5001")
    canvas_course_ids: List[str] = Field(..., min_length=1, description="List of Canvas course IDs to add to the local database.")

# --- CHAT REQUEST/RESPONSE MODELS ---
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = None
    file_id: Optional[str] = None  # ID of uploaded material for context

class ChatResponse(BaseModel):
    success: bool
    response: str
    message: Optional[str] = None
    context_used: Optional[bool] = None
    web_search_used: Optional[bool] = None
    stored_in_memory: Optional[bool] = None

# Web search support (placeholder for future integration with web search API)
async def web_search(query: str) -> str:
    """
    Placeholder web search function.
    In production, this would integrate with a real web search API (Google, Bing, etc.)
    For now, returns formatted notice that web search would be performed.

    Args:
        query: Search query

    Returns:
        Search results as formatted string
    """
    # TODO: Integrate with actual web search API
    # For now, return a placeholder indicating web search capability
    return f"[Web search results for: '{query}' would appear here with actual search integration]"

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist (Original non-Canvas upload location)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize services
_supermemory_service: Optional[SupermemoryService] = None
_claude_service: Optional[ClaudeService] = None
_db_service: Optional[DBService] = None


# --- DATABASE UTILITY (FOR SCHEMA MIGRATION/RESET) ---
def reset_db_schema():
    """Deletes the existing database file to force schema creation."""
    db_file = Path(DB_PATH.split('sqlite:///')[-1])
    if db_file.exists():
        logger.warning(f"Existing database file found at {db_file}. Deleting to apply new schema...")
        try:
            db_file.unlink()
            logger.info("Database file deleted successfully.")
        except Exception as e:
            logger.error(f"Failed to delete database file: {e}")
            raise

# --- DEPENDENCY INJECTION: Get DB Session ---
def get_db():
    """Dependency to get a SQLAlchemy session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DBSession = Annotated[SessionLocal, Depends(get_db)]

def get_supermemory_service() -> Optional[SupermemoryService]:
    """Get or initialize Supermemory service"""
    global _supermemory_service
    if _supermemory_service is None:
        try:
            _supermemory_service = SupermemoryService()
        except ValueError as e:
            logger.warning(f"Supermemory service not available: {e}")
    return _supermemory_service

def get_claude_service() -> Optional[ClaudeService]:
    """Get or initialize Claude service (relies on ANTHROPIC_API_KEY from env)"""
    global _claude_service
    if _claude_service is None:
        try:
            # Note: API Key is loaded from environment by the service itself
            _claude_service = ClaudeService() 
        except ValueError as e:
            logger.warning(f"Claude service not available: {e}")
    return _claude_service

def get_db_service() -> Optional[DBService]:
    """Get or initialize DB Service logic helper"""
    global _db_service
    if _db_service is None:
        _db_service = DBService()
    return _db_service
    
def get_canvas_service(token: str) -> Optional[CanvasService]:
    """Get or initialize Canvas service"""
    try:
        return CanvasService(token)
    except ValueError as e:
        logger.error(f"Canvas service failed initialization: {e}")
        return None

# --- UTILITY: Path Sanitization ---
def sanitize_path_name(name: str) -> str:
    """Sanitizes a string for use as a directory or file name."""
    # Replace non-alphanumeric, non-space, non-hyphen, non-underscore characters with nothing
    sanitized = re.sub(r'[^\w\s-]', '', name).strip()
    # Replace spaces with underscores
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized or 'unknown_resource'


# --- STARTUP/SHUTDOWN EVENTS ---
@app.on_event("startup")
def startup_event():
    reset_db_schema() 
    logger.info("Initializing SQLAlchemy database with new schema...")
    init_db() 
    get_db_service()
    
# --- API ROUTES ---

@app.get("/")
async def root():
    return {"message": "AI Study Buddy API (Single-User Mode)", "version": "1.0.0"}

@app.get("/health")
async def health(db: DBSession):
    db_status = "unconfigured"
    try:
        # Check database connection by querying a lightweight table (e.g., Course)
        db.query(Course).first() 
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
        
    return {
        "status": "healthy",
        "canvas_token_configured": bool(CANVAS_TOKEN),
        "supermemory_configured": get_supermemory_service() is not None,
        "claude_configured": get_claude_service() is not None,
        "database_status": db_status
    }

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint - returns tokens as they are generated

    Request format same as /api/chat
    Response: Server-Sent Events (SSE) with JSON chunks

    Each line contains JSON:
    - {"metadata": {"context_used": bool, "web_search_used": bool}} (first chunk)
    - {"text": "token"} (subsequent chunks)
    - {"done": true} (final chunk)
    """
    try:
        print(f"[INFO] Received streaming chat request: {request.message[:100]}...")

        # Initialize services
        try:
            claude_client = ClaudeClient()
        except ValueError as e:
            print(f"[ERROR] Claude service initialization failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="Claude API is not configured. Please set ANTHROPIC_API_KEY in your .env file."
            )

        supermemory_service = get_supermemory_service()
        context = None
        context_used = False

        # STEP 1: Retrieve context from Supermemory (if file_id provided)
        if request.file_id and supermemory_service:
            try:
                print(f"[INFO] Retrieving context from Supermemory for file_id: {request.file_id}")
                # Increase retry count and delay to give documents more time to index
                rag_results = await supermemory_service.query(
                    request.message,
                    limit=3,
                    retry_count=5,  # Increased from 3
                    retry_delay=2.0  # Increased from 1.0
                )

                # Extract context from results
                if isinstance(rag_results, dict):
                    if "results" in rag_results:
                        context = "\n\n".join([
                            str(result.get("content", result.get("text", "")))
                            for result in rag_results["results"]
                        ])
                    elif "content" in rag_results:
                        context = str(rag_results["content"])
                    elif "data" in rag_results:
                        data = rag_results["data"]
                        if isinstance(data, list):
                            context = "\n\n".join([
                                str(item.get("content", item.get("text", "")))
                                for item in data
                            ])
                        elif isinstance(data, dict) and "content" in data:
                            context = str(data["content"])

                if context and len(context.strip()) > 0:
                    context_used = True
                    print(f"[INFO] Retrieved context from Supermemory ({len(context)} chars)")
                else:
                    context = None
                    print("[INFO] No relevant context found in Supermemory")
            except Exception as e:
                print(f"[WARN] Failed to retrieve context from Supermemory: {e}")
                context = None

        # STEP 2: Stream response from Claude
        chat_history = None
        if request.conversation_history:
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        print(f"[INFO] Streaming response from Claude Sonnet 4.5")

        # Create streaming generator (async)
        async def generate():
            import sys
            import json
            import asyncio

            full_response = ""
            response_context_used = False
            web_search_used = False
            chunk_count = 0

            try:
                # Stream from Claude (async generator)
                async for chunk in claude_client.answer_with_web_search_stream(
                    question=request.message,
                    context=context,
                    chat_history=chat_history,
                    web_search_fn=web_search
                ):
                    chunk_count += 1
                    print(f"[STREAM] Yielding chunk {chunk_count}", file=sys.stderr, flush=True)

                    # Ensure chunk ends with newline for proper line delimitering
                    chunk_to_send = chunk + "\n" if not chunk.endswith("\n") else chunk
                    yield chunk_to_send

                    # Force a brief async yield to allow client to receive this chunk immediately
                    await asyncio.sleep(0.001)

                    # Extract metadata and text from chunks for memory storage
                    try:
                        data = json.loads(chunk.strip())
                        if "metadata" in data:
                            response_context_used = data["metadata"]["context_used"]
                            web_search_used = data["metadata"]["web_search_used"]
                        elif "text" in data:
                            full_response += data["text"]
                    except:
                        pass

                # STEP 3: Store Q&A pair in Supermemory after streaming completes
                if supermemory_service and request.file_id and full_response:
                    try:
                        print(f"[INFO] Storing Q&A in Supermemory...")
                        conversation_entry = f"Q: {request.message}\n\nA: {full_response}"

                        await supermemory_service.ingest_document(
                            content=conversation_entry,
                            filename=f"conversation-{request.file_id[:8]}.md",
                            metadata={
                                "type": "conversation",
                                "file_id": request.file_id,
                                "timestamp": datetime.utcnow().isoformat(),
                                "context_used": str(response_context_used),
                                "web_search_used": str(web_search_used),
                                "model": "claude-sonnet-4-5"
                            }
                        )
                        print(f"[INFO] Conversation stored in Supermemory")
                    except Exception as e:
                        print(f"[WARN] Failed to store conversation in Supermemory: {e}")

            except Exception as e:
                print(f"[ERROR] Streaming error: {str(e)}")
                error_chunk = json.dumps({
                    "error": str(e),
                    "text": "An error occurred while streaming the response."
                }) + "\n"
                yield error_chunk

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Streaming chat request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing streaming chat request: {str(e)}"
        )

# Endpoint renamed and simplified - no user context needed
@app.get("/api/courses") 
async def get_all_courses(db: DBSession):
    db_service = get_db_service()
    
    # Fetch all courses (no user filtering)
    courses = db_service.get_all_courses(db)
    
    # Transform ORM objects into a simple list/dict structure
    response_courses = []
    for course in courses:
        modules = db.query(Module).filter_by(course_id=course.id).all()
        
        response_courses.append({
            "courseName": course.name,
            "local_course_id": course.id, # Internal PK (1, 2, 3...)
            "canvas_id": course.canvas_id, # External Canvas ID (5001, 6002...)
            "progress": course.progress,
            "total_modules": course.total_modules,
            "module_count": len(modules),
            "last_upload_filename": "N/A" # Placeholder
        })
        
    return {"courses": response_courses, "status": "single-user mode"} 

# --- NEW: Endpoint to fetch courses available for adding ---
@app.get("/api/canvas/available-courses")
async def get_available_canvas_courses(db: DBSession):
    db_service = get_db_service()
    
    canvas_token = CANVAS_TOKEN
    if not canvas_token:
        raise HTTPException(
            status_code=500,
            detail="CANVAS_TOKEN environment variable not set. Cannot connect to Canvas."
        )

    try:
        canvas_service = get_canvas_service(canvas_token)
        if not canvas_service:
            raise Exception("Canvas Service Initialization failed.")
            
        # 1. Fetch all active courses from Canvas API
        all_canvas_courses = await canvas_service.get_user_courses()
        
        # 2. Get the set of IDs already stored in the local DB
        local_canvas_ids = db_service.get_all_canvas_ids(db)
        
        # 3. Filter the Canvas courses
        available_courses = []
        for course in all_canvas_courses:
            course_id_str = str(course.get("id"))
            
            if course.get("name") and course_id_str not in local_canvas_ids:
                available_courses.append({
                    "canvas_id": course_id_str,
                    "name": course.get("name"),
                    "course_code": course.get("course_code", "N/A")
                })
        
        return JSONResponse(
            status_code=200,
            content={"available_courses": available_courses}
        )
    
    except httpx.HTTPStatusError as e:
        error_msg = f"Canvas API Error: HTTP {e.response.status_code}. Please check your CANVAS_TOKEN validity."
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred while listing available courses: {str(e)}"
        logger.error(f"Available courses failed: {e}")
        raise HTTPException(status_code=500, detail=error_msg)


# --- NEW: Endpoint to add selected courses to the DB ---
@app.post("/api/canvas/add-courses")
async def add_selected_canvas_courses(
    db: DBSession, 
    selection: CourseSelection
):
    db_service = get_db_service()
    imported_count = 0
    
    try:
        canvas_service = get_canvas_service(CANVAS_TOKEN)
        if not canvas_service:
            raise Exception("Canvas Service Initialization failed.")
            
        all_canvas_courses = await canvas_service.get_user_courses()
        canvas_course_map = {str(c.get("id")): c.get("name") for c in all_canvas_courses if c.get("id") and c.get("name")}
    except Exception as e:
        logger.error(f"Failed to verify course IDs against Canvas: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not verify course selections against Canvas. Please try again."
        )

    for course_id_str in selection.canvas_course_ids:
        course_name = canvas_course_map.get(course_id_str)
        
        if course_name:
            db_service.get_or_create_course_from_canvas(
                db, 
                course_name=course_name, 
                canvas_id=course_id_str
            )
            imported_count += 1
            
    if imported_count == 0 and len(selection.canvas_course_ids) > 0:
         return JSONResponse(
            status_code=200,
            content={"message": "All selected courses were already present or invalid. 0 new courses added."}
        )

    return JSONResponse(
        status_code=200,
        content={"message": f"Successfully added {imported_count} new course(s) to the local database."}
    )


# --- Original fetch-canvas-courses endpoint (now renamed to be explicit) ---
@app.post("/api/canvas/sync-all")
async def sync_all_canvas_courses(db: DBSession):
    db_service = get_db_service()
    
    canvas_token = CANVAS_TOKEN
    if not canvas_token:
        raise HTTPException(
            status_code=500,
            detail="CANVAS_TOKEN environment variable not set. Cannot connect to Canvas."
        )
    
    try:
        canvas_service = get_canvas_service(canvas_token)
        if not canvas_service:
            raise Exception("Canvas Service Initialization failed.")
            
        canvas_courses = await canvas_service.get_user_courses()
        
        imported_count = 0
        for canvas_course in canvas_courses:
            course_name = canvas_course.get("name")
            course_id = str(canvas_course.get("id"))
            
            if course_name and course_id:
                db_service.get_or_create_course_from_canvas(
                    db, 
                    course_name=course_name, 
                    canvas_id=course_id
                )
                imported_count += 1

        return JSONResponse(
            status_code=200,
            content={"message": f"Successfully fetched and processed {imported_count} courses from Canvas."}
        )
    
    except httpx.HTTPStatusError as e:
        error_msg = f"Canvas API Error: HTTP {e.response.status_code}. Please check your CANVAS_TOKEN validity."
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred during Canvas sync: {str(e)}"
        logger.error(f"Canvas sync failed: {e}")
        raise HTTPException(status_code=500, detail=error_msg)


# --- NEW: Endpoint to sync files for a specific course (from previous response) ---
@app.post("/api/canvas/courses/{local_course_id}/sync-files")
async def sync_course_files(
    local_course_id: int,
    db: DBSession
):
    db_service = get_db_service()
    
    course = db.query(Course).filter_by(id=local_course_id).first()
    if not course or not course.canvas_id:
        raise HTTPException(
            status_code=404,
            detail=f"Course with local ID {local_course_id} not found or has no Canvas ID."
        )

    canvas_token = CANVAS_TOKEN
    if not canvas_token:
        raise HTTPException(
            status_code=500,
            detail="CANVAS_TOKEN environment variable not set. Cannot connect to Canvas."
        )

    try:
        canvas_service = get_canvas_service(canvas_token)
        if not canvas_service:
            raise Exception("Canvas Service Initialization failed.")
            
        canvas_files = await canvas_service.get_course_files(course.canvas_id)
        
        if not canvas_files:
            return JSONResponse(
                status_code=200,
                content={"message": f"No files found on Canvas for course '{course.name}' ({course.canvas_id}). 0 modules synced."}
            )

        synced_count = db_service.sync_modules_from_canvas_files(db, local_course_id, canvas_files)

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully synced {synced_count} file(s) from Canvas to course '{course.name}' modules.",
                "total_files_found": len(canvas_files)
            }
        )
    
    except httpx.HTTPStatusError as e:
        error_msg = f"Canvas API Error: HTTP {e.response.status_code}. Please check your CANVAS_TOKEN or course ID validity."
        logger.error(f"Canvas file sync failed for course {local_course_id}: {e}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred during Canvas file sync: {str(e)}"
        logger.error(f"Canvas file sync failed for course {local_course_id}: {e}")
        raise HTTPException(status_code=500, detail=error_msg)

# --- NEW: Endpoint to download a specific module file ---
@app.post("/api/canvas/modules/{local_module_id}/download")
async def download_module_file(
    local_module_id: int,
    db: DBSession
):
    db_service = get_db_service()
    
    # 1. Retrieve the module and course details from the database
    module = db.query(Module).filter_by(id=local_module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail=f"Module with ID {local_module_id} not found.")

    course = module.course
    if not course:
        raise HTTPException(status_code=500, detail="Associated course not found for this module.")
        
    if not module.file_url:
        raise HTTPException(status_code=400, detail="Module does not have a Canvas download URL.")

    if module.is_downloaded:
        return JSONResponse(
            status_code=200,
            content={"message": f"File '{module.name}' is already downloaded."}
        )

    canvas_token = CANVAS_TOKEN
    if not canvas_token:
        raise HTTPException(
            status_code=500,
            detail="CANVAS_TOKEN environment variable not set. Cannot connect to Canvas."
        )

    try:
        # 2. Determine the save path: backend/download/{sanitized_course_name}/{module_name}
        course_folder_name = sanitize_path_name(course.name)
        file_path_name = module.name # Use the display name provided by Canvas
        
        # Construct the final absolute path
        local_dir = DOWNLOAD_BASE_DIR / course_folder_name
        local_file_path = local_dir / file_path_name

        # 3. Download the file
        canvas_service = get_canvas_service(canvas_token)
        if not canvas_service:
            raise Exception("Canvas Service Initialization failed.")
            
        await canvas_service.download_file(
            file_url=module.file_url,
            save_path=local_file_path
        )

        # 4. Update the database status
        db_service.update_module_download_status(db, local_module_id, is_downloaded=True)

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully downloaded '{module.name}' for course '{course.name}'.",
                "local_path": str(local_file_path)
            }
        )

    except httpx.HTTPStatusError as e:
        error_msg = f"File Download Error: HTTP {e.response.status_code}. The secure URL may have expired."
        logger.error(f"File download failed for module {local_module_id}: {e}")
        # If download fails, ensure status is False
        db_service.update_module_download_status(db, local_module_id, is_downloaded=False)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred during file download: {str(e)}: {e}"
        logger.error(f"File download failed for module {local_module_id}: {e}")
        # If download fails, ensure status is False
        db_service.update_module_download_status(db, local_module_id, is_downloaded=False)
        raise HTTPException(status_code=500, detail=error_msg)


# --- NEW: Endpoint to ingest a specific module file into Supermemory ---
@app.post("/api/canvas/modules/{local_module_id}/ingest")
async def ingest_module_file(
    local_module_id: int,
    db: DBSession
):
    db_service = get_db_service()
    supermemory_service = get_supermemory_service()
    
    if not supermemory_service:
        raise HTTPException(
            status_code=503,
            detail="Supermemory service is not configured. Please check SUPERMEMORY_API_KEY."
        )
    
    # 1. Retrieve the module and course details from the database
    module = db.query(Module).filter_by(id=local_module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail=f"Module with ID {local_module_id} not found.")

    course = module.course
    if not course:
        raise HTTPException(status_code=500, detail="Associated course not found for this module.")
        
    if not module.is_downloaded:
        raise HTTPException(
            status_code=400, 
            detail="File has not been downloaded yet. Please download the file first."
        )
    
    if module.is_ingested:
        return JSONResponse(
            status_code=200,
            content={"message": f"File '{module.name}' is already ingested into Supermemory."}
        )

    # 2. Determine the local path
    course_folder_name = sanitize_path_name(course.name)
    local_file_path = DOWNLOAD_BASE_DIR / course_folder_name / module.name
    
    if not local_file_path.exists():
         raise HTTPException(
            status_code=404, 
            detail=f"Local file not found at expected path: {local_file_path}. Please try downloading again."
        )

    try:
        # 3. Extract text content from the local file
        logger.info(f"Extracting text from: {local_file_path}")
        document_content = await extract_text_from_file(local_file_path)
        
        if not document_content:
             raise Exception("Extracted document content was empty.")

        # 4. Ingest document into Supermemory
        metadata = {
            "course_name": course.name,
            "canvas_course_id": course.canvas_id,
            "module_name": module.name,
            "canvas_file_id": module.canvas_file_id,
            "local_module_id": local_module_id
        }
        
        logger.info(f"Ingesting {module.name} into Supermemory...")
        ingestion_response = await supermemory_service.ingest_document(
            content=document_content,
            filename=module.name,
            metadata=metadata
        )

        # 5. Update the database status
        db_service.update_module_ingestion_status(db, local_module_id, is_ingested=True)

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully ingested '{module.name}' for course '{course.name}' into Supermemory.",
                "supermemory_response": ingestion_response
            }
        )

    except Exception as e:
        error_msg = f"An unexpected error occurred during file ingestion: {str(e)}"
        logger.error(f"File ingestion failed for module {local_module_id}: {e}")
        # If ingestion fails, ensure status is False
        db_service.update_module_ingestion_status(db, local_module_id, is_ingested=False)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/upload-material")
async def upload_material(file: UploadFile = File(...)):
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

        # Initialize response data
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
                    and memory_status == "completed"
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
                        topics_response = await claude_service.extract_topics(extracted_text)
                else:
                    if memory_status == "queued":
                        print("[INFO] Document is still queued in Supermemory, using direct text extraction...")
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

# ============================================================================
# PERSISTENCE ENDPOINTS - Save/Load study state and progress from Supermemory
# ============================================================================

class StudyProgress(BaseModel):
    """Study progress data to persist"""
    file_id: str
    filename: str
    topics: list  # List of topics with subtopic completion status
    overall_progress: float  # Percentage complete
    last_updated: str
    title: str = "Study Progress"

@app.post("/api/study-progress/save")
async def save_study_progress(progress: StudyProgress):
    """
    Study progress endpoint (disabled - no longer saving to Supermemory)

    Progress is now stored locally in sessionStorage only.
    This endpoint remains for backward compatibility.
    """
    # No-op: Progress is stored locally in sessionStorage only
    print(f"[INFO] Study progress save request received for file_id: {progress.file_id} (not saving to Supermemory)")
    return {
        "success": True,
        "message": "Study progress tracked locally"
    }

@app.get("/api/study-progress/load/{file_id}")
async def load_study_progress(file_id: str):
    """
    Load study progress endpoint (disabled - no longer loading from Supermemory)

    Progress is now stored locally in sessionStorage only.
    This endpoint remains for backward compatibility.
    """
    # No-op: Progress is stored locally in sessionStorage only
    print(f"[INFO] Study progress load request received for file_id: {file_id} (not loading from Supermemory)")
    return {
        "success": False,
        "message": "Progress is tracked locally only",
        "progress_data": None
    }

@app.get("/api/materials/list")
async def list_uploaded_materials():
    """
    List all previously uploaded materials for the current session

    Returns a list of files the user has uploaded, allowing them to
    switch between different study materials.
    """
    try:
        supermemory_service = get_supermemory_service()
        if not supermemory_service:
            return JSONResponse(
                status_code=503,
                content={"error": "Supermemory service not available"}
            )

        print("[INFO] Listing uploaded materials...")

        # Query for all uploaded documents (not conversations or progress)
        search_results = await supermemory_service.query(
            query="uploaded document material study",
            limit=20
        )

        materials = []
        if search_results and search_results.get("results"):
            for result in search_results["results"]:
                content = result.get("content", "")
                # Filter out conversation and progress records
                if "progress" not in content.lower() and "Q:" not in content:
                    materials.append({
                        "id": result.get("id"),
                        "content_preview": content[:200],
                        "timestamp": result.get("timestamp"),
                    })

        return {
            "success": True,
            "materials": materials,
            "count": len(materials)
        }

    except Exception as e:
        print(f"[ERROR] Failed to list materials: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "materials": []
        }

@app.get("/api/courses/{local_course_id}/modules")
async def get_course_modules_list(
    local_course_id: int,
    db: DBSession
):
    db_service = get_db_service()
    
    # 1. Fetch the Course record
    course = db.query(Course).filter_by(id=local_course_id).first()
    if not course:
        # Returns a 404 if the course ID doesn't exist locally
        raise HTTPException(
            status_code=404,
            detail=f"Course with local ID {local_course_id} not found."
        )

    # 2. Fetch all Module records associated with the Course
    modules = db.query(Module).filter_by(course_id=local_course_id).all()

    # 3. Serialize the data to match the frontend's expected structure
    response_modules = []
    for module in modules:
        response_modules.append({
            "id": module.id,
            "course_id": module.course_id,
            "name": module.name,
            "completed": module.completed,
            "canvas_file_id": module.canvas_file_id,
            "file_url": module.file_url,
            "is_downloaded": module.is_downloaded,
            "is_ingested": module.is_ingested,
        })
        
    return JSONResponse(
        status_code=200,
        content={
            "courseName": course.name,
            "courseId": course.id,
            "canvasId": course.canvas_id,
            "modules": response_modules
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)