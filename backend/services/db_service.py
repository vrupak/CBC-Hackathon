from models import SessionLocal, User, Course, Module

class DBService:
    def session(self):
        return SessionLocal()

    # ---- User Helpers ----
    def ensure_user(self, db, user_id: str, api_key: str):
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(user_id=user_id, api_key=api_key)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    # ---- Course Helpers ----
    def create_course(self, db, owner_user_pk: int, course_name: str):
        # NOTE: This should be renamed to get_or_create_course 
        # based on your requirements to reuse courses.
        course = db.query(Course).filter_by(name=course_name, user_id=owner_user_pk).first()
        if not course:
            course = Course(name=course_name, user_id=owner_user_pk)
            db.add(course)
            db.commit()
            db.refresh(course)
        return course

    # ---- NEW: Get Course List ----
    def get_all_user_courses(self, db, user_pk: int):
        return db.query(Course).filter_by(user_id=user_pk).all()
        
    # ---- Module Helpers ---- (Modified for topic persistence)
    def add_modules_bulk(self, db, course_id: int, topics_data: list[dict]):
        # This assumes topics_data is the parsed Claude JSON list of TopicData
        # where each TopicData has subtopics
        module_names = []
        for topic in topics_data:
            # Main Topic
            module_names.append(topic['title'])
            # Subtopics (if you want them as individual modules)
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
