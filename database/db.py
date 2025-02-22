from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import logging
from typing import Optional
from sqlalchemy import inspect

from .models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.engine = create_engine('sqlite:///cardsnap.db')
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(self.SessionFactory)
        self._initialized = True
    
    def init_db(self):
        """Initialize the database, creating all tables."""
        try:
            # Create all tables if they don't exist
            Base.metadata.create_all(self.engine)
            logger.info("Database initialized successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def reset_db(self):
        """Reset the database by dropping all tables and recreating them."""
        try:
            # Drop all tables
            Base.metadata.drop_all(self.engine)
            # Create all tables
            Base.metadata.create_all(self.engine)
            logger.info("Database reset successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error resetting database: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
            self.Session.remove()
    
    def add_item(self, item):
        """Add a single item to the database."""
        with self.get_session() as session:
            try:
                session.add(item)
                session.commit()
                session.refresh(item)
                return item
            except SQLAlchemyError as e:
                logger.error(f"Error adding item to database: {e}")
                raise
    
    def get_item_by_id(self, model, item_id: int):
        """Get an item by its ID."""
        with self.get_session() as session:
            try:
                return session.query(model).filter(model.id == item_id).first()
            except SQLAlchemyError as e:
                logger.error(f"Error retrieving item from database: {e}")
                raise
    
    def update_item(self, item):
        """Update an existing item in the database."""
        with self.get_session() as session:
            try:
                merged_item = session.merge(item)
                session.commit()
                session.refresh(merged_item)
                return merged_item
            except SQLAlchemyError as e:
                logger.error(f"Error updating item in database: {e}")
                raise
    
    def delete_item(self, item):
        """Delete an item from the database."""
        with self.get_session() as session:
            try:
                session.delete(item)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error deleting item from database: {e}")
                raise
    
    def get_all_items(self, model):
        """Get all items of a specific model."""
        with self.get_session() as session:
            try:
                return session.query(model).all()
            except SQLAlchemyError as e:
                logger.error(f"Error retrieving items from database: {e}")
                raise

# Create a global instance of DatabaseManager
db = DatabaseManager() 