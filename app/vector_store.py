from typing import List, Dict, Any
import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from .config import settings
import logging

logger = logging.getLogger(__name__)


class VectorStoreManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        # Use relative path from this file's location
        base_dir = Path(__file__).parent.parent
        self.index_path = str(base_dir / "data" / "faiss_index")
        self.vector_store = None

    def add_documents(self, documents: List[Document]):
        """Add documents to the vector store."""
        if not documents:
            return

        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
        else:
            self.vector_store.add_documents(documents)

        logger.info(f"Added {len(documents)} documents to vector store")

    def save_index(self):
        """Save the FAISS index to disk."""
        if self.vector_store:
            self.vector_store.save_local(self.index_path)
            logger.info("Vector store saved to disk")

    def load_index(self) -> bool:
        """Load the FAISS index from disk."""
        if os.path.exists(self.index_path):
            try:
                self.vector_store = FAISS.load_local(self.index_path, self.embeddings, allow_dangerous_deserialization=True)
                logger.info("Vector store loaded from disk")
                return True
            except Exception as e:
                logger.error(f"Error loading vector store: {e}")
                return False
        return False

    def as_retriever(self):
        """Return the vector store as a retriever."""
        if self.vector_store:
            # Increase k for better coverage in multi-entity queries
            return self.vector_store.as_retriever(search_kwargs={"k": 8})
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        if self.vector_store:
            return {
                "total_documents": self.vector_store.index.ntotal,
                "embedding_dimension": self.vector_store.index.d,
                "model_name": settings.embedding_model,
            }
        return {
            "total_documents": 0,
            "embedding_dimension": 0,
            "model_name": settings.embedding_model,
        }


# Global vector store instance
vector_store = VectorStoreManager()
