from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import aiofiles
from pathlib import Path
from typing import Optional, Annotated
import uuid
from datetime import datetime
import json

from utils.file_processor import extract_text_from_file
from services.supermemory_service import SupermemoryService
from services.claude_service import ClaudeService
# --- NEW IMPORTS ---
from services.db_service import DBService # Assuming db_service.py is now in services/
from models import init_db, SessionLocal, User, Course, Module # Assuming models.py is in backend/

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
        "database_status": db_status # NEW DB STATUS
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
    db: DBSession, # Inject SQLAlchemy Session
    file: UploadFile = File(...),
    courseId: str = Form("TEMP_ID"),
    courseName: str = Form("New Uploaded Material")
):
    file_id = None
    file_path = None
    db_service = get_db_service()
    
    # --- FIX: Initialize processing_data here ---
    processing_data = {"topics_extracted": False} 
    
    # --- TEMPORARY USER FOR DEMO ---
    user = db_service.ensure_user(db, user_id="demo_user_1", api_key=os.getenv("ANTHROPIC_API_KEY", "DUMMY_KEY"))
    
    # --- TEMPORARY COURSE LINKING ---
    # NOTE: This call must succeed or the whole process fails early.
    course_record = db_service.create_course(db, user.id, courseName)
    
    try:
        print(f"[INFO] Received upload request for file: {file.filename}, Course: {courseName}")
        
        # 1. Validation and File Saving (Existing Logic)
        # ... (rest of the file saving and text extraction logic) ...

        # The subsequent sections (Supermemory, Claude) can now update 'processing_data' safely.
        
        # ... (rest of the function, including the return) ...
        
    except HTTPException:
        # Cleanup
        if file_path and file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        print(f"[ERROR] Upload failed: {str(e)}")
        # Cleanup
        if file_path and file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)