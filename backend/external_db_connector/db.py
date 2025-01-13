from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from collections.abc import Generator
import logging
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

def get_db_configs_from_env() -> Dict[str, Dict[str, str]]:
    """
    Parse database configurations from environment variables.
    Expected format:
    DB_1_NAME=db1
    DB_1_URL=mysql+pymysql://user1:password1@db1_host:3306/db1_name
    DB_2_NAME=db2
    DB_2_URL=mysql+pymysql://user2:password2@db2_host:3306/db2_name
    """
    db_configs = {}
    i = 1
    
    while True:
        db_name = os.getenv(f'DB_{i}_NAME')
        db_url = os.getenv(f'DB_{i}_URL')
        
        if not db_name or not db_url:
            break
            
        db_configs[db_name] = {
            "url": db_url
        }
        i += 1
    
    if not db_configs:
        raise ValueError("No database configurations found in environment variables")
    
    return db_configs

# Get database configurations from environment
DB_CONFIGS = get_db_configs_from_env()

# Store engine and session makers for each database
engines: Dict[str, Any] = {}
session_makers: Dict[str, Any] = {}

# Initialize engines and session makers
for db_name, config in DB_CONFIGS.items():
    engines[db_name] = create_engine(config["url"])
    session_makers[db_name] = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engines[db_name]
    )

def get_db(db_name: str) -> Generator:
    """
    Get database session for specified database
    """
    if db_name not in session_makers:
        raise ValueError(f"Unknown database: {db_name}")
    
    try:
        db = session_makers[db_name]()
        yield db
    finally:
        db.close()

def init() -> None:
    """
    Initialize connections to all databases
    """
    try:
        logger.info("Initializing database connections")
        for db_name, session_maker in session_makers.items():
            try:
                db = session_maker()
                db.execute(text("SELECT 1"))
                db.close()
                logger.info(f"Successfully connected to {db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to {db_name}: {str(e)}")
                raise e
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