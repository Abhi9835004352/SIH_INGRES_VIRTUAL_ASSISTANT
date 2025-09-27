#!/usr/bin/env python3
"""Test MongoDB connection with updated SSL configuration"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import DatabaseManager

async def test_connection():
    """Test MongoDB connection"""
    try:
        print("🔗 Testing MongoDB connection...")
        db_manager = DatabaseManager()
        await db_manager.initialize()
        print('✅ MongoDB connection successful!')
        
        # Test a simple query
        count = await db_manager.groundwater_collection.count_documents({})
        print(f'📊 Found {count} documents in groundwater collection')
        
        # Test a sample groundwater query
        sample = await db_manager.groundwater_collection.find_one({})
        if sample:
            print(f'📄 Sample document found: {list(sample.keys())[:5]}...')
        
        await db_manager.close()
        print('🔒 Connection closed successfully')
        return True
        
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        print("\n🎉 Database connection test passed!")
        sys.exit(0)
    else:
        print("\n💥 Database connection test failed!")
        sys.exit(1)