from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from collections.abc import Generator
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Update with your MySQL connection details
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/dbname"

# Configure SQLAlchemy for MySQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def init() -> None:
    try:
        logger.info("Initializing")
        db = SessionLocal()
        logger.info("Connected to db")
        # Try to create session to check if DB is awake
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise e


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Initializing service")
    init()
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()