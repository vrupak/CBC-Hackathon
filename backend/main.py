from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field # Import Pydantic BaseModel for POST body
import os
from pathlib import Path
from typing import Optional, Annotated, List
import httpx 
from dotenv import load_dotenv
import logging
import re

from services.supermemory_service import SupermemoryService 
from services.claude_service import ClaudeService 
from services.db_service import DBService 
from services.canvas_service import CanvasService 
from utils.file_processor import extract_text_from_file # CORRECTED IMPORT PATH
from models import init_db, SessionLocal, Course, Module, DB_PATH # DB_PATH imported

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


# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
async def upload_material(
    db: DBSession, 
    file: UploadFile = File(...),
    courseId: str = Form("TEMP_ID"),
    courseName: str = Form("New Uploaded Material")
):
    # Functionality is disabled as requested
    raise HTTPException(
        status_code=403,
        detail="File upload is temporarily disabled as the system transitions to Canvas integration."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)