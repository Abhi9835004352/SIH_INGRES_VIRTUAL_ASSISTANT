import asyncio
from app.rag_engine import query_processor
from app.models import QueryRequest

async def comprehensive_final_test():
    """Comprehensive test of the final RAG system with updated classification"""
    
    test_scenarios = [
        # Data queries - should all be 'statistics'
        {
            "query": "what is rainfall in bihar?",
            "expected_intent": "statistics",
            "expected_data": "1202.46",
            "description": "Basic rainfall query"
        },
        {
            "query": "bihar rainfall data",
            "expected_intent": "statistics", 
            "expected_data": "1202.46",
            "description": "Direct data request"
        },
        {
            "query": "show me groundwater data for bihar",
            "expected_intent": "statistics",
            "expected_data": "bihar",
            "description": "Complex data request"
        },
        {
            "query": "rainfall in maharashtra",
            "expected_intent": "statistics",
            "expected_data": "1039.98",
            "description": "State-specific query"
        },
        
        # Help queries
        {
            "query": "how to use this system?",
            "expected_intent": "help",
            "expected_data": "help",
            "description": "System usage help"
        },
        {
            "query": "help me with groundwater data",
            "expected_intent": "help", 
            "expected_data": "help",
            "description": "General help request"
        },
        
        # Explanation queries
        {
            "query": "how does groundwater work?",
            "expected_intent": "explanation",
            "expected_data": "work",
            "description": "Conceptual question"
        },
        
        # Greeting/Social
        {
            "query": "hello",
            "expected_intent": "greeting",
            "expected_data": "hello",
            "description": "Basic greeting"
        },
        
        # Comparison
        {
            "query": "compare bihar vs maharashtra rainfall",
            "expected_intent": "comparison",
            "expected_data": "compare",
            "description": "State comparison"
        }
    ]
    
    print("🚀 FINAL RAG SYSTEM COMPREHENSIVE TEST")
    print("=" * 70)
    
    total_tests = len(test_scenarios)
    passed_tests = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 TEST {i}/{total_tests}: {scenario['description']}")
        print(f"Query: '{scenario['query']}'")
        print("-" * 50)
        
        try:
            # Test intent classification
            actual_intent = query_processor._classify_intent(scenario['query'])
            intent_correct = actual_intent == scenario['expected_intent']
            
            print(f"Intent: {actual_intent} {'✅' if intent_correct else '❌'}")
            
            # Test full pipeline
            request = QueryRequest(query=scenario['query'])
            response = await query_processor.process_query(request)
            
            # Analyze response
            response_contains_expected = scenario['expected_data'].lower() in response.answer.lower()
            response_length = len(response.answer)
            sources_count = len(response.sources)
            
            print(f"Response length: {response_length} chars")
            print(f"Sources: {sources_count}")
            print(f"Confidence: {response.confidence_score:.2f}")
            print(f"Contains expected content: {'✅' if response_contains_expected else '❌'}")
            
            # Show response preview
            preview_length = 150
            preview = response.answer[:preview_length] + ("..." if len(response.answer) > preview_length else "")
            print(f"Response preview: {preview}")
            
            # Test scoring
            test_passed = intent_correct and response_contains_expected and response_length > 10
            if test_passed:
                passed_tests += 1
                print("🎯 TEST RESULT: PASSED")
            else:
                print("❌ TEST RESULT: FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    success_rate = (passed_tests / total_tests) * 100
    print("\n" + "🏆" * 20)
    print(f"FINAL SYSTEM PERFORMANCE: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    print("🏆" * 20)
    
    return success_rate

async def test_edge_cases():
    """Test edge cases and error handling"""
    
    edge_cases = [
        "rainfall data for unknown_state",  # Non-existent state
        "",  # Empty query
        "abcdefgh random nonsense",  # Gibberish
        "rainfall in bihar maharashtra punjab",  # Multiple states
        "what is the rainfall precipitation data information for bihar state?",  # Complex query
    ]
    
    print("\n🔧 TESTING EDGE CASES")
    print("=" * 40)
    
    for query in edge_cases:
        print(f"\nEdge case: '{query}'")
        try:
            request = QueryRequest(query=query)
            response = await query_processor.process_query(request)
            print(f"✅ Handled successfully: {len(response.answer)} chars")
            print(f"   Preview: {response.answer[:100]}...")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Starting comprehensive final system test...")
    success_rate = asyncio.run(comprehensive_final_test())
    asyncio.run(test_edge_cases())
    
    if success_rate >= 90:
        print("\n🎉 SYSTEM IS READY FOR PRODUCTION!")
    elif success_rate >= 80:
        print("\n⚠️ System needs minor improvements")
    else:
        print("\n❌ System needs significant improvements")