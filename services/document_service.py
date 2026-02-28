import asyncio
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from ..models.document import Document, DocumentStatus, DocumentProcessingConfig
from ..models.extraction import ExtractionResult, ExtractedData
from ..models.summary import SummaryResult
from ..core.chunker import DocumentChunker
from ..utils.helpers import sanitize_filename, save_file_securely, validate_file_type
from ..utils.constants import ALLOWED_FILE_EXTENSIONS
from ..utils.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class DocumentService:
    def __init__(self):
        self.upload_dir = Path(settings.upload_directory)
        self.processed_dir = Path(settings.processed_directory)
        self.chunker = DocumentChunker()
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_document(
        self, 
        file_data: bytes, 
        filename: str,
        config: Optional[DocumentProcessingConfig] = None
    ) -> Document:
        """
        Upload and store a document
        """
        # Validate file type
        if not validate_file_type(filename, ALLOWED_FILE_EXTENSIONS):
            raise ValueError(f"File type not allowed. Allowed: {ALLOWED_FILE_EXTENSIONS}")
        
        # Check file size
        if len(file_data) > settings.max_file_size:
            raise ValueError(f"File size exceeds limit of {settings.max_file_size} bytes")
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Save file securely
        file_path = save_file_securely(
            file_data, 
            str(self.upload_dir), 
            safe_filename
        )
        
        # Create document record
        document = Document(
            filename=safe_filename,
            file_path=file_path,
            file_size=len(file_data),
            mime_type=self._get_mime_type(filename),
            config=config or DocumentProcessingConfig()
        )
        
        logger.info(f"Uploaded document: {document.id} - {document.filename}")
        return document
    
    def _get_mime_type(self, filename: str) -> str:
        """
        Determine MIME type based on file extension
        """
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.csv': 'text/csv'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    async def process_document(self, document: Document) -> Dict[str, Any]:
        """
        Process a document through the entire pipeline
        """
        logger.info(f"Starting processing for document: {document.id}")
        
        # Update document status
        document.status = DocumentStatus.PROCESSING
        document.processing_start_time = datetime.now()
        
        try:
            # Read the document content
            content = await self._read_document_content(document.file_path)
            
            # Process based on configuration
            results = {}
            
            if document.config.extract_entities:
                results['extraction'] = await self._process_extraction(content, document)
            
            if document.config.generate_summary:
                results['summary'] = await self._process_summarization(content, document)
            
            # TODO: Add entity linking and anomaly detection when those services are implemented
            
            # Calculate overall confidence
            # This would involve combining the results from various processing steps
            document.confidence_score = self._calculate_overall_confidence(results)
            
            # Mark as completed
            document.status = DocumentStatus.COMPLETED
            document.processing_end_time = datetime.now()
            document.processing_duration = (
                document.processing_end_time - document.processing_start_time
            ).total_seconds()
            
            logger.info(f"Completed processing for document: {document.id}")
            
            return {
                "document": document,
                "results": results,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {str(e)}")
            document.status = DocumentStatus.FAILED
            document.processing_end_time = datetime.now()
            if document.processing_start_time:
                document.processing_duration = (
                    document.processing_end_time - document.processing_start_time
                ).total_seconds()
            
            return {
                "document": document,
                "error": str(e),
                "success": False
            }
    
    async def _read_document_content(self, file_path: str) -> str:
        """
        Read document content based on file type
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return await self._read_pdf_content(file_path)
        elif file_ext == '.txt':
            return await self._read_txt_content(file_path)
        elif file_ext in ['.docx', '.csv']:
            # For now, treat these as text files
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            # Default to text reading
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    
    async def _read_pdf_content(self, file_path: str) -> str:
        """
        Extract text content from PDF file
        """
        import fitz  # PyMuPDF
        
        try:
            doc = fitz.open(file_path)
            content = ""
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                content += page.get_text() + "\n"
            
            doc.close()
            return content
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {str(e)}")
            raise
    
    async def _read_txt_content(self, file_path: str) -> str:
        """
        Read text content from TXT file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def _process_extraction(self, content: str, document: Document) -> ExtractionResult:
        """
        Process document for entity extraction
        """
        from .extraction_service import ExtractionService
        from ..core.llm_client import LLMClient
        
        llm_client = LLMClient()
        extraction_service = ExtractionService(llm_client)
        
        try:
            # Chunk the content for processing
            chunks = self.chunker.chunk_text(content)
            document.total_chunks = len(chunks)
            
            # Extract from all chunks
            extracted_data = await extraction_service.extract_from_chunks(chunks, document.config)
            
            # Create extraction result
            extraction_result = ExtractionResult(
                document_id=document.id,
                extracted_data=extracted_data,
                confidence_score=extracted_data.entities[0].confidence_score if extracted_data.entities else 0.5,
                processing_time=0.0,  # Will be calculated properly in the actual service
                tokens_used=0  # Will be calculated properly in the actual service
            )
            
            return extraction_result
        finally:
            await llm_client.close()
    
    async def _process_summarization(self, content: str, document: Document) -> SummaryResult:
        """
        Process document for summarization
        """
        from .summarization_service import SummarizationService
        from ..core.llm_client import LLMClient
        
        llm_client = LLMClient()
        summarization_service = SummarizationService(llm_client)
        
        try:
            # Chunk the content for processing
            chunks = self.chunker.chunk_text(content)
            
            # Generate summaries
            summary_result = await summarization_service.summarize_document(
                chunks, 
                document.config
            )
            
            return summary_result
        finally:
            await llm_client.close()
    
    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> float:
        """
        Calculate overall confidence based on processing results
        """
        if not results:
            return 0.0
        
        # Simple average for now - would be more sophisticated in practice
        confidences = []
        
        if 'extraction' in results and hasattr(results['extraction'], 'confidence_score'):
            confidences.append(results['extraction'].confidence_score)
        
        if 'summary' in results and hasattr(results['summary'], 'confidence_score'):
            confidences.append(results['summary'].confidence_score)
        
        if not confidences:
            return 0.5  # Default confidence if no results available
        
        return sum(confidences) / len(confidences)
    
    async def get_document_status(self, document_id: str) -> Optional[Document]:
        """
        Get the status of a document
        """
        # In a real implementation, this would fetch from the database
        # For now, we'll simulate by returning a basic document object
        # This method would be expanded when DB integration is added
        pass