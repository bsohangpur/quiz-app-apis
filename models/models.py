from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import uuid
import json

Base = declarative_base()

class UserModel(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)

class SessionModel(Base):
    __tablename__ = 'sessions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    questions = relationship("QuestionModel", order_by="QuestionModel.id", back_populates="session")

class QuestionModel(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('sessions.id'), nullable=False)
    question = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    answer = Column(Text, nullable=False)  # Will store JSON string for structured answers
    explanation = Column(Text, nullable=True)
    
    options = Column(Text, nullable=True)  # For MCQ options
    match_the_following_pairs = Column(Text, nullable=True)  # For matching pairs
    sequence_items = Column(Text, nullable=True)  # For sequence questions

    session = relationship("SessionModel", back_populates="questions")

    def set_answer(self, answer):
        """Serialize answer based on question type"""
        if answer is not None:
            if self.type in ["sequence", "match_the_following"]:
                self.answer = json.dumps(answer)
            else:
                self.answer = str(answer)

    def get_answer(self):
        """Deserialize answer based on question type"""
        if self.type in ["sequence", "match_the_following"]:
            try:
                return json.loads(self.answer)
            except:
                return self.answer
        return self.answer

    def set_options(self, options):
        """Serialize options to JSON string"""
        if options is not None:
            self.options = json.dumps(options)

    def get_options(self):
        """Deserialize options from JSON string"""
        return json.loads(self.options) if self.options else None

    def set_match_pairs(self, pairs):
        """Serialize matching pairs to JSON string"""
        if pairs is not None:
            self.match_the_following_pairs = json.dumps(pairs)

    def get_match_pairs(self):
        """Deserialize matching pairs from JSON string"""
        return json.loads(self.match_the_following_pairs) if self.match_the_following_pairs else None

    def set_sequence_items(self, items):
        """Serialize sequence items to JSON string"""
        if items is not None:
            self.sequence_items = json.dumps(items)

    def get_sequence_items(self):
        """Deserialize sequence items from JSON string"""
        return json.loads(self.sequence_items) if self.sequence_items else None

SessionModel.questions = relationship("QuestionModel", order_by=QuestionModel.id, back_populates="session")

# Database connection setup
DATABASE_URL = "sqlite:///application.db"
engine = create_engine(DATABASE_URL)

Session = sessionmaker(bind=engine)
db_session = Session()

def init_db():
    """Initialize the database by creating all tables."""
    print("Initializing database...")
    print("Please use 'alembic upgrade head' to initialize the database!")