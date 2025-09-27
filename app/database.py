import motor.motor_asyncio
from typing import List, Dict, Any, Optional
import pandas as pd
from .config import settings
from .models import GroundWaterData, TextChunk, ChatSession, FeedbackRequest
from datetime import datetime
import logging
import asyncio
import ssl
import certifi

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.groundwater_collection = None
        self.text_chunks_collection = None
        self.sessions_collection = None
        self.feedback_collection = None
        self._initialized = False

    async def initialize(self):
        """Initialize MongoDB connection and collections"""
        if self._initialized:
            return

        try:
            # Simple MongoDB client - let the connection string handle SSL
            logger.info("🔗 Connecting to MongoDB Atlas...")
            
            self.client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)

            # Test connection
            await self.client.admin.command("ping")
            logger.info("✅ Connected to MongoDB Atlas successfully")

            self.db = self.client[settings.database_name]
            self.groundwater_collection = self.db.groundwater_data
            self.text_chunks_collection = self.db.text_chunks
            self.sessions_collection = self.db.chat_sessions
            self.feedback_collection = self.db.feedback

            self._initialized = True

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            logger.info("🔄 Falling back to mock database...")
            # Import and use mock database
            from .mock_database import MockDatabaseManager
            mock_db = MockDatabaseManager()
            await mock_db.initialize()
            
            # Replace this instance's methods with mock methods
            self.query_groundwater_data = mock_db.query_groundwater_data
            self.store_conversation = mock_db.store_conversation
            self.get_conversation_history = mock_db.get_conversation_history
            self.store_feedback = mock_db.store_feedback
            self.close = mock_db.close
            self._initialized = True
            return

    async def create_indexes(self):
        """Create necessary indexes for optimal performance"""
        await self.initialize()

        try:
            # Create text index for groundwater data
            await self.groundwater_collection.create_index(
                [("state", "text"), ("year", 1)]
            )

            # Create indexes for text chunks
            await self.text_chunks_collection.create_index(
                [("source", 1), ("source_type", 1)]
            )

            # Create index for sessions
            await self.sessions_collection.create_index(
                [("session_id", 1), ("user_id", 1), ("last_active", -1)]
            )

            logger.info("✅ Database indexes created successfully")
            return True

        except Exception as e:
            logger.warning(
                f"⚠️  Could not create indexes (this is okay for free MongoDB clusters): {e}"
            )
            return True  # Continue even if indexing fails

    async def store_groundwater_data(self, data: List[GroundWaterData]) -> bool:
        """Store groundwater statistics in MongoDB"""
        await self.initialize()
        try:
            documents = [doc.dict() for doc in data]
            result = await self.groundwater_collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} groundwater records")
            return True
        except Exception as e:
            logger.error(f"Error storing groundwater data: {e}")
            return False

    async def store_text_chunks(self, chunks: List[TextChunk]) -> bool:
        """Store text chunks in MongoDB"""
        await self.initialize()
        try:
            documents = [chunk.dict() for chunk in chunks]
            result = await self.text_chunks_collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} text chunks")
            return True
        except Exception as e:
            logger.error(f"Error storing text chunks: {e}")
            return False

    async def query_groundwater_data(
        self,
        state: Optional[str] = None,
        year: Optional[str] = None,
        text_search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query structured groundwater data"""
        await self.initialize()
        try:
            query = {}

            if state:
                # Try different field name variations for state
                query["$or"] = [
                    {"STATE": {"$regex": state, "$options": "i"}},
                    {"State": {"$regex": state, "$options": "i"}},
                    {"state": {"$regex": state, "$options": "i"}},
                ]

            if year:
                query["year"] = year

            if text_search:
                # Use comprehensive text search across all fields
                query["$or"] = [
                    {"STATE": {"$regex": text_search, "$options": "i"}},
                    {"State": {"$regex": text_search, "$options": "i"}},
                    {"state": {"$regex": text_search, "$options": "i"}},
                    {"year": {"$regex": text_search, "$options": "i"}},
                ]

            logger.info(f"Querying groundwater data with: {query}")
            cursor = self.groundwater_collection.find(query)
            results = await cursor.to_list(length=100)
            logger.info(f"Found {len(results)} groundwater records")

            # Log first result for debugging
            if results:
                logger.info(f"Sample result keys: {list(results[0].keys())}")

            return results
        except Exception as e:
            logger.error(f"Error querying groundwater data: {e}")
            return []

    async def get_text_chunks_by_source(
        self, source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve text chunks by source type"""
        await self.initialize()
        try:
            query = {}
            if source_type:
                query["source_type"] = source_type

            cursor = self.text_chunks_collection.find(query)
            results = await cursor.to_list(length=1000)
            return results
        except Exception as e:
            logger.error(f"Error retrieving text chunks: {e}")
            return []

    async def store_chat_session(self, session: ChatSession) -> bool:
        """Store or update chat session"""
        await self.initialize()
        try:
            await self.sessions_collection.replace_one(
                {"session_id": session.session_id}, session.dict(), upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error storing chat session: {e}")
            return False

    async def store_feedback(self, feedback: FeedbackRequest) -> bool:
        """Store user feedback"""
        await self.initialize()
        try:
            feedback_doc = feedback.dict()
            feedback_doc["created_at"] = datetime.utcnow()
            await self.feedback_collection.insert_one(feedback_doc)
            return True
        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chat session by ID"""
        await self.initialize()
        try:
            session = await self.sessions_collection.find_one(
                {"session_id": session_id}
            )
            return session
        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
            return None

    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")


# Global database instance
db_manager = DatabaseManager()
