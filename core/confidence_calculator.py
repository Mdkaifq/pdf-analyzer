from typing import Dict, List, Any, Optional
from statistics import mean
from ..models.extraction import ExtractedData
from ..models.summary import SummaryResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfidenceCalculator:
    def __init__(self):
        # Weights for different components of confidence calculation
        self.weights = {
            "extraction_validity": 0.3,      # Valid JSON and schema compliance
            "entity_consistency": 0.2,       # Cross-validation of entities
            "text_coverage": 0.15,           # How much of the text was processed
            "repetition_penalty": 0.1,       # Penalty for repetitive content
            "repair_attempts": 0.15,         # Number of repair attempts needed
            "token_efficiency": 0.1          # Efficient use of context window
        }
    
    def calculate_extraction_confidence(
        self, 
        extracted_data: ExtractedData, 
        text_length: int,
        repair_attempts: int = 0,
        max_repairs: int = 3
    ) -> float:
        """
        Calculate confidence score for extracted data
        Returns a value between 0 and 1
        """
        scores = {}
        
        # 1. Extraction validity score (0-1) - based on presence of expected fields
        total_expected_items = (
            len(extracted_data.entities) +
            len(extracted_data.key_points) +
            len(extracted_data.dates) +
            len(extracted_data.numerical_values) +
            len(extracted_data.risks)
        )
        scores["extraction_validity"] = min(total_expected_items / 10.0, 1.0)  # Normalize assuming ~10 items is good
        
        # 2. Entity consistency score (0-1) - based on confidence scores of individual entities
        if extracted_data.entities:
            avg_entity_confidence = mean([e.confidence_score for e in extracted_data.entities])
            scores["entity_consistency"] = avg_entity_confidence
        else:
            scores["entity_consistency"] = 0.0
        
        # 3. Text coverage score (0-1) - how much of the original text was covered
        # This would require additional metadata about which parts of the text were processed
        scores["text_coverage"] = 0.8  # Placeholder - in a real implementation, this would be calculated based on processed chunks
        
        # 4. Repetition penalty (0-1) - lower score for more repair attempts
        scores["repetition_penalty"] = max(0, 1 - (repair_attempts / max_repairs))
        
        # 5. Repair attempts penalty - higher penalty for more attempts
        repair_penalty = max(0, 1 - (repair_attempts * 0.2))  # 20% penalty per repair attempt
        scores["repair_attempts"] = repair_penalty
        
        # 6. Token efficiency - not applicable here since this is for extraction, not generation
        scores["token_efficiency"] = 1.0  # Max score for this component
        
        # Calculate weighted average
        total_weight = sum(self.weights.values())
        confidence_score = sum(scores[key] * self.weights[key] for key in scores) / total_weight
        
        logger.info(f"Extraction confidence breakdown: {scores}")
        return round(confidence_score, 3)
    
    def calculate_summary_confidence(
        self,
        summary_result: SummaryResult,
        original_text_length: int,
        num_chunks: int,
        repair_attempts: int = 0
    ) -> float:
        """
        Calculate confidence score for summary
        Returns a value between 0 and 1
        """
        scores = {}
        
        # 1. Extraction validity - based on completeness of summary components
        completeness_score = 0.0
        if summary_result.global_summary:
            completeness_score += 0.4  # Global summary is important
        if summary_result.section_summaries:
            completeness_score += 0.3 * min(1.0, len(summary_result.section_summaries) / 5)  # Up to 5 sections
        if summary_result.chunk_summaries:
            completeness_score += 0.3 * min(1.0, len(summary_result.chunk_summaries) / num_chunks)  # Proportional to chunks
        
        scores["extraction_validity"] = completeness_score
        
        # 2. Entity consistency - based on summary confidence scores
        all_summaries = [summary_result.global_summary] + [s.content for s in summary_result.section_summaries] + [s.content for s in summary_result.chunk_summaries]
        avg_summary_confidence = mean([summary_result.confidence_score] + [s.confidence_score for s in summary_result.section_summaries + summary_result.chunk_summaries])
        scores["entity_consistency"] = avg_summary_confidence
        
        # 3. Text coverage - based on number of chunks summarized
        scores["text_coverage"] = min(1.0, len(summary_result.chunk_summaries) / num_chunks) if num_chunks > 0 else 0.0
        
        # 4. Repetition penalty
        scores["repetition_penalty"] = max(0, 1 - (repair_attempts / 3))
        
        # 5. Repair attempts penalty
        repair_penalty = max(0, 1 - (repair_attempts * 0.2))
        scores["repair_attempts"] = repair_penalty
        
        # 6. Token efficiency - based on summary conciseness
        total_summary_length = len(summary_result.global_summary) + sum(len(s.content) for s in summary_result.section_summaries + summary_result.chunk_summaries)
        efficiency_ratio = original_text_length / max(total_summary_length, 1)  # Higher ratio = better efficiency
        scores["token_efficiency"] = min(1.0, efficiency_ratio / 10)  # Normalize assuming 10:1 compression is excellent
        
        # Calculate weighted average
        total_weight = sum(self.weights.values())
        confidence_score = sum(scores[key] * self.weights[key] for key in scores) / total_weight
        
        logger.info(f"Summary confidence breakdown: {scores}")
        return round(confidence_score, 3)
    
    def calculate_overall_confidence(
        self,
        extraction_confidence: float,
        summary_confidence: float,
        anomaly_confidence: float,
        entity_linking_confidence: float
    ) -> Dict[str, Any]:
        """
        Calculate overall document processing confidence
        """
        # Weighted average of all components
        component_weights = {
            "extraction": 0.3,
            "summary": 0.3,
            "anomaly": 0.2,
            "entity_linking": 0.2
        }
        
        overall_confidence = (
            extraction_confidence * component_weights["extraction"] +
            summary_confidence * component_weights["summary"] +
            anomaly_confidence * component_weights["anomaly"] +
            entity_linking_confidence * component_weights["entity_linking"]
        )
        
        return {
            "overall_confidence": round(overall_confidence, 3),
            "component_scores": {
                "extraction": extraction_confidence,
                "summary": summary_confidence,
                "anomaly": anomaly_confidence,
                "entity_linking": entity_linking_confidence
            },
            "confidence_breakdown": {
                "extraction_weight": component_weights["extraction"],
                "summary_weight": component_weights["summary"],
                "anomaly_weight": component_weights["anomaly"],
                "entity_linking_weight": component_weights["entity_linking"]
            }
        }
    
    def apply_confidence_thresholds(self, confidence_score: float) -> str:
        """
        Categorize confidence score into qualitative levels
        """
        if confidence_score >= 0.8:
            return "high"
        elif confidence_score >= 0.6:
            return "medium"
        elif confidence_score >= 0.4:
            return "low"
        else:
            return "very_low"