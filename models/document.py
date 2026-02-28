from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentProcessingConfig(BaseModel):
    extract_entities: bool = True
    generate_summary: bool = True
    detect_anomalies: bool = True
    perform_entity_linking: bool = True
    max_chunk_size: int = 2000
    overlap_size: int = 200
    enable_context_compression: bool = True
    llm_model: str = "gpt-4-turbo"
    temperature: float = 0.1


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    upload_date: datetime = Field(default_factory=datetime.now)
    status: DocumentStatus = DocumentStatus.UPLOADED
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    processing_duration: Optional[float] = None
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    config: DocumentProcessingConfig = Field(default_factory=DocumentProcessingConfig)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            DocumentStatus: lambda v: v.value
        }


class DocumentProcessingRequest(BaseModel):
    config: Optional[DocumentProcessingConfig] = Field(default_factory=DocumentProcessingConfig)


class DocumentProcessingResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    processing_time: Optional[float] = None
    confidence_score: Optional[float] = None
    summary: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    anomalies: Optional[list] = None
    metrics: Optional[Dict[str, Any]] = None