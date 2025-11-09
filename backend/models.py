# backend/models.py (Updated)

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pathlib import Path


BACKEND_DIR = Path(__file__).parent
DB_PATH = f"sqlite:///{BACKEND_DIR / 'db' / 'studybuddy_orm.db'}"

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    api_key = Column(String, nullable=False)
    
    # 🌟 NEW: Relationship to Courses
    courses = relationship("Course", back_populates="owner")
    # You will likely need a Document relationship here too, once consolidated

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    progress = Column(Integer, default=0)
    total_modules = Column(Integer, default=0)
    
    # 🌟 NEW: Relationship to User and Modules
    owner = relationship("User", back_populates="courses")
    modules = relationship("Module", back_populates="course")

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    name = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    
    # 🌟 NEW: Relationship to Course
    course = relationship("Course", back_populates="modules")

# SQLite engine setup
engine = create_engine(DB_PATH, echo=True)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    # Ensures the 'db' subdirectory exists
    Path(DB_PATH.split('sqlite:///')[-1]).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)