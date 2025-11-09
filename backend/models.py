# backend/models.py 

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, create_engine, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pathlib import Path


BACKEND_DIR = Path(__file__).parent
DB_PATH = f"sqlite:///{BACKEND_DIR / 'db' / 'studybuddy_orm.db'}"

Base = declarative_base()

# The User model has been removed as per request.
# The application now operates in a single-user mode, loading credentials 
# (like CANVAS_TOKEN) directly from environment variables.

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # The user_id foreign key has been removed.
    progress = Column(Integer, default=0)
    total_modules = Column(Integer, default=0)
    # To store the external Canvas Course ID
    canvas_id = Column(String, nullable=True) 
    
    # The owner relationship has been removed.
    modules = relationship("Module", back_populates="course")
    
    # Since there is no user_id, we only ensure uniqueness by canvas_id for a single local application instance
    __table_args__ = (UniqueConstraint('canvas_id', name='_canvas_course_uc'),)


class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    name = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    
    # --- NEW: Canvas File Fields ---
    canvas_file_id = Column(String, nullable=True) # External file ID from Canvas
    file_url = Column(String, nullable=True)       # Secure download URL from Canvas
    is_downloaded = Column(Boolean, default=False) # Status of local file download
    is_ingested = Column(Boolean, default=False)   # Status of RAG ingestion
    
    # --- NEW: Study Path Persistence ---
    study_path_json = Column(String, nullable=True) # Stores the generated path (large JSON string)
    
    # Relationship to Course
    course = relationship("Course", back_populates="modules")

    # Add a unique constraint to prevent duplicate file records for the same course
    __table_args__ = (UniqueConstraint('course_id', 'canvas_file_id', name='_course_file_uc'),)


# SQLite engine setup
engine = create_engine(DB_PATH, echo=True)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    # Ensures the 'db' subdirectory exists
    db_file_path = Path(DB_PATH.split('sqlite:///')[-1])
    db_file_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)