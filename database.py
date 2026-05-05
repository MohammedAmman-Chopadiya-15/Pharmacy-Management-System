import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL for a connection to the database
# Values actually put in .env file in a production environment
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:admin123@db:3306/MedCare"

# The engine is the starting point for any SQLAlchemy application
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True,  # Checks if connection is alive before using it
    connect_args={"connect_timeout": 10}
)

# Each instance of the SessionLocal class will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# We will inherit from this class to create each of the database models
Base = declarative_base()

# Dependency to get a DB session for our routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()