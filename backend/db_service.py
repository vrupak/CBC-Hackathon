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
        course = Course(name=course_name, user_id=owner_user_pk)
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    def add_modules_bulk(self, db, course_id: int, names: list[str]):
        for n in names:
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
