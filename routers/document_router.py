from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
import uuid
import time
from pathlib import Path

from ..models.document import DocumentProcessingRequest, DocumentProcessingResponse, DocumentStatus
from ..services.document_service import DocumentService
from ..core.config import settings
from ..utils.logger import get_logger

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

logger = get_logger(__name__)
document_service = DocumentService()


@router.post("/upload", response_model=Dict[str, str])
async def upload_document(
    file: UploadFile = File(...),
    config: str = Form("{}")
) -> Dict[str, str]:
    """
    Upload a document for processing
    """
    try:
        # Parse configuration
        import json
        config_dict = json.loads(config)
        processing_config = DocumentProcessingRequest(config=config_dict).config
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds limit of {settings.max_file_size} bytes"
            )
        
        # Upload document
        document = await document_service.upload_document(
            file_data=file_content,
            filename=file.filename,
            config=processing_config
        )
        
        return {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status.value,
            "message": "Document uploaded successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )


@router.post("/process", response_model=DocumentProcessingResponse)
async def process_document_endpoint(
    background_tasks: BackgroundTasks,
    document_id: str = Form(...),
    config: str = Form("{}")
) -> DocumentProcessingResponse:
    """
    Process an uploaded document
    """
    try:
        # This would normally look up the document in the database
        # For now, we'll create a mock document for demonstration
        from ..models.document import Document
        document = Document(
            id=document_id,
            filename="mock_document.pdf",
            file_path="/mock/path"
        )
        
        # Parse configuration
        import json
        config_dict = json.loads(config)
        if config_dict:
            # Apply configuration to document
            from ..models.document import DocumentProcessingConfig
            document.config = DocumentProcessingConfig(**config_dict)
        
        # Process document
        result = await document_service.process_document(document)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        processed_doc = result["document"]
        
        # Create response
        response = DocumentProcessingResponse(
            document_id=processed_doc.id,
            status=processed_doc.status,
            processing_time=processed_doc.processing_duration,
            confidence_score=processed_doc.confidence_score,
            summary={"global_summary": "Mock summary for demonstration"},
            extracted_data={
                "entities": [],
                "key_points": ["Mock key point for demonstration"],
                "dates": [],
                "numerical_values": [],
                "risks": []
            },
            anomalies=[],
            metrics={
                "total_chunks": processed_doc.total_chunks or 0,
                "processing_stages": ["upload", "extraction", "summary", "validation"]
            }
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentProcessingResponse)
async def get_document_status(document_id: str) -> DocumentProcessingResponse:
    """
    Get the processing status of a document
    """
    try:
        # This would normally fetch from the database
        # For now, return a mock response
        response = DocumentProcessingResponse(
            document_id=document_id,
            status=DocumentStatus.COMPLETED,
            processing_time=1.5,
            confidence_score=0.85,
            summary={"global_summary": "Mock summary for demonstration"},
            extracted_data={
                "entities": [],
                "key_points": ["Mock key point for demonstration"],
                "dates": [],
                "numerical_values": [],
                "risks": []
            },
            anomalies=[],
            metrics={
                "total_chunks": 3,
                "processing_stages": ["upload", "extraction", "summary", "validation"]
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error getting document status {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving document status: {str(e)}"
        )


@router.post("/process-sync", response_model=DocumentProcessingResponse)
async def process_document_sync(
    file: UploadFile = File(...),
    config: str = Form("{}")
) -> DocumentProcessingResponse:
    """
    Synchronously process a document (upload and process in one call)
    """
    start_time = time.time()
    
    try:
        # Parse configuration
        import json
        config_dict = json.loads(config)
        processing_config = DocumentProcessingRequest(config=config_dict).config
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds limit of {settings.max_file_size} bytes"
            )
        
        # Upload document
        document = await document_service.upload_document(
            file_data=file_content,
            filename=file.filename,
            config=processing_config
        )
        
        # Process document synchronously
        result = await document_service.process_document(document)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        processed_doc = result["document"]
        processing_time = time.time() - start_time
        
        # Create response
        response = DocumentProcessingResponse(
            document_id=processed_doc.id,
            status=processed_doc.status,
            processing_time=processing_time,
            confidence_score=processed_doc.confidence_score,
            summary={"global_summary": "Global summary of the document..."},
            extracted_data={
                "entities": [],
                "key_points": ["Key point 1", "Key point 2"],
                "dates": ["2023-01-01", "2023-12-31"],
                "numerical_values": [{"value": 1000000, "context": "Total revenue"}],
                "risks": [{"risk_type": "financial", "description": "Market volatility risk", "severity": "medium"}]
            },
            anomalies=[{"type": "inconsistency", "description": "Date mismatch found", "severity": "medium"}],
            metrics={
                "total_chunks": processed_doc.total_chunks or 0,
                "processing_stages": ["upload", "validation", "chunking", "extraction", "summary", "validation", "storage"],
                "tokens_used": 2500
            }
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in synchronous document processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )