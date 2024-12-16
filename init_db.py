from models.models import  User, Session, Question, Base, engine

def setup_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    setup_database() 