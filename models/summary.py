from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class SummaryLevel(str, Enum):
    CHUNK = "chunk"
    SECTION = "section"
    GLOBAL = "global"


class SummaryItem(BaseModel):
    level: SummaryLevel
    content: str
    confidence_score: float
    chunk_indices: List[int] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SummaryResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    global_summary: str
    section_summaries: List[SummaryItem] = Field(default_factory=list)
    chunk_summaries: List[SummaryItem] = Field(default_factory=list)
    confidence_score: float
    processing_time: float
    tokens_used: int
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)