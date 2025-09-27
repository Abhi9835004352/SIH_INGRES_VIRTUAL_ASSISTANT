from typing import List, Dict, Any, Optional, Tuple
import re
import asyncio
from datetime import datetime
import logging
import google.generativeai as genai
from .config import settings
from .database import db_manager
from .vector_store import vector_store
from .models import QueryRequest, QueryResponse


logger = logging.getLogger(__name__)


class QueryProcessor:
    def __init__(self):
        # Configure Gemini
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.gemini_model = None

        self.entities_patterns = {
            "states": [
                "andhra pradesh",
                "arunachal pradesh",
                "assam",
                "bihar",
                "chhattisgarh",
                "goa",
                "gujarat",
                "haryana",
                "himachal pradesh",
                "jharkhand",
                "karnataka",
                "kerala",
                "madhya pradesh",
                "maharashtra",
                "manipur",
                "meghalaya",
                "mizoram",
                "nagaland",
                "odisha",
                "punjab",
                "rajasthan",
                "sikkim",
                "tamil nadu",
                "telangana",
                "tripura",
                "uttar pradesh",
                "uttarakhand",
                "west bengal",
                "delhi",
                "chandigarh",
                "dadra and nagar haveli",
                "daman and diu",
                "lakshadweep",
                "puducherry",
                "andaman and nicobar islands",
                "jammu and kashmir",
                "ladakh",
            ],
            "metrics": [
                "rainfall",
                "ground water extraction",
                "groundwater extraction",
                "annual extractable ground water resources",
                "water resources",
                "precipitation",
                "aquifer",
                "bore well",
                "tube well",
            ],
            "years": ["2024", "2025", "2023", "2022", "2021"],
        }

    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Main query processing pipeline"""
        start_time = datetime.utcnow()

        try:
            # Step 1: Preprocess and extract entities/intent
            entities = self._extract_entities(request.query)
            intent = self._classify_intent(request.query)

            # Step 2: Handle special intents (greeting, farewell, help) without data retrieval
            if intent in ["greeting", "farewell", "help"]:
                answer = await self._generate_answer(request.query, "", intent)
                response_time = (datetime.utcnow() - start_time).total_seconds()

                return QueryResponse(
                    answer=answer,
                    sources=[],
                    confidence_score=1.0,  # High confidence for direct responses
                    response_time=response_time,
                )

            # Step 3: For technical queries, do structured retrieval
            structured_results = await self._retrieve_structured_data(
                request.query, entities
            )

            # Step 4: For technical queries, do unstructured retrieval
            unstructured_results = self._retrieve_unstructured_data(request.query)

            # Step 5: Build context
            context = self._build_context(
                structured_results, unstructured_results, entities
            )

            # Step 6: Generate answer using LLM
            answer = await self._generate_answer(request.query, context, intent)

            # Step 7: Compile sources
            sources = self._compile_sources(structured_results, unstructured_results)

            response_time = (datetime.utcnow() - start_time).total_seconds()

            response = QueryResponse(
                answer=answer,
                sources=sources,
                confidence_score=self._calculate_confidence(context, answer),
                response_time=response_time,
            )

            logger.info(f"Query processed successfully in {response_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return QueryResponse(
                answer="I apologize, but I encountered an error while processing your query. Please try again or rephrase your question.",
                sources=[],
                confidence_score=0.0,
                response_time=(datetime.utcnow() - start_time).total_seconds(),
            )
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from the query"""
        entities = {"states": [], "metrics": [], "years": []}

        query_lower = query.lower()

        # Extract states
        for state in self.entities_patterns["states"]:
            if state in query_lower:
                entities["states"].append(state)

        # Extract metrics
        for metric in self.entities_patterns["metrics"]:
            if metric in query_lower:
                entities["metrics"].append(metric)

        # Extract years
        for year in self.entities_patterns["years"]:
            if year in query_lower:
                entities["years"].append(year)

        return entities

    def _classify_intent(self, query: str) -> str:
        """Classify user intent with improved accuracy"""
        query_lower = query.lower()
        
        # Help patterns - FIXED (check before greetings to avoid conflicts)
        help_patterns = ["help", "how to use", "guide", "tutorial", "assistance", "support"]
        help_questions = ["how to use this", "how do i", "can you help", "need help", "how to"]
        if (any(help_pattern in query_lower for help_pattern in help_patterns) or 
            any(help_q in query_lower for help_q in help_questions)):
            return "help"
        
        # Greeting patterns (moved after help to avoid conflicts)
        greeting_patterns = ["hi", "hello", "hey", "namaste", "good morning", "good evening", "greetings"]
        if any(greeting in query_lower for greeting in greeting_patterns):
            return "greeting"
        
        # Farewell patterns
        farewell_patterns = ["bye", "goodbye", "see you", "farewell", "take care"]
        if any(farewell in query_lower for farewell in farewell_patterns):
            return "farewell"
        
        # Comparison patterns  
        comparison_patterns = ["compare", " vs ", " versus ", "difference between", "compare between"]
        if any(pattern in query_lower for pattern in comparison_patterns):
            return "comparison"
        
        # STATISTICS patterns (highest priority for data queries)
        data_request_patterns = [
            "what is rainfall", "rainfall in", "rainfall data", "rainfall for",
            "what is groundwater", "groundwater in", "groundwater data", "groundwater for", 
            "show me", "give me", "tell me about", "data for", "information for",
            "statistics for", "stats for", "how much rain", "rain in"
        ]
        
        # If query contains any data request pattern, classify as statistics
        if any(pattern in query_lower for pattern in data_request_patterns):
            return "statistics"
        
        # Additional statistics indicators
        stats_keywords = ["rainfall", "groundwater", "extraction", "resources", "data", "statistics", "mm", "cubic"]
        state_mentioned = any(state in query_lower for state in self.entities_patterns["states"])
        metric_mentioned = any(metric in query_lower for metric in self.entities_patterns["metrics"])
        
        # If query mentions state + metric, it's likely a statistics query
        if state_mentioned and (metric_mentioned or any(keyword in query_lower for keyword in stats_keywords)):
            return "statistics"
        
        # EXPLANATION patterns - For concept/definition questions
        # REFINED: Only pure conceptual questions without data request indicators
        explanation_patterns = [
            "how does", "what does", "explain", "definition of", "meaning of",
            "what are the", "how do", "why does", "process of"
        ]
        
        # More specific definition patterns that should be explanations
        definition_patterns = ["what is groundwater extraction", "what is water cycle", "what is"]
        
        # Check for pure definition questions (without state/data context)
        if any(pattern in query_lower for pattern in definition_patterns):
            # If it's asking "what is X" without mentioning specific locations/data
            if not state_mentioned and not any(data_word in query_lower for data_word in ["data", "in ", "for "]):
                return "explanation"
        
        if any(pattern in query_lower for pattern in explanation_patterns):
            # But if it also contains data request patterns, prioritize statistics
            if not any(pattern in query_lower for pattern in data_request_patterns):
                return "explanation"
            else:
                return "statistics"  # Data request takes priority
        
        # Default classification based on content
        if any(keyword in query_lower for keyword in ["rainfall", "groundwater", "extraction", "data"]):
            return "statistics"
        
        return "general"

    async def _retrieve_structured_data(
        self, query: str, entities: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant structured data from MongoDB"""
        results = []

        # Query based on extracted entities
        if entities["states"]:
            for state in entities["states"]:
                state_data = await db_manager.query_groundwater_data(state=state)
                results.extend(state_data)
                logger.info(f"Found {len(state_data)} records for state: {state}")

        # If no specific entities, try to extract state names directly from query
        if not results:
            query_lower = query.lower()
            # Check for state names directly in the query
            for state in self.entities_patterns["states"]:
                if state in query_lower:
                    state_data = await db_manager.query_groundwater_data(state=state)
                    results.extend(state_data)
                    logger.info(
                        f"Direct match found {len(state_data)} records for state: {state}"
                    )
                    break

        # If still no results, do text search
        if not results:
            text_search_results = await db_manager.query_groundwater_data(
                text_search=query
            )
            results.extend(text_search_results)
            logger.info(f"Text search found {len(text_search_results)} records")

        logger.info(f"Total structured results: {len(results)}")
        return results[:10]  # Limit results

    def _retrieve_unstructured_data(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant unstructured data from FAISS"""
        try:
            similar_docs = vector_store.search_similar(
                query, top_k=settings.top_k_results
            )
            return similar_docs
        except Exception as e:
            logger.error(f"Error retrieving unstructured data: {e}")
            return []

    def _build_context(
        self,
        structured: List[Dict[str, Any]],
        unstructured: List[Dict[str, Any]],
        entities: Dict[str, List[str]],
    ) -> str:
        """Build context for LLM from retrieved data with better formatting"""
        context_parts = []

        logger.info(
            f"Building context with {len(structured)} structured and {len(unstructured)} unstructured results"
        )

        # Add structured data context with better formatting
        if structured:
            context_parts.append("=== GROUNDWATER DATABASE RECORDS ===")
            for i, item in enumerate(structured[:5]):  # Top 5 structured results
                logger.info(f"Processing structured item {i+1}: {list(item.keys())}")

                context_parts.append(f"\nRecord {i+1}:")

                # Handle different key casings - MORE COMPREHENSIVE
                state_key = next(
                    (
                        k
                        for k in item.keys()
                        if k.lower() in ["state", "state_name", "state_ut"]
                    ),
                    None,
                )
                rainfall_key = next(
                    (
                        k
                        for k in item.keys()
                        if "rainfall" in k.lower() or "precipitation" in k.lower()
                    ),
                    None,
                )
                extraction_key = next(
                    (
                        k
                        for k in item.keys()
                        if "extraction" in k.lower()
                        or "ground_water" in k.lower()
                        or "groundwater" in k.lower()
                    ),
                    None,
                )
                resources_key = next(
                    (
                        k
                        for k in item.keys()
                        if "resources" in k.lower() or "extractable" in k.lower()
                    ),
                    None,
                )

                # Add data with clear labels
                if state_key:
                    context_parts.append(f"  • State/UT: {item.get(state_key, 'N/A')}")
                if rainfall_key:
                    context_parts.append(
                        f"  • Annual Rainfall: {item.get(rainfall_key, 'N/A')} mm"
                    )
                if extraction_key:
                    context_parts.append(
                        f"  • Ground Water Extraction: {item.get(extraction_key, 'N/A')}"
                    )
                if resources_key:
                    context_parts.append(
                        f"  • Annual Extractable Resources: {item.get(resources_key, 'N/A')}"
                    )

                # Add ALL other numerical/important data
                for key, value in item.items():
                    if (
                        key
                        not in [
                            state_key,
                            rainfall_key,
                            extraction_key,
                            resources_key,
                            "_id",
                            "source_file",
                        ]
                        and value is not None
                        and str(value).strip() != ""
                    ):
                        # Format numeric values properly
                        if isinstance(value, (int, float)):
                            context_parts.append(f"  • {key}: {value}")
                        elif (
                            isinstance(value, str)
                            and value.replace(".", "")
                            .replace("-", "")
                            .replace(",", "")
                            .isdigit()
                        ):
                            context_parts.append(f"  • {key}: {value}")

        # Add unstructured data context
        if unstructured:
            context_parts.append("\n=== ADDITIONAL DOCUMENTS ===")
            for i, item in enumerate(unstructured[:3]):  # Top 3 unstructured results
                context_parts.append(f"\nDocument {i+1}:")
                context_parts.append(f"  • Source: {item.get('source_type', 'N/A')}")
                context_parts.append(
                    f"  • Content: {item.get('content', '')[:500]}..."  # Truncate long content
                )
                context_parts.append(
                    f"  • Relevance Score: {item.get('similarity_score', 0.0):.2f}"
                )
                context_parts.append("---")

        final_context = "\n".join(context_parts)
        logger.info(f"Built context length: {len(final_context)} characters")
        return final_context

    # Add this method to debug what's happening
    def _debug_context_and_query(
        self, query: str, context: str, intent: str
    ) -> Dict[str, Any]:
        """Debug method to see what's being passed to LLM"""
        debug_info = {
            "original_query": query,
            "intent": intent,
            "context_length": len(context),
            "context_preview": context[:500] + "..." if len(context) > 500 else context,
            "has_gemini_model": self.gemini_model is not None,
            "gemini_api_key_available": bool(settings.gemini_api_key),
        }
        logger.info(f"Debug info: {debug_info}")
        return debug_info

    async def _generate_answer(self, query: str, context: str, intent: str) -> str:
        """Generate answer using Google Gemini with better debugging"""
        try:
            # Add debugging
            debug_info = self._debug_context_and_query(query, context, intent)

            if not self.gemini_model:
                logger.warning("Gemini model not available, using fallback")
                return self._generate_fallback_answer(query, context, intent)

            # Check if we have actual context for technical queries
            if intent not in ["greeting", "farewell", "help"] and not context.strip():
                logger.warning(
                    "No context available for technical query, using fallback"
                )
                return self._generate_fallback_answer(query, context, intent)

            # Handle special intents with direct responses
            if intent == "greeting":
                prompt = f"""You are the INGRES (Integrated Groundwater Resource Information System) assistant. 
                
The user has greeted you with: "{query}"

Please respond in a friendly, welcoming manner and briefly introduce what you can help with regarding groundwater resources in India. Keep it conversational and helpful."""

            elif intent == "farewell":
                prompt = f"""You are the INGRES assistant. The user said: "{query}"

Please respond politely and encourage them to come back if they need help with groundwater information."""

            elif intent == "help":
                prompt = f"""You are the INGRES assistant. The user is asking for help: "{query}"

Please provide a helpful overview of what you can assist with regarding groundwater resources, statistics, and the INGRES system. Be specific about your capabilities."""

            else:
                # For technical queries, use context - IMPROVED PROMPT
                prompt = f"""You are INGRES Assistant, a specialized AI for India's Integrated Groundwater Resource Information System.

IMPORTANT INSTRUCTIONS:
- You MUST use the provided context data to answer the user's question
- If the context contains specific numerical data (rainfall, extraction, resources), you MUST include these exact numbers in your response
- Be specific and data-driven in your answers
- If context shows data for a specific state, provide that state's information
- Don't say "I don't have information" if the context clearly contains relevant data

CONTEXT DATA PROVIDED:
{context}

USER QUERY: {query}
INTENT: {intent}

Based on the context data above, provide a specific, helpful answer. If you see numerical data in the context, include those exact numbers in your response."""

            # Log the actual prompt being sent
            logger.info(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            logger.info(f"Prompt preview: {prompt[:200]}...")

            response = await asyncio.to_thread(
                self.gemini_model.generate_content, prompt
            )

            generated_answer = response.text.strip()
            logger.info(
                f"Gemini response received (length: {len(generated_answer)} chars)"
            )
            logger.info(f"Response preview: {generated_answer[:200]}...")

            return generated_answer

        except Exception as e:
            logger.error(f"Error generating answer with Gemini: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Context length: {len(context)}")
            return self._generate_fallback_answer(query, context, intent)

    def _generate_fallback_answer(self, query: str, context: str, intent: str) -> str:
        """Generate fallback answer when Gemini is not available"""

        # Handle special intents with predefined responses
        if intent == "greeting":
            return """Hello! Welcome to INGRES (Integrated Groundwater Resource Information System). 

I'm here to help you with information about groundwater resources in India. I can assist you with:

🔹 Groundwater statistics for different states
🔹 Rainfall data and its relationship with groundwater
🔹 Water extraction and resource availability information
🔹 Using the INGRES system and understanding reports
🔹 General groundwater management questions

What would you like to know about groundwater resources today?"""

        elif intent == "farewell":
            return """Thank you for using INGRES! If you need any more information about groundwater resources in India, feel free to ask anytime. Take care! 🌊"""

        elif intent == "help":
            return """I'm the INGRES assistant and I can help you with various groundwater-related queries:

📊 **Data & Statistics:**
- State-wise groundwater data
- Rainfall patterns and trends
- Water extraction figures
- Resource availability

🛠️ **System Help:**
- How to use INGRES platform
- Understanding reports and data
- Uploading shapefiles
- Navigation guidance

📚 **Information:**
- Groundwater management practices
- Technical terminology
- Policy and regulations

Just ask me about any specific state, data point, or general groundwater topic!"""

        # For technical queries
        if not context:
            return "I couldn't find specific information to answer your query. Please try rephrasing your question or ask about specific states or groundwater metrics like rainfall, extraction, or resources."

        # Template-based responses for technical queries
        if intent == "statistics" and "state" in context.lower():
            return "Based on the available data, here are the groundwater statistics for the requested region. The data includes rainfall patterns, groundwater extraction figures, and annual extractable resources. Please refer to the sources for detailed numbers and specific metrics."
        elif intent == "comparison":
            return "I can help you compare groundwater data between different states or regions. The comparison would include rainfall patterns, extraction rates, and available resources. Please specify which states or metrics you'd like to compare."
        elif intent == "explanation":
            return "I can explain various aspects of groundwater management and the INGRES system. This includes how data is collected, what different metrics mean, and how to interpret the results."
        else:
            return "Based on the available information in our groundwater database, I found some relevant data for your query. The information includes state-wise statistics, rainfall data, and resource availability figures."

    def _compile_sources(
        self, structured: List[Dict[str, Any]], unstructured: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compile source information for the response"""
        sources = []

        for item in structured:
            sources.append(
                {
                    "type": "structured",
                    "source": "INGRES Database",
                    "content": f"Groundwater data for {item.get('state', 'Unknown')}",
                    "metadata": item,
                }
            )

        for item in unstructured:
            sources.append(
                {
                    "type": "unstructured",
                    "source": item.get("source", "Unknown"),
                    "source_type": item.get("source_type", "Unknown"),
                    "relevance_score": item.get("similarity_score", 0.0),
                    "content": item.get("content", "")[:200]
                    + "...",  # Truncated content
                }
            )

        return sources

    def _calculate_confidence(self, context: str, answer: str) -> float:
        """Calculate confidence score for the response"""
        if not context or not answer:
            return 0.1

        # Simple heuristic based on context length and answer specificity
        context_score = min(len(context) / 1000, 1.0)  # Normalize by 1000 chars
        answer_score = min(len(answer) / 200, 1.0)  # Normalize by 200 chars

        # Check for specific data in answer
        specificity_score = 0.0
        if any(char.isdigit() for char in answer):
            specificity_score += 0.3
        if any(
            word in answer.lower()
            for word in ["state", "rainfall", "groundwater", "ham", "mm"]
        ):
            specificity_score += 0.2

        confidence = context_score * 0.4 + answer_score * 0.3 + specificity_score * 0.3
        return round(confidence, 2)


# Global query processor instance
query_processor = QueryProcessor()
