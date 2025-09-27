#!/usr/bin/env python3
"""
Startup script for INGRES RAG Chatbot

This script initializes and starts the complete RAG system including:
- Database setup
- Data preprocessing
- Vector store initialization
- FastAPI server
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import db_manager
from app.vector_store import vector_store
from app.preprocessor import preprocessor
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_system():
    """Initialize the complete RAG system"""
    logger.info("🚀 Initializing INGRES RAG Chatbot System...")

    try:
        # 1. Check environment variables
        if not settings.gemini_api_key:
            logger.warning("⚠️  GEMINI_API_KEY not set. Using fallback responses.")

        # 2. Initialize database
        logger.info("📊 Setting up database...")
        await db_manager.create_indexes()

        # 3. Initialize or load vector store
        logger.info("🔍 Setting up vector store...")
        if not vector_store.load_index():
            logger.info("📚 No existing vector store found. Processing data...")
            await preprocessor.process_all_data()
            logger.info("✅ Data processing completed!")
        else:
            logger.info("✅ Vector store loaded successfully!")

        # 4. Display system statistics
        vector_stats = vector_store.get_stats()
        preprocessing_stats = preprocessor.get_processing_stats()

        logger.info("📈 System Statistics:")
        logger.info(f"   - Vector Store: {vector_stats['total_documents']} documents")
        logger.info(f"   - Embedding Model: {vector_stats['model_name']}")
        logger.info(
            f"   - CSV Files: {preprocessing_stats['structured_files']['csv_files']}"
        )
        logger.info(
            f"   - Excel Files: {preprocessing_stats['structured_files']['excel_files']}"
        )
        logger.info(
            f"   - HTML Files: {preprocessing_stats['unstructured_files']['html_files']}"
        )
        logger.info(
            f"   - PDF Files: {preprocessing_stats['unstructured_files']['pdf_files']}"
        )

        logger.info("✅ System initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ System initialization failed: {e}")
        return False


def check_requirements():
    """Check if all required files and directories exist"""
    logger.info("🔍 Checking system requirements...")

    required_dirs = ["data/raw", "data/structure_tables", "app"]

    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)

    if missing_dirs:
        logger.error(f"❌ Missing required directories: {missing_dirs}")
        return False

    # Check for data files
    data_dir = Path("data")
    csv_files = list((data_dir / "structure_tables").glob("*.csv"))
    excel_files = list((data_dir / "structure_tables").glob("*.xlsx"))
    html_files = list((data_dir / "raw").rglob("*.html"))
    pdf_files = list((data_dir / "raw").rglob("*.pdf"))

    if not any([csv_files, excel_files, html_files, pdf_files]):
        logger.warning(
            "⚠️  No data files found. The system will work but with limited content."
        )

    logger.info("✅ Requirements check completed!")
    return True


def main():
    """Main startup function"""
    print("🌊 INGRES RAG Chatbot System")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        logger.error(
            "❌ Requirements check failed. Please ensure all required directories and files are present."
        )
        sys.exit(1)

    # Initialize system
    success = asyncio.run(initialize_system())

    if not success:
        logger.error(
            "❌ Failed to initialize system. Please check the logs for errors."
        )
        sys.exit(1)

    # Start the FastAPI server
    logger.info("🚀 Starting FastAPI server...")
    print("\n" + "=" * 50)
    print("🌐 Server will be available at:")
    print("   API: http://localhost:8001")
    print("   Docs: http://localhost:8001/docs")
    print("   Frontend: Open frontend/index.html in your browser")
    print("=" * 50)
    print("\nPress Ctrl+C to stop the server")

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            reload=False,  # Set to True for development
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("👋 Shutting down server...")


if __name__ == "__main__":
    main()
