import asyncio
from typing import List, Tuple, Dict, Any
from ..models.summary import SummaryResult, SummaryItem, SummaryLevel
from ..models.document import DocumentProcessingConfig
from ..core.llm_client import LLMClient
from ..services.llm_service import LLMService
from ..core.validator import AutoRepairValidator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SummarizationService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.llm_service = LLMService(llm_client)
        self.validator = AutoRepairValidator(llm_client)
    
    async def summarize_document(
        self, 
        chunks: List[Tuple[int, str]], 
        config: DocumentProcessingConfig
    ) -> SummaryResult:
        """
        Generate hierarchical summaries for a document
        """
        logger.info(f"Starting hierarchical summarization for {len(chunks)} chunks")
        
        # Generate chunk-level summaries
        chunk_summaries = await self._generate_chunk_summaries(chunks)
        
        # Generate section summaries from chunk summaries
        section_summaries = await self._generate_section_summaries(chunk_summaries)
        
        # Generate global summary from section summaries
        global_summary = await self._generate_global_summary(section_summaries)
        
        # Calculate confidence score
        # For now, use a simple average - would be more sophisticated in practice
        confidence_score = 0.75  # Placeholder
        
        # Create summary result
        summary_result = SummaryResult(
            document_id="temp_doc_id",  # Will be set by caller
            global_summary=global_summary,
            section_summaries=section_summaries,
            chunk_summaries=chunk_summaries,
            confidence_score=confidence_score,
            processing_time=0.0,  # Will be calculated properly
            tokens_used=0  # Will be calculated properly
        )
        
        logger.info("Hierarchical summarization completed")
        return summary_result
    
    async def _generate_chunk_summaries(
        self, 
        chunks: List[Tuple[int, str]]
    ) -> List[SummaryItem]:
        """
        Generate summaries for each chunk
        """
        logger.info(f"Generating summaries for {len(chunks)} chunks")
        
        chunk_summaries = []
        
        # Process chunks in parallel batches
        batch_size = 5  # Limit concurrent API calls
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Create tasks for batch processing
            tasks = []
            for chunk_idx, chunk_text in batch:
                task = self._generate_single_chunk_summary(chunk_idx, chunk_text)
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error summarizing chunk {batch[j][0]}: {str(result)}")
                    continue
                
                summary_item = result
                chunk_summaries.append(summary_item)
        
        logger.info(f"Generated {len(chunk_summaries)} chunk summaries")
        return chunk_summaries
    
    async def _generate_single_chunk_summary(
        self, 
        chunk_idx: int, 
        chunk_text: str
    ) -> SummaryItem:
        """
        Generate summary for a single chunk
        """
        prompt = f"""
        Provide a concise summary of the following text chunk:

        TEXT CHUNK (Index: {chunk_idx}):
        {chunk_text}

        SUMMARY:
        """
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                temperature=0.3  # Slightly higher for creativity in summarization
            )
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            summary_text = response["content"].strip()
            
            # Create summary item
            summary_item = SummaryItem(
                level=SummaryLevel.CHUNK,
                content=summary_text,
                confidence_score=0.8,  # Placeholder
                chunk_indices=[chunk_idx]
            )
            
            return summary_item
        
        except Exception as e:
            logger.error(f"Error generating summary for chunk {chunk_idx}: {str(e)}")
            # Return a summary with the original text as fallback
            return SummaryItem(
                level=SummaryLevel.CHUNK,
                content=f"[SUMMARY ERROR for chunk {chunk_idx}]",
                confidence_score=0.0,
                chunk_indices=[chunk_idx]
            )
    
    async def _generate_section_summaries(
        self, 
        chunk_summaries: List[SummaryItem]
    ) -> List[SummaryItem]:
        """
        Group chunk summaries into sections and generate section summaries
        """
        if not chunk_summaries:
            return []
        
        logger.info(f"Generating section summaries from {len(chunk_summaries)} chunk summaries")
        
        # Group chunk summaries into sections (e.g., 5 chunks per section)
        section_size = 5
        sections = []
        
        for i in range(0, len(chunk_summaries), section_size):
            section_chunk_summaries = chunk_summaries[i:i + section_size]
            
            # Combine the summaries for this section
            section_text = "\n\n".join([cs.content for cs in section_chunk_summaries])
            section_chunk_indices = [cs.chunk_indices[0] for cs in section_chunk_summaries]  # Simplified
            
            # Generate section summary
            prompt = f"""
            Provide a coherent summary of the following section composed of multiple text segments:

            SECTION TEXT:
            {section_text}

            SECTION SUMMARY:
            """
            
            try:
                response = await self.llm_client.generate_response(
                    prompt=prompt,
                    temperature=0.3
                )
                
                if response.get("error"):
                    raise Exception(f"LLM error: {response['error']}")
                
                section_summary = response["content"].strip()
                
                # Create section summary item
                section_summary_item = SummaryItem(
                    level=SummaryLevel.SECTION,
                    content=section_summary,
                    confidence_score=0.8,  # Placeholder
                    chunk_indices=section_chunk_indices
                )
                
                sections.append(section_summary_item)
            
            except Exception as e:
                logger.error(f"Error generating section summary: {str(e)}")
                # Add error placeholder
                sections.append(SummaryItem(
                    level=SummaryLevel.SECTION,
                    content="[SECTION SUMMARY ERROR]",
                    confidence_score=0.0,
                    chunk_indices=section_chunk_indices
                ))
        
        logger.info(f"Generated {len(sections)} section summaries")
        return sections
    
    async def _generate_global_summary(
        self, 
        section_summaries: List[SummaryItem]
    ) -> str:
        """
        Generate a global summary from section summaries
        """
        if not section_summaries:
            return "No content to summarize."
        
        logger.info(f"Generating global summary from {len(section_summaries)} section summaries")
        
        # Combine all section summaries
        combined_sections = "\n\n".join([ss.content for ss in section_summaries])
        
        prompt = f"""
        Provide a comprehensive yet concise global summary of the entire document based on the following section summaries:

        SECTION SUMMARIES:
        {combined_sections}

        GLOBAL SUMMARY:
        """
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                temperature=0.3
            )
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            global_summary = response["content"].strip()
            return global_summary
        
        except Exception as e:
            logger.error(f"Error generating global summary: {str(e)}")
            return "[GLOBAL SUMMARY ERROR]"
    
    async def summarize_with_context_compression(
        self, 
        chunks: List[Tuple[int, str]], 
        config: DocumentProcessingConfig
    ) -> SummaryResult:
        """
        Generate summaries using context compression for very large documents
        """
        logger.info("Starting summarization with context compression")
        
        # For large documents, use a sliding window approach
        # This would involve compressing context as we move through the document
        
        # For now, implement the regular approach
        return await self.summarize_document(chunks, config)
    
    async def evaluate_summary_quality(
        self, 
        summary_result: SummaryResult, 
        original_chunks: List[Tuple[int, str]]
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of generated summaries
        """
        quality_metrics = {
            "coherence_score": 0.0,
            "information_preservation": 0.0,
            "conciseness_ratio": 0.0,
            "relevance_score": 0.0
        }
        
        # Calculate basic metrics
        original_text_length = sum(len(chunk[1]) for chunk in original_chunks)
        summary_text_length = len(summary_result.global_summary)
        
        if original_text_length > 0:
            quality_metrics["conciseness_ratio"] = summary_text_length / original_text_length
        
        # Placeholder for more sophisticated evaluation
        # In practice, this would involve comparing summaries to original content
        # using various NLP metrics or LLM-based evaluation
        
        return quality_metrics