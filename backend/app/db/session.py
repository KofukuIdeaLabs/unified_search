from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging


logging.info("Session is being called")
engine = create_engine(
    "postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}".format(POSTGRES_USER=os.getenv("POSTGRES_USER"), POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD"), POSTGRES_SERVER=os.getenv("POSTGRES_SERVER"), POSTGRES_DB=os.getenv("POSTGRES_DB")), pool_pre_ping=True, pool_size=100, max_overflow=50
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
