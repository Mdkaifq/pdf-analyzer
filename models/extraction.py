from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ExtractedEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    entity_value: str
    confidence_score: float
    position_start: Optional[int] = None
    position_end: Optional[int] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExtractedData(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)  # ISO format
    numerical_values: List[Dict[str, Any]] = Field(default_factory=list)  # {"value": float, "context": str}
    risks: List[Dict[str, Any]] = Field(default_factory=list)  # {"risk_type": str, "description": str, "severity": str}


class ExtractionResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    extracted_data: ExtractedData
    confidence_score: float
    processing_time: float
    tokens_used: int
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)