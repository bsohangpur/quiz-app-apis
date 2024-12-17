from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid
import json

Base = declarative_base()

class SessionModel(Base):
    __tablename__ = 'sessions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    questions_json = Column(Text, nullable=False)  # Store complete JSON response

    def set_questions(self, questions):
        """Store questions as JSON string"""
        self.questions_json = json.dumps(questions)

    def get_questions(self):
        """Retrieve questions from JSON string"""
        return json.loads(self.questions_json) if self.questions_json else []

# Database connection setup
DATABASE_URL = "sqlite:///application.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db_session = Session()

def init_db():
    """Initialize the database by creating all tables."""
    print("Please use 'alembic upgrade head' to initialize the database!")