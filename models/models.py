from sqlalchemy import Column, Integer, String, Text,  JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid

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
    # user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # user = relationship("UserModel", back_populates="sessions")

    questions = relationship("QuestionModel", order_by="QuestionModel.id", back_populates="session")

class QuestionModel(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('sessions.id'), nullable=False)
    question = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)  # For MCQ options
    match_the_following_pairs = Column(JSON, nullable=True)  # For matching pairs
    correct_answer = Column(JSON, nullable=True)  # For sequence answers or matching pairs

    session = relationship("SessionModel", back_populates="questions")

SessionModel.questions = relationship("QuestionModel", order_by=QuestionModel.id, back_populates="session")

# Database connection setup
DATABASE_URL = "sqlite:///application.db"  # Change to your database URL
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
# session = Session()
db_session = Session()


def init_db():
    """Initialize the database by creating all tables."""
    print("Initializing database...")
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")