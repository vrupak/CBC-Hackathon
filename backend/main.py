from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import Optional, Annotated
import httpx 
from dotenv import load_dotenv

from services.supermemory_service import SupermemoryService 
from services.claude_service import ClaudeService 
from services.db_service import DBService 
from services.canvas_service import CanvasService 
from models import init_db, SessionLocal, Course, Module # User model removed

# Load environment variables globally
load_dotenv()
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")

app = FastAPI(title="AI Study Buddy API (Single-User)", version="1.0.0")

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
            print(f"[WARN] Supermemory service not available: {e}")
    return _supermemory_service

def get_claude_service() -> Optional[ClaudeService]:
    """Get or initialize Claude service (relies on ANTHROPIC_API_KEY from env)"""
    global _claude_service
    if _claude_service is None:
        try:
            # Note: API Key is loaded from environment by the service itself
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
    # Initialize the database and create all tables (only Course and Module now)
    print("[INFO] Initializing SQLAlchemy database...")
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
            "courseId": course.id, 
            "progress": course.progress,
            "total_modules": course.total_modules,
            "module_count": len(modules),
            "last_upload_filename": "N/A" # Placeholder
        })
        
    return {"courses": response_courses, "status": "single-user mode"} 

# --- Removed: save-canvas-token and canvas-token-status endpoints ---


# --- Updated: Endpoint to fetch courses from Canvas API ---
@app.post("/api/fetch-canvas-courses")
async def fetch_canvas_courses(db: DBSession):
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
                # user_pk removed
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