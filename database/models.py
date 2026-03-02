from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    status = Column(String, default="uploaded")
    processing_start_time = Column(DateTime)
    processing_end_time = Column(DateTime)
    processing_duration = Column(Float)
    confidence_score = Column(Float)
    total_chunks = Column(Integer)
    config = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class ExtractionResultModel(Base):
    __tablename__ = "extraction_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True)
    extracted_data = Column(JSON)
    confidence_score = Column(Float)
    processing_time = Column(Float)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=func.now())

class SummaryResultModel(Base):
    __tablename__ = "summary_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True)
    global_summary = Column(Text)
    section_summaries = Column(JSON)
    chunk_summaries = Column(JSON)
    confidence_score = Column(Float)
    processing_time = Column(Float)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=func.now())

class AnomalyResultModel(Base):
    __tablename__ = "anomaly_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True)
    anomalies = Column(JSON)
    confidence_score = Column(Float)
    processing_time = Column(Float)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=func.now())