from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    entity_value: str
    confidence_score: float
    variations: List[str] = Field(default_factory=list)
    linked_entities: List[str] = Field(default_factory=list)  # IDs of linked entities
    occurrence_count: int = 0
    pages_mentioned: List[int] = Field(default_factory=list)
    chunks_mentioned: List[int] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class EntityRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence_score: float
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)