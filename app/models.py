from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: Optional[float] = None
    response_time: Optional[float] = None


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: int  # 1-5 scale
    comments: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class GroundWaterData(BaseModel):
    state: str
    rainfall_mm: float
    ground_water_extraction_ham: float
    annual_extractable_ground_water_resources_ham: float
    url: Optional[str] = None
    year: Optional[str] = "2024-2025"


class TextChunk(BaseModel):
    content: str
    source: str
    source_type: str  # 'pdf', 'html', 'csv', 'xlsx'
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class ChatSession(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    queries: List[Dict[str, Any]] = []
    created_at: datetime
    last_active: datetime
