import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import pickle
import os
from .config import settings
from .models import TextChunk
import logging

logger = logging.getLogger(__name__)


class VectorStoreManager:
    def __init__(self):
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = settings.vector_dimension
        self.index = None
        self.documents = []
        self.index_path = "data/faiss_index.bin"
        self.documents_path = "data/documents.pkl"

    def initialize_index(self):
        """Initialize FAISS index"""
        self.index = faiss.IndexFlatIP(
            self.dimension
        )  # Inner Product for cosine similarity
        logger.info("FAISS index initialized")

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        embeddings = self.model.encode(
            texts, convert_to_tensor=True, normalize_embeddings=True
        )
        return embeddings.cpu().numpy()

    def add_documents(self, chunks: List[TextChunk]):
        """Add documents to vector store"""
        if self.index is None:
            self.initialize_index()

        texts = [chunk.content for chunk in chunks]
        embeddings = self.encode_texts(texts)

        # Add to FAISS index
        self.index.add(embeddings.astype("float32"))

        # Store document metadata
        for chunk in chunks:
            self.documents.append(
                {
                    "content": chunk.content,
                    "source": chunk.source,
                    "source_type": chunk.source_type,
                    "metadata": chunk.metadata,
                }
            )

        logger.info(f"Added {len(chunks)} documents to vector store")

    def search_similar(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if top_k is None:
            top_k = settings.top_k_results

        if self.index is None or len(self.documents) == 0:
            return []

        # Generate query embedding
        query_embedding = self.encode_texts([query])

        # Search FAISS index
        scores, indices = self.index.search(query_embedding.astype("float32"), top_k)

        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.documents):
                result = self.documents[idx].copy()
                result["similarity_score"] = float(score)
                result["rank"] = i + 1
                results.append(result)

        return results

    def save_index(self):
        """Save FAISS index and documents to disk"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        if self.index is not None:
            faiss.write_index(self.index, self.index_path)

        with open(self.documents_path, "wb") as f:
            pickle.dump(self.documents, f)

        logger.info("Vector store saved to disk")

    def load_index(self) -> bool:
        """Load FAISS index and documents from disk"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.documents_path):
                self.index = faiss.read_index(self.index_path)

                with open(self.documents_path, "rb") as f:
                    self.documents = pickle.load(f)

                logger.info(f"Vector store loaded with {len(self.documents)} documents")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal if self.index else 0,
            "embedding_dimension": self.dimension,
            "model_name": settings.embedding_model,
        }


# Global vector store instance
vector_store = VectorStoreManager()
