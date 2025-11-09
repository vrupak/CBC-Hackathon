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

    # ---- Course Helpers ----
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
    def get_all_courses(self, db):
        return db.query(Course).all()
        
    # ---- Module Helpers ---- 
    def sync_modules_from_canvas_files(self, db, course_id: int, file_data: list[dict]):
        """
        Syncs the local Module table with files fetched from the Canvas API.
        It updates existing files and creates new ones.
        """
        synced_count = 0
        
        # Fetch existing canvas_file_ids for this course for faster lookup
        existing_modules = db.query(Module).filter(
            Module.course_id == course_id,
            Module.canvas_file_id.isnot(None)
        ).all()
        
        # Create a map of existing module file IDs for quick lookup
        existing_file_map = {m.canvas_file_id: m for m in existing_modules}
        
        for file in file_data:
            file_id_str = str(file.get('id'))
            
            # Filter out files without necessary data
            if not file_id_str or not file.get('display_name') or not file.get('url'):
                continue
            
            module = existing_file_map.get(file_id_str)
            
            # Data to be inserted/updated
            new_name = file.get('display_name')
            new_url = file.get('url')
            
            if module:
                # Update existing module
                if module.name != new_name or module.file_url != new_url:
                    module.name = new_name
                    module.file_url = new_url
                    # Reset download/ingestion status if the file URL has changed
                    module.is_downloaded = False
                    module.is_ingested = False
                # Do not commit yet, wait for the bulk commit
                synced_count += 1
            else:
                # Create a new module entry
                new_module = Module(
                    course_id=course_id, 
                    name=new_name, 
                    canvas_file_id=file_id_str,
                    file_url=new_url,
                    completed=False
                )
                db.add(new_module)
                synced_count += 1
        
        db.commit()
        
        # Update course total modules count
        self.recompute_course_progress(db, course_id)
        
        return synced_count
        
    # --- NEW: Update download status for a module ---
    def update_module_download_status(self, db, module_id: int, is_downloaded: bool):
        """Updates the download status for a specific module."""
        module = db.query(Module).filter_by(id=module_id).first()
        if module:
            module.is_downloaded = is_downloaded
            # If download status changes, recompute progress
            self.recompute_course_progress(db, module.course_id)
            return True
        return False
    
    # --- NEW: Update ingestion status for a module ---
    def update_module_ingestion_status(self, db, module_id: int, is_ingested: bool):
        """Updates the ingestion (Supermemory) status for a specific module."""
        module = db.query(Module).filter_by(id=module_id).first()
        if module:
            module.is_ingested = is_ingested
            # If ingestion status changes, recompute progress
            self.recompute_course_progress(db, module.course_id)
            return True
        return False


    def recompute_course_progress(self, db, course_id: int):
        course = db.query(Course).filter_by(id=course_id).first()
        if course:
            # We are now tracking study material files as modules, so total is now 
            # the count of Canvas-linked modules.
            total = db.query(Module).filter(
                Module.course_id == course_id,
                Module.canvas_file_id.isnot(None) # Only count files as modules
            ).count()
            # Assuming 'completed' means fully processed (downloaded + ingested)
            done = db.query(Module).filter(
                Module.course_id == course_id, 
                Module.is_ingested == True
            ).count()
            
            course.total_modules = total
            course.progress = int((done / total) * 100) if total else 0
            db.commit()

    # The original topic-based add_modules_bulk is now likely obsolete 
    # but retained here for backward compatibility with the original code.
    def add_modules_bulk(self, db, course_id: int, topics_data: list[dict]):
        # This function is retained but its relevance is decreasing
        module_names = []
        for topic in topics_data:
            module_names.append(topic['title'])
            for subtopic in topic.get('subtopics', []):
                 module_names.append(f"{topic['title']}: {subtopic['title']}")

        for n in module_names:
            module = Module(course_id=course_id, name=n, completed=False)
            db.add(module)
        db.commit()