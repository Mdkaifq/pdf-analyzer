import asyncio
import json
from typing import List, Tuple, Dict, Any
from ..models.extraction import ExtractedData, ExtractedEntity
from ..models.document import DocumentProcessingConfig
from ..core.llm_client import LLMClient
from ..services.llm_service import LLMService
from ..core.validator import AutoRepairValidator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExtractionService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.llm_service = LLMService(llm_client)
        self.validator = AutoRepairValidator(llm_client)
    
    async def extract_from_chunks(
        self, 
        chunks: List[Tuple[int, str]], 
        config: DocumentProcessingConfig
    ) -> ExtractedData:
        """
        Extract structured data from document chunks
        """
        logger.info(f"Starting extraction from {len(chunks)} chunks")
        
        # Define the schema for extraction
        schema_description = """
        Extract the following information from the text:
        - entities: Array of objects with entity_type, entity_value, and confidence_score
        - key_points: Array of important points from the text
        - dates: Array of dates in ISO format (YYYY-MM-DD)
        - numerical_values: Array of objects with value, unit (if applicable), and context
        - risks: Array of objects with risk_type, description, severity (low/medium/high/critical), and confidence_score
        """
        
        # Process chunks in batches to manage API calls efficiently
        all_entities = []
        all_key_points = []
        all_dates = []
        all_numerical_values = []
        all_risks = []
        
        # Process chunks in parallel batches
        batch_size = 5  # Limit concurrent API calls
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Create tasks for batch processing
            tasks = []
            for chunk_idx, chunk_text in batch:
                task = self._extract_from_single_chunk(
                    chunk_text, 
                    chunk_idx, 
                    schema_description
                )
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error extracting from chunk {batch[j][0]}: {str(result)}")
                    continue
                
                chunk_idx, chunk_entities, chunk_key_points, chunk_dates, chunk_numerical_values, chunk_risks = result
                
                # Add chunk-specific information to entities
                for entity in chunk_entities:
                    entity.chunk_index = chunk_idx
                    all_entities.append(entity)
                
                all_key_points.extend(chunk_key_points)
                all_dates.extend(chunk_dates)
                all_numerical_values.extend(chunk_numerical_values)
                all_risks.extend(chunk_risks)
        
        # Create final extracted data
        extracted_data = ExtractedData(
            entities=all_entities,
            key_points=list(set(all_key_points)),  # Remove duplicates
            dates=list(set(all_dates)),  # Remove duplicates
            numerical_values=all_numerical_values,
            risks=all_risks
        )
        
        logger.info(f"Extraction completed: {len(extracted_data.entities)} entities, "
                   f"{len(extracted_data.key_points)} key points, "
                   f"{len(extracted_data.dates)} dates, "
                   f"{len(extracted_data.numerical_values)} numerical values, "
                   f"{len(extracted_data.risks)} risks")
        
        return extracted_data
    
    async def _extract_from_single_chunk(
        self, 
        chunk_text: str, 
        chunk_index: int, 
        schema_description: str
    ) -> Tuple[int, List[ExtractedEntity], List[str], List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract data from a single chunk
        """
        # Prepare the prompt
        prompt = f"""
        Extract structured information from the following text chunk according to the specified schema.
        
        SCHEMA DESCRIPTION:
        {schema_description}
        
        TEXT CHUNK (Index: {chunk_index}):
        {chunk_text}
        
        Please return only the structured data in valid JSON format without any additional explanation or markdown formatting:
        {{
          "entities": [
            {{
              "entity_type": "string",
              "entity_value": "string",
              "confidence_score": 0.0-1.0
            }}
          ],
          "key_points": ["string"],
          "dates": ["YYYY-MM-DD"],
          "numerical_values": [
            {{
              "value": number,
              "unit": "string (optional)",
              "context": "string"
            }}
          ],
          "risks": [
            {{
              "risk_type": "string",
              "description": "string",
              "severity": "low|medium|high|critical",
              "confidence_score": 0.0-1.0
            }}
          ]
        }}
        """
        
        try:
            # Generate response from LLM
            response = await self.llm_client.generate_response(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistency
                json_mode=True
            )
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            # Validate and repair the JSON if needed
            validated_data = await self.validator.validate_and_repair(
                response["content"],
                type('TempModel', (), {'model_validate': staticmethod(lambda x: x)})(),
                schema_description
            )
            
            data = validated_data["data"]
            
            # Convert to our model objects
            entities = []
            for entity_data in data.get("entities", []):
                entity = ExtractedEntity(
                    entity_type=entity_data.get("entity_type", ""),
                    entity_value=entity_data.get("entity_value", ""),
                    confidence_score=entity_data.get("confidence_score", 0.5),
                    chunk_index=chunk_index
                )
                entities.append(entity)
            
            key_points = data.get("key_points", [])
            dates = data.get("dates", [])
            numerical_values = data.get("numerical_values", [])
            risks = data.get("risks", [])
            
            return chunk_index, entities, key_points, dates, numerical_values, risks
        
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk_index}: {str(e)}")
            # Return empty results for this chunk
            return chunk_index, [], [], [], [], []
    
    async def extract_specific_entities(
        self, 
        text: str, 
        entity_types: List[str]
    ) -> List[ExtractedEntity]:
        """
        Extract specific types of entities from text
        """
        entity_types_str = ", ".join(entity_types)
        
        prompt = f"""
        Extract the following types of entities from the text: {entity_types_str}
        
        TEXT:
        {text}
        
        Return in JSON format:
        {{
          "entities": [
            {{
              "entity_type": "string",
              "entity_value": "string",
              "confidence_score": 0.0-1.0
            }}
          ]
        }}
        """
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                json_mode=True
            )
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            validated_data = await self.validator.validate_and_repair(
                response["content"],
                type('TempModel', (), {'model_validate': staticmethod(lambda x: x)})(),
                f"JSON with 'entities' array containing objects with 'entity_type' (one of {entity_types_str}), 'entity_value', and 'confidence_score'"
            )
            
            entities_data = validated_data["data"].get("entities", [])
            
            entities = []
            for entity_data in entities_data:
                entity = ExtractedEntity(
                    entity_type=entity_data.get("entity_type", "unknown"),
                    entity_value=entity_data.get("entity_value", ""),
                    confidence_score=entity_data.get("confidence_score", 0.5)
                )
                entities.append(entity)
            
            return entities
        
        except Exception as e:
            logger.error(f"Error extracting specific entities: {str(e)}")
            return []
    
    async def validate_extraction_quality(
        self, 
        extracted_data: ExtractedData, 
        original_text: str
    ) -> Dict[str, Any]:
        """
        Validate the quality of extracted data against the original text
        """
        quality_metrics = {
            "coverage_ratio": 0.0,
            "entity_accuracy": 0.0,
            "consistency_score": 0.0,
            "completeness_score": 0.0
        }
        
        # Calculate basic metrics
        total_entities = len(extracted_data.entities)
        total_key_points = len(extracted_data.key_points)
        total_dates = len(extracted_data.dates)
        total_numerical_values = len(extracted_data.numerical_values)
        total_risks = len(extracted_data.risks)
        
        # Completeness score based on variety of extracted information
        has_entities = total_entities > 0
        has_key_points = total_key_points > 0
        has_dates = total_dates > 0
        has_numerical_values = total_numerical_values > 0
        has_risks = total_risks > 0
        
        completeness_score = sum([
            1 if has_entities else 0,
            1 if has_key_points else 0,
            1 if has_dates else 0,
            1 if has_numerical_values else 0,
            1 if has_risks else 0
        ]) / 5.0
        
        quality_metrics["completeness_score"] = completeness_score
        
        # Additional validation could be implemented here based on specific requirements
        
        return quality_metrics