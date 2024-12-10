from models.base import init_db, engine, Base
from models.models import Subject, Topic, QuestionType, QuestionSet

def setup_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    setup_database() 