import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure the data directory exists
data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
os.makedirs(data_dir, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(data_dir, 'iotlab.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()