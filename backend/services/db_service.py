from models import SessionLocal, Course, Module
import os
from dotenv import load_dotenv

# Load .env variables (needed here for accessing CANVAS_TOKEN if logic was present, 
# but mostly retained for context consistency)
load_dotenv()
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

class DBService:
    def session(self):
        return SessionLocal()

    # ---- User Helpers (All removed) ----

    # ---- Course Helpers ----
    # User PK parameter removed
    def create_course(self, db, course_name: str):
        """Creates a course record (typically for a manual upload)."""
        # We assume one app instance, so filtering is only by name and canvas_id=None
        course = db.query(Course).filter_by(name=course_name, canvas_id=None).first()
        if not course:
            course = Course(name=course_name)
            db.add(course)
            db.commit()
            db.refresh(course)
        return course

    # User PK parameter removed
    def get_or_create_course_from_canvas(self, db, course_name: str, canvas_id: str):
        """Gets or creates a course record linked to a Canvas ID."""
        # Now only filters by canvas_id globally
        course = db.query(Course).filter_by(canvas_id=canvas_id).first()
        if not course:
            course = Course(
                name=course_name, 
                canvas_id=canvas_id, 
                progress=0, 
                total_modules=0
            )
            db.add(course)
            db.commit()
            db.refresh(course)
        return course
    
    def get_all_canvas_ids(self, db) -> set[str]:
        """Returns a set of all canvas_id strings currently stored locally."""
        # Use query(Course.canvas_id) to efficiently select only the IDs
        # filter(Course.canvas_id.isnot(None)) ensures we only get Canvas-linked courses
        results = db.query(Course.canvas_id).filter(Course.canvas_id.isnot(None)).all()
        # Convert list of tuples (e.g., [('123',), ('456',)]) to a set of strings
        return {str(r[0]) for r in results if r[0] is not None}
        
    # ---- Get Course List ----
    # Renamed and simplified
    def get_all_courses(self, db):
        return db.query(Course).all()
        
    # ---- Module Helpers ---- 
    def add_modules_bulk(self, db, course_id: int, topics_data: list[dict]):
        # This function is retained but not currently used with the upload disabled
        module_names = []
        for topic in topics_data:
            module_names.append(topic['title'])
            for subtopic in topic.get('subtopics', []):
                 module_names.append(f"{topic['title']}: {subtopic['title']}")

        for n in module_names:
            module = Module(course_id=course_id, name=n, completed=False)
            db.add(module)
        db.commit()

    def recompute_course_progress(self, db, course_id: int):
        course = db.query(Course).filter_by(id=course_id).first()
        if course:
            total = db.query(Module).filter_by(course_id=course_id).count()
            done = db.query(Module).filter_by(course_id=course_id, completed=True).count()
            course.total_modules = total
            course.progress = int((done / total) * 100) if total else 0
            db.commit()