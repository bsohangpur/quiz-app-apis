import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    # SQLite configuration
    SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'question_generator.db')
    DATABASE_URL = f'sqlite:///{SQLITE_DB_PATH}' 