"""Mock database for development when MongoDB Atlas is unavailable"""
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class MockDatabaseManager:
    """Mock database that simulates MongoDB operations"""
    
    def __init__(self):
        self._initialized = False
        self.mock_data = {
            "bihar": {"state": "Bihar", "rainfall": 1202.46, "groundwater_level": 12.5},
            "maharashtra": {"state": "Maharashtra", "rainfall": 1039.98, "groundwater_level": 15.2},
            "rajasthan": {"state": "Rajasthan", "rainfall": 431.23, "groundwater_level": 8.9},
            "punjab": {"state": "Punjab", "rainfall": 617.85, "groundwater_level": 18.3},
        }
    
    async def initialize(self):
        """Mock initialization"""
        if self._initialized:
            return
        
        logger.info("🔗 Using mock database (MongoDB Atlas unavailable)")
        logger.info("✅ Mock database initialized successfully")
        self._initialized = True
    
    async def query_groundwater_data(self, state: str = None, **kwargs) -> List[Dict[str, Any]]:
        """Mock groundwater data query"""
        if not self._initialized:
            await self.initialize()
        
        if state:
            state_key = state.lower().strip()
            if state_key in self.mock_data:
                return [self.mock_data[state_key]]
            else:
                logger.info(f"No mock data for state: {state}")
                return []
        
        # Return all data if no state specified
        return list(self.mock_data.values())
    
    async def store_conversation(self, session_id: str, query: str, response: str):
        """Mock conversation storage"""
        logger.info(f"Mock: Stored conversation for session {session_id}")
    
    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Mock conversation history"""
        return []  # Return empty history for now
    
    async def store_feedback(self, session_id: str, rating: int, feedback: str):
        """Mock feedback storage"""
        logger.info(f"Mock: Stored feedback with rating {rating}")
    
    async def close(self):
        """Mock close operation"""
        logger.info("Mock database connection closed")
        self._initialized = False

# For quick testing - replace the real DatabaseManager
DatabaseManager = MockDatabaseManager