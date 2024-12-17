from models.models import Base, engine

def init_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!") 