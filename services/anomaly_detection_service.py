import asyncio
import re
from typing import List, Dict, Any
from ..models.extraction import ExtractedData
from ..models.document import DocumentProcessingConfig
from ..core.llm_client import LLMClient
from ..services.llm_service import LLMService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AnomalyDetectionService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.llm_service = LLMService(llm_client)
    
    async def detect_anomalies_in_document(
        self, 
        extracted_data: ExtractedData, 
        text_chunks: List[str],
        config: DocumentProcessingConfig
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in extracted data and document content
        """
        logger.info("Starting anomaly detection")
        
        anomalies = []
        
        # Rule-based anomaly detection
        rule_anomalies = self._detect_rule_based_anomalies(extracted_data)
        anomalies.extend(rule_anomalies)
        
        # LLM-based anomaly detection
        llm_anomalies = await self._detect_llm_based_anomalies(extracted_data, text_chunks)
        anomalies.extend(llm_anomalies)
        
        logger.info(f"Detected {len(anomalies)} anomalies")
        return anomalies
    
    def _detect_rule_based_anomalies(self, extracted_data: ExtractedData) -> List[Dict[str, Any]]:
        """
        Detect anomalies using rule-based methods
        """
        anomalies = []
        
        # Check for duplicate entities with different values
        anomalies.extend(self._check_duplicate_entities(extracted_data))
        
        # Check for date inconsistencies
        anomalies.extend(self._check_date_inconsistencies(extracted_data))
        
        # Check for numerical value anomalies
        anomalies.extend(self._check_numerical_anomalies(extracted_data))
        
        # Check for contradictory information
        anomalies.extend(self._check_contradictory_info(extracted_data))
        
        return anomalies
    
    def _check_duplicate_entities(self, extracted_data: ExtractedData) -> List[Dict[str, Any]]:
        """
        Check for entities that appear multiple times with different values
        """
        anomalies = []
        
        # Group entities by type
        entity_map = {}
        for entity in extracted_data.entities:
            if entity.entity_type not in entity_map:
                entity_map[entity.entity_type] = []
            entity_map[entity.entity_type].append(entity)
        
        # Check for duplicates with different values
        for entity_type, entities in entity_map.items():
            if len(entities) > 1:
                # Get unique values
                unique_values = set()
                value_entities = {}
                
                for entity in entities:
                    value = entity.entity_value.lower().strip()
                    if value not in value_entities:
                        value_entities[value] = []
                    value_entities[value].append(entity)
                    unique_values.add(value)
                
                # If we have multiple different values for the same entity type
                if len(unique_values) > 1:
                    anomalies.append({
                        "type": "duplicate_entity",
                        "description": f"Multiple different values found for entity type '{entity_type}': {list(unique_values)}",
                        "severity": "medium",
                        "confidence_score": 0.7,
                        "location": f"entity_type:{entity_type}",
                        "details": {
                            "entity_type": entity_type,
                            "values": list(unique_values),
                            "count": len(entities)
                        }
                    })
        
        return anomalies
    
    def _check_date_inconsistencies(self, extracted_data: ExtractedData) -> List[Dict[str, Any]]:
        """
        Check for date inconsistencies
        """
        anomalies = []
        
        # Parse dates to datetime objects for comparison
        dates = []
        for date_str in extracted_data.dates:
            try:
                from datetime import datetime
                # Try to parse the date string
                parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                dates.append((date_str, parsed_date))
            except ValueError:
                # If parsing fails, note as anomaly
                anomalies.append({
                    "type": "invalid_date_format",
                    "description": f"Invalid date format: {date_str}",
                    "severity": "high",
                    "confidence_score": 0.9,
                    "location": f"date:{date_str}",
                    "details": {
                        "date_string": date_str
                    }
                })
        
        # Check for logical inconsistencies (e.g., future dates for historical documents)
        # This is a simplified example - real implementation would need more context
        from datetime import datetime
        current_date = datetime.now()
        
        future_dates = [d for d in dates if d[1] > current_date]
        if future_dates:
            anomalies.append({
                "type": "future_date",
                "description": f"Found {len(future_dates)} dates in the future",
                "severity": "medium",
                "confidence_score": 0.6,
                "location": "dates_section",
                "details": {
                    "future_dates": [d[0] for d in future_dates]
                }
            })
        
        return anomalies
    
    def _check_numerical_anomalies(self, extracted_data: ExtractedData) -> List[Dict[str, Any]]:
        """
        Check for numerical value anomalies
        """
        anomalies = []
        
        # Look for unusually large or small numbers
        for num_val in extracted_data.numerical_values:
            value = num_val.get("value", 0)
            context = num_val.get("context", "")
            
            # Check for extremely large numbers (could be data entry errors)
            if abs(value) > 1e10:  # 10 billion
                anomalies.append({
                    "type": "extreme_numerical_value",
                    "description": f"Extremely large numerical value found: {value} in context '{context}'",
                    "severity": "high",
                    "confidence_score": 0.8,
                    "location": f"numerical_value:{value}",
                    "details": {
                        "value": value,
                        "context": context
                    }
                })
            
            # Check for negative values where positive expected (based on context)
            if value < 0 and any(pos_word in context.lower() for pos_word in ["amount", "payment", "revenue", "profit"]):
                anomalies.append({
                    "type": "negative_amount",
                    "description": f"Negative value found in context where positive expected: {value} in '{context}'",
                    "severity": "medium",
                    "confidence_score": 0.7,
                    "location": f"numerical_value:{value}",
                    "details": {
                        "value": value,
                        "context": context
                    }
                })
        
        return anomalies
    
    def _check_contradictory_info(self, extracted_data: ExtractedData) -> List[Dict[str, Any]]:
        """
        Check for potentially contradictory information
        """
        anomalies = []
        
        # This is a simplified example - real implementation would need more sophisticated logic
        # Look for entities that contradict each other
        
        # Example: Check for both "signed" and "unsigned" contract status
        contract_statuses = []
        for entity in extracted_data.entities:
            if "contract" in entity.entity_type.lower():
                value_lower = entity.entity_value.lower()
                if any(status in value_lower for status in ["signed", "executed", "agreed"]):
                    contract_statuses.append("signed")
                elif any(status in value_lower for status in ["unsigned", "draft", "pending"]):
                    contract_statuses.append("unsigned")
        
        if "signed" in contract_statuses and "unsigned" in contract_statuses:
            anomalies.append({
                "type": "contradictory_contract_status",
                "description": "Found contradictory contract statuses in document",
                "severity": "high",
                "confidence_score": 0.8,
                "location": "contract_section",
                "details": {
                    "statuses_found": contract_statuses
                }
            })
        
        return anomalies
    
    async def _detect_llm_based_anomalies(
        self, 
        extracted_data: ExtractedData, 
        text_chunks: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to detect anomalies based on context and content
        """
        anomalies = []
        
        # Convert extracted data to text for LLM analysis
        extracted_text = self._extracted_data_to_text(extracted_data)
        
        # Analyze each chunk for anomalies
        for i, chunk in enumerate(text_chunks):
            chunk_anomalies = await self._analyze_chunk_for_anomalies(
                chunk, 
                extracted_text, 
                f"chunk_{i}"
            )
            anomalies.extend(chunk_anomalies)
        
        return anomalies
    
    def _extracted_data_to_text(self, extracted_data: ExtractedData) -> str:
        """
        Convert extracted data to text format for LLM analysis
        """
        text_parts = []
        
        # Entities
        text_parts.append("ENTITIES:")
        for entity in extracted_data.entities:
            text_parts.append(f"- {entity.entity_type}: {entity.entity_value}")
        
        # Key points
        text_parts.append("\nKEY POINTS:")
        for point in extracted_data.key_points:
            text_parts.append(f"- {point}")
        
        # Dates
        text_parts.append("\nDATES:")
        for date in extracted_data.dates:
            text_parts.append(f"- {date}")
        
        # Numerical values
        text_parts.append("\nNUMERICAL VALUES:")
        for num_val in extracted_data.numerical_values:
            text_parts.append(f"- {num_val.get('value', 0)} ({num_val.get('context', '')})")
        
        # Risks
        text_parts.append("\nRISKS:")
        for risk in extracted_data.risks:
            text_parts.append(f"- {risk.get('risk_type', '')}: {risk.get('description', '')}")
        
        return "\n".join(text_parts)
    
    async def _analyze_chunk_for_anomalies(
        self, 
        chunk: str, 
        extracted_summary: str, 
        location: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze a text chunk for anomalies using LLM
        """
        prompt = f"""
        Analyze the following text chunk for anomalies, inconsistencies, or unusual patterns.
        
        EXTRACTED DATA SUMMARY:
        {extracted_summary}
        
        TEXT CHUNK:
        {chunk}
        
        Identify any anomalies and return them in the following JSON format:
        {{
          "anomalies": [
            {{
              "type": "string",
              "description": "detailed description of the anomaly",
              "severity": "low|medium|high|critical",
              "confidence_score": 0.0-1.0,
              "location": "{location}",
              "details": {{
                "context": "surrounding text context",
                "extracted_vs_actual": "comparison between extracted and actual text"
              }}
            }}
          ]
        }}
        
        Return only the JSON without additional text:
        """
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                json_mode=True
            )
            
            if response.get("error"):
                logger.error(f"LLM error in anomaly detection: {response['error']}")
                return []
            
            import json
            result = json.loads(response["content"])
            
            return result.get("anomalies", [])
        
        except Exception as e:
            logger.error(f"Error analyzing chunk for anomalies: {str(e)}")
            return []
    
    async def calculate_anomaly_confidence(
        self, 
        anomalies: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate overall confidence in anomaly detection
        """
        if not anomalies:
            return 0.0
        
        # Calculate confidence based on severity and count of anomalies
        total_weighted_score = 0
        total_severity_weight = 0
        
        severity_weights = {
            "low": 0.3,
            "medium": 0.5,
            "high": 0.8,
            "critical": 1.0
        }
        
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            confidence = anomaly.get("confidence_score", 0.5)
            
            weight = severity_weights.get(severity, 0.5)
            total_weighted_score += confidence * weight
            total_severity_weight += weight
        
        if total_severity_weight == 0:
            return 0.0
        
        # Average confidence weighted by severity
        avg_confidence = total_weighted_score / total_severity_weight
        
        # Adjust based on number of anomalies (more anomalies might indicate higher confidence in detection)
        anomaly_count_factor = min(len(anomalies) / 10.0, 1.0)  # Cap at 1.0 for 10+ anomalies
        
        final_confidence = (avg_confidence * 0.7) + (anomaly_count_factor * 0.3)
        
        return min(final_confidence, 1.0)  # Cap at 1.0