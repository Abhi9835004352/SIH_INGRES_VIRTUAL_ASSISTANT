#!/usr/bin/env python3
"""
Test script to verify the comparison query fix for INGRES RAG system
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from app.rag_engine_langchain import LangchainQueryProcessor
from app.models import QueryRequest


async def test_comparison_queries():
    """Test various comparison queries to verify both states' data is retrieved"""
    
    processor = LangchainQueryProcessor()
    
    test_queries = [
        "Compare the rainfall between Karnataka and Gujarat in 2023-24",
        "What is the difference in groundwater extraction between Karnataka and Gujarat?",
        "Compare groundwater utilization between Karnataka and Gujarat",
        "How does Karnataka's rainfall compare to Gujarat's rainfall?"
    ]
    
    print("🧪 TESTING COMPARISON QUERIES")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📋 Test {i}: {query}")
        print("-" * 60)
        
        request = QueryRequest(query=query, user_id="test_user")
        response = await processor.process_query(request)
        
        # Check if both states are mentioned in the response
        response_upper = response.answer.upper()
        has_karnataka = "KARNATAKA" in response_upper
        has_gujarat = "GUJARAT" in response_upper
        
        print(f"✅ Contains Karnataka data: {has_karnataka}")
        print(f"✅ Contains Gujarat data: {has_gujarat}")
        
        if has_karnataka and has_gujarat:
            print("🎉 SUCCESS: Both states' data retrieved!")
        else:
            print("❌ ISSUE: Missing data for one or both states")
            
        print(f"\n📄 Response:\n{response.answer}")
        print(f"\n⏱️  Response time: {response.response_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_comparison_queries())