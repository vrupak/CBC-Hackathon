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

from services.supermemory_service import SupermemoryService 
from services.claude_service import ClaudeService 
from services.db_service import DBService 
from services.canvas_service import CanvasService 
from models import init_db, SessionLocal, Course, Module, DB_PATH # DB_PATH imported

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables globally
load_dotenv()
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")

app = FastAPI(title="AI Study Buddy API (Single-User)", version="1.0.0")

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

# Create uploads directory if it doesn't exist
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


# --- STARTUP/SHUTDOWN EVENTS ---
@app.on_event("startup")
def startup_event():
    # --- ACTION: Reset the DB to ensure the new schema is used ---
    # This is left here to resolve the previous OperationalError. 
    # For long-term use, this should be replaced by a proper migration system.
    # Note: If you want to keep your data, comment out or remove reset_db_schema() 
    # after the initial successful run.
    reset_db_schema() 
    
    # Initialize the database and create all tables (only Course and Module now)
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
            "canvas_id": course.canvas_id, # <<< NEW: External Canvas ID (5001, 6002...)
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
        # 1. Fetch all active courses from Canvas API
        canvas_service = CanvasService(canvas_token)
        all_canvas_courses = await canvas_service.get_user_courses()
        
        # 2. Get the set of IDs already stored in the local DB
        local_canvas_ids = db_service.get_all_canvas_ids(db)
        
        # 3. Filter the Canvas courses
        available_courses = []
        for course in all_canvas_courses:
            # IMPORTANT: Use the canvas 'id' field for filtering and returning
            course_id_str = str(course.get("id"))
            
            # Check if course has a name and is not already in the local DB
            if course.get("name") and course_id_str not in local_canvas_ids:
                available_courses.append({
                    "canvas_id": course_id_str,
                    "name": course.get("name"),
                    "course_code": course.get("course_code", "N/A") # Include course code if available
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
    selection: CourseSelection # Uses the Pydantic model for validation
):
    db_service = get_db_service()
    imported_count = 0
    
    # Fetch all courses from Canvas API one last time to get the names for the IDs
    try:
        canvas_service = CanvasService(CANVAS_TOKEN)
        all_canvas_courses = await canvas_service.get_user_courses()
        # Map Canvas ID (string) to Course Name (string)
        canvas_course_map = {str(c.get("id")): c.get("name") for c in all_canvas_courses if c.get("id") and c.get("name")}
    except Exception as e:
        logger.error(f"Failed to verify course IDs against Canvas: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not verify course selections against Canvas. Please try again."
        )

    for course_id_str in selection.canvas_course_ids:
        # 1. Verify the ID is valid and exists on Canvas
        course_name = canvas_course_map.get(course_id_str)
        
        if course_name:
            # 2. Add the course to the local DB. The canvas_id is correctly saved here.
            db_service.get_or_create_course_from_canvas(
                db, 
                course_name=course_name, 
                canvas_id=course_id_str # This is the external Canvas ID (e.g., "5001")
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
    
    # Load token directly from environment variable
    canvas_token = CANVAS_TOKEN
    
    if not canvas_token:
        raise HTTPException(
            status_code=500,
            detail="CANVAS_TOKEN environment variable not set. Cannot connect to Canvas."
        )
    
    try:
        # Instantiate CanvasService with the environment token
        canvas_service = CanvasService(canvas_token)
        canvas_courses = await canvas_service.get_user_courses()
        
        # Save/update courses in the local DB
        imported_count = 0
        for canvas_course in canvas_courses:
            course_name = canvas_course.get("name")
            course_id = str(canvas_course.get("id"))
            
            if course_name and course_id:
                # This ensures every course found on Canvas is added locally
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
        # The original error handling here is too broad, but we keep it for unexpected errors
        error_msg = f"An unexpected error occurred during Canvas sync: {str(e)}"
        logger.error(f"Canvas sync failed: {e}")
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