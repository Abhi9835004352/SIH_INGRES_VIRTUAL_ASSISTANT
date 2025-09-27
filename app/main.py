from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uuid
from datetime import datetime
import os

from .config import settings
from .models import QueryRequest, QueryResponse, FeedbackRequest
from .database import db_manager
from .vector_store import vector_store
from .preprocessor import preprocessor
from .rag_engine_langchain import get_query_processor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting INGRES RAG Chatbot API...")

    try:
        # Initialize database connection and indexes
        await db_manager.initialize()
        await db_manager.create_indexes()

        # Load or create vector store
        if not vector_store.load_index():
            logger.info("No existing vector store found. Processing data...")
            await preprocessor.process_all_data()
        else:
            logger.info("Vector store loaded successfully")

        logger.info("API startup completed successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down INGRES RAG Chatbot API...")
        await db_manager.close()


# Create FastAPI app with lifespan
app = FastAPI(
    title="INGRES RAG Chatbot API",
    description="Retrieval-Augmented Generation chatbot for INGRES groundwater information system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure according to your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "INGRES RAG Chatbot API is running",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check vector store
        vector_stats = vector_store.get_stats()

        # Check preprocessing stats
        preprocessing_stats = preprocessor.get_processing_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "vector_store": {
                    "status": (
                        "healthy" if vector_stats["total_documents"] > 0 else "warning"
                    ),
                    "stats": vector_stats,
                },
                "data_processor": {"status": "healthy", "stats": preprocessing_stats},
                "database": {
                    "status": "healthy"  # Add actual DB health check if needed
                },
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a user query and return AI-generated response"""
    query_processor = get_query_processor()
    try:
        # Generate session ID if not provided
        if not request.session_id:
            request.session_id = str(uuid.uuid4())

        logger.info(
            f"Processing query from session {request.session_id}: {request.query[:100]}..."
        )

        # Process the query
        response = await query_processor.process_query(request)

        # Log the interaction (could be stored in DB for analytics)
        logger.info(
            f"Query processed successfully. Response length: {len(response.answer)}"
        )

        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Error processing query")


@app.post("/feedback")
async def store_feedback(feedback: FeedbackRequest):
    """Store user feedback for query responses"""
    try:
        success = await db_manager.store_feedback(feedback)

        if success:
            logger.info(f"Feedback stored: Rating {feedback.rating}/5")
            return {"message": "Feedback stored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store feedback")

    except Exception as e:
        logger.error(f"Error storing feedback: {e}")
        raise HTTPException(status_code=500, detail="Error storing feedback")


@app.get("/stats")
async def get_system_stats():
    """Get system statistics and performance metrics"""
    try:
        vector_stats = vector_store.get_stats()
        preprocessing_stats = preprocessor.get_processing_stats()

        return {
            "vector_store": vector_stats,
            "data_processing": preprocessing_stats,
            "api_info": {
                "title": app.title,
                "version": app.version,
                "openapi_version": app.openapi_version,
            },
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving system statistics"
        )


@app.post("/reprocess-data")
async def reprocess_data(background_tasks: BackgroundTasks):
    """Reprocess all data (admin endpoint)"""
    try:
        background_tasks.add_task(preprocessor.process_all_data)

        return {
            "message": "Data reprocessing started in background",
            "status": "processing",
        }
    except Exception as e:
        logger.error(f"Error starting data reprocessing: {e}")
        raise HTTPException(status_code=500, detail="Error starting data reprocessing")


@app.get("/search/structured")
async def search_structured_data(
    state: str = None, year: str = None, text_search: str = None
):
    """Search structured groundwater data"""
    try:
        results = await db_manager.query_groundwater_data(
            state=state, year=year, text_search=text_search
        )

        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error searching structured data: {e}")
        raise HTTPException(status_code=500, detail="Error searching structured data")


@app.get("/search/unstructured")
async def search_unstructured_data(query: str, top_k: int = 5):
    """Search unstructured data using vector similarity"""
    try:
        retriever = vector_store.as_retriever()
        if retriever:
            results = await retriever.ainvoke(query, top_k=top_k)
        else:
            results = []

        return {"results": results, "count": len(results), "query": query}
    except Exception as e:
        logger.error(f"Error searching unstructured data: {e}")
        raise HTTPException(status_code=500, detail="Error searching unstructured data")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
