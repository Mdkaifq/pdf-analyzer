from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from database.models import DocumentModel, ExtractionResultModel, SummaryResultModel, AnomalyResultModel
from models.document import Document, DocumentStatus
from models.extraction import ExtractionResult, ExtractedData
from models.summary import SummaryResult
from datetime import datetime
import json
import uuid

async def create_document(db: AsyncSession, document: Document) -> DocumentModel:
    """Create a new document record"""
    db_document = DocumentModel(
        id=document.id,
        filename=document.filename,
        file_path=document.file_path,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status.value,
        config=document.config.dict() if document.config else None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    return db_document

async def get_document(db: AsyncSession, document_id: str) -> Optional[DocumentModel]:
    """Get a document by ID"""
    result = await db.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    return result.scalar_one_or_none()

async def update_document_status(db: AsyncSession, document_id: str, status: DocumentStatus) -> Optional[DocumentModel]:
    """Update document status"""
    result = await db.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    db_document = result.scalar_one_or_none()
    
    if db_document:
        db_document.status = status.value
        db_document.updated_at = datetime.now()
        await db.commit()
        await db.refresh(db_document)
        
    return db_document

async def update_document_processing_info(
    db: AsyncSession, 
    document_id: str, 
    processing_start_time: Optional[datetime] = None,
    processing_end_time: Optional[datetime] = None,
    processing_duration: Optional[float] = None,
    confidence_score: Optional[float] = None,
    total_chunks: Optional[int] = None
) -> Optional[DocumentModel]:
    """Update document processing information"""
    result = await db.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    db_document = result.scalar_one_or_none()
    
    if db_document:
        if processing_start_time:
            db_document.processing_start_time = processing_start_time
        if processing_end_time:
            db_document.processing_end_time = processing_end_time
        if processing_duration is not None:
            db_document.processing_duration = processing_duration
        if confidence_score is not None:
            db_document.confidence_score = confidence_score
        if total_chunks is not None:
            db_document.total_chunks = total_chunks
            
        db_document.updated_at = datetime.now()
        await db.commit()
        await db.refresh(db_document)
        
    return db_document

async def create_extraction_result(db: AsyncSession, extraction_result: ExtractionResult) -> ExtractionResultModel:
    """Create a new extraction result record"""
    db_extraction_result = ExtractionResultModel(
        document_id=extraction_result.document_id,
        extracted_data=extraction_result.extracted_data.dict() if extraction_result.extracted_data else None,
        confidence_score=extraction_result.confidence_score,
        processing_time=extraction_result.processing_time,
        tokens_used=extraction_result.tokens_used
    )
    
    db.add(db_extraction_result)
    await db.commit()
    await db.refresh(db_extraction_result)
    
    return db_extraction_result

async def get_extraction_result(db: AsyncSession, document_id: str) -> Optional[ExtractionResultModel]:
    """Get extraction result for a document"""
    result = await db.execute(
        select(ExtractionResultModel).where(ExtractionResultModel.document_id == document_id)
    )
    return result.scalar_one_or_none()

async def create_summary_result(db: AsyncSession, summary_result: SummaryResult) -> SummaryResultModel:
    """Create a new summary result record"""
    db_summary_result = SummaryResultModel(
        document_id=summary_result.document_id,
        global_summary=summary_result.global_summary,
        section_summaries=[s.dict() for s in summary_result.section_summaries],
        chunk_summaries=[s.dict() for s in summary_result.chunk_summaries],
        confidence_score=summary_result.confidence_score,
        processing_time=summary_result.processing_time,
        tokens_used=summary_result.tokens_used
    )
    
    db.add(db_summary_result)
    await db.commit()
    await db.refresh(db_summary_result)
    
    return db_summary_result

async def get_summary_result(db: AsyncSession, document_id: str) -> Optional[SummaryResultModel]:
    """Get summary result for a document"""
    result = await db.execute(
        select(SummaryResultModel).where(SummaryResultModel.document_id == document_id)
    )
    return result.scalar_one_or_none()

async def create_anomaly_result(db: AsyncSession, document_id: str, anomalies: List[dict], confidence_score: float) -> AnomalyResultModel:
    """Create a new anomaly result record"""
    db_anomaly_result = AnomalyResultModel(
        document_id=document_id,
        anomalies=anomalies,
        confidence_score=confidence_score,
        processing_time=0.0,  # Placeholder - would be calculated in real implementation
        tokens_used=0  # Placeholder - would be calculated in real implementation
    )
    
    db.add(db_anomaly_result)
    await db.commit()
    await db.refresh(db_anomaly_result)
    
    return db_anomaly_result

async def get_anomaly_result(db: AsyncSession, document_id: str) -> Optional[AnomalyResultModel]:
    """Get anomaly result for a document"""
    result = await db.execute(
        select(AnomalyResultModel).where(AnomalyResultModel.document_id == document_id)
    )
    return result.scalar_one_or_none()

async def get_document_status(db: AsyncSession, document_id: str) -> Optional[DocumentModel]:
    """Get document status - wrapper for get_document"""
    return await get_document(db, document_id)