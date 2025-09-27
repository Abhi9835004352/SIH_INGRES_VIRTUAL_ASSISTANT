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
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


class LangchainQueryProcessor:
    def __init__(self):
        if settings.gemini_api_key:
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.gemini_api_key)
        else:
            self.llm = None

        # Load or initialize vector store
        if not vector_store.load_index():
            logger.warning("No vector store found. Run data preprocessing first.")
            
        self.retriever = vector_store.as_retriever()
        if self.retriever is None:
            logger.error("Could not initialize retriever. Vector store is empty.")
            
        self.prompt = self.create_prompt_template()
        self.rag_chain = self.create_rag_chain() if self.retriever and self.llm else None

    def create_prompt_template(self):
        template = """You are INGRES Assistant, a specialized AI for India's Integrated Groundwater Resource Information System.

IMPORTANT INSTRUCTIONS:
- You MUST use the provided context data to answer the user's question
- If the context contains multiple years of data for the same location, PRIORITIZE the most recent year (2024-2025 over 2023-2024)
- If the context shows data with 0.0 extraction values alongside data with actual values, use the data with actual non-zero values
- If the context contains specific numerical data (rainfall, extraction, resources), you MUST include these exact numbers in your response
- Be specific and data-driven in your answers
- If context shows data for a specific state, provide that state's information
- Don't say "I don't have information" if the context clearly contains relevant data
- When multiple data points exist for the same state, prioritize the most complete and recent dataset
- For comparison queries, SEARCH THE ENTIRE CONTEXT for all relevant states/locations mentioned
- If asked to compare multiple states/locations, ensure you find and present data for ALL requested entities

CONTEXT DATA PROVIDED:
{context}

USER QUERY: {question}


Based on the context data above, provide a specific, helpful answer. If you see multiple data entries for the same location, use the most recent and complete data with actual non-zero values. For comparison queries, make sure to extract and present data for ALL requested states/locations found in the context. Include exact numbers from the context in your response."""
        return ChatPromptTemplate.from_template(template)

    def create_rag_chain(self):
        if not self.retriever or not self.llm:
            return None
            
        return (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    async def process_query(self, request: QueryRequest) -> QueryResponse:
        start_time = datetime.utcnow()

        try:
            # Check if this is a comparison query that might need enhanced retrieval
            is_comparison = any(keyword in request.query.lower() for keyword in 
                              ['compare', 'comparison', 'between', 'vs', 'versus', 'and'])
            
            if is_comparison and self.retriever:
                # For comparison queries, get more documents to ensure both entities are captured
                enhanced_retriever = vector_store.vector_store.as_retriever(search_kwargs={"k": 12})
                enhanced_chain = (
                    {"context": enhanced_retriever, "question": RunnablePassthrough()}
                    | self.prompt
                    | self.llm
                    | StrOutputParser()
                )
                answer = await enhanced_chain.ainvoke(request.query)
            elif self.rag_chain:
                answer = await self.rag_chain.ainvoke(request.query)
            else:
                answer = "The system is not properly initialized. Please run data preprocessing first or check the configuration."

            response_time = (datetime.utcnow() - start_time).total_seconds()

            response = QueryResponse(
                answer=answer,
                sources=[],  # TODO: Implement source retrieval
                confidence_score=0.9,  # TODO: Implement confidence score
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

# Global query processor instance
query_processor_langchain = None

def get_query_processor():
    global query_processor_langchain
    if query_processor_langchain is None:
        query_processor_langchain = LangchainQueryProcessor()
    return query_processor_langchain
