import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    def __init__(self):
        self.mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.database_name: str = os.getenv("DATABASE_NAME", "ingres_rag")
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.vector_dimension: int = int(os.getenv("VECTOR_DIMENSION", "384"))
        self.top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))


settings = Settings()
