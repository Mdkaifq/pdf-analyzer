import asyncio
import re
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from ..models.entity import Entity, EntityRelationship
from ..models.extraction import ExtractedEntity
from ..core.llm_client import LLMClient
from ..services.llm_service import LLMService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EntityLinkingService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.llm_service = LLMService(llm_client)
        
        # Initialize sentence transformer for semantic similarity
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def link_entities_across_chunks(
        self, 
        entities: List[ExtractedEntity], 
        chunks: List[str]
    ) -> List[EntityRelationship]:
        """
        Link entities that appear across different chunks/pages of a document
        """
        logger.info(f"Starting entity linking for {len(entities)} entities")
        
        # Group entities by their normalized values
        entity_groups = self._group_similar_entities(entities)
        
        # Find relationships between entities in different chunks
        relationships = []
        for group in entity_groups.values():
            if len(group) > 1:  # Only create relationships for entities that appear multiple times
                group_relationships = self._find_relationships_within_group(group)
                relationships.extend(group_relationships)
        
        logger.info(f"Found {len(relationships)} entity relationships")
        return relationships
    
    def _group_similar_entities(self, entities: List[ExtractedEntity]) -> Dict[str, List[ExtractedEntity]]:
        """
        Group entities that are likely the same but have slight variations
        """
        groups = {}
        
        for entity in entities:
            # Normalize the entity value for comparison
            normalized_value = self._normalize_entity_value(entity.entity_value)
            
            # Look for similar entities
            found_group = False
            for group_key in groups:
                # Check for exact match or fuzzy match
                if self._is_similar_entity(normalized_value, group_key):
                    groups[group_key].append(entity)
                    found_group = True
                    break
            
            if not found_group:
                groups[normalized_value] = [entity]
        
        return groups
    
    def _normalize_entity_value(self, value: str) -> str:
        """
        Normalize entity value for comparison
        """
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', value.lower().strip())
        
        # Remove common prefixes/suffixes that don't affect meaning
        normalized = re.sub(r'^the\s+', '', normalized)
        normalized = re.sub(r'\s+inc$', '', normalized)
        normalized = re.sub(r'\s+llc$', '', normalized)
        normalized = re.sub(r'\s+corp$', '', normalized)
        normalized = re.sub(r'\s+company$', '', normalized)
        
        return normalized
    
    def _is_similar_entity(self, val1: str, val2: str) -> bool:
        """
        Check if two entity values are similar enough to be considered the same
        """
        # Exact match
        if val1 == val2:
            return True
        
        # Length difference check (avoid comparing very different lengths)
        if abs(len(val1) - len(val2)) > max(len(val1), len(val2)) * 0.5:
            return False
        
        # Check for substring relationship
        if val1 in val2 or val2 in val1:
            return True
        
        # Use fuzzy matching for more complex cases
        similarity = self._compute_string_similarity(val1, val2)
        return similarity > 0.8  # Threshold for considering entities similar
    
    def _compute_string_similarity(self, str1: str, str2: str) -> float:
        """
        Compute similarity between two strings using multiple approaches
        """
        # Simple ratio based on common characters
        def simple_ratio(s1, s2):
            if len(s1) == 0 and len(s2) == 0:
                return 1.0
            if len(s1) == 0 or len(s2) == 0:
                return 0.0
            
            # Count common characters
            common_chars = set(s1) & set(s2)
            total_chars = set(s1) | set(s2)
            
            if len(total_chars) == 0:
                return 1.0
            
            return len(common_chars) / len(total_chars)
        
        # Use the simple ratio
        return simple_ratio(str1, str2)
    
    def _find_relationships_within_group(self, group: List[ExtractedEntity]) -> List[EntityRelationship]:
        """
        Find relationships between entities within a group
        """
        relationships = []
        
        # Create relationships between all pairs in the group
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                entity1 = group[i]
                entity2 = group[j]
                
                # Calculate relationship confidence based on entity confidence scores
                confidence = min(entity1.confidence_score, entity2.confidence_score)
                
                # Create relationship
                relationship = EntityRelationship(
                    source_entity_id=entity1.id,
                    target_entity_id=entity2.id,
                    relationship_type="same_as",  # Indicates these refer to the same real-world entity
                    confidence_score=confidence
                )
                
                relationships.append(relationship)
        
        return relationships
    
    async def create_entity_registry(self, entities: List[ExtractedEntity]) -> List[Entity]:
        """
        Create a consolidated entity registry with merged information
        """
        logger.info(f"Creating entity registry for {len(entities)} entities")
        
        # Group similar entities
        entity_groups = self._group_similar_entities(entities)
        
        registry = []
        for normalized_value, group in entity_groups.items():
            # Consolidate information from all occurrences
            entity_info = self._consolidate_entity_info(group, normalized_value)
            registry.append(entity_info)
        
        logger.info(f"Created registry with {len(registry)} unique entities")
        return registry
    
    def _consolidate_entity_info(self, group: List[ExtractedEntity], normalized_value: str) -> Entity:
        """
        Consolidate information from multiple occurrences of the same entity
        """
        # Use the first entity as base
        base_entity = group[0]
        
        # Collect all variations
        variations = set()
        for entity in group:
            variations.add(entity.entity_value)
        
        # Collect all pages and chunks mentioned
        pages_mentioned = set()
        chunks_mentioned = set()
        total_confidence = 0
        
        for entity in group:
            if entity.page_number is not None:
                pages_mentioned.add(entity.page_number)
            if entity.chunk_index is not None:
                chunks_mentioned.add(entity.chunk_index)
            total_confidence += entity.confidence_score
        
        # Calculate average confidence
        avg_confidence = total_confidence / len(group) if group else 0.0
        
        # Create consolidated entity
        consolidated_entity = Entity(
            entity_type=base_entity.entity_type,
            entity_value=normalized_value,
            confidence_score=avg_confidence,
            variations=list(variations),
            occurrence_count=len(group),
            pages_mentioned=list(pages_mentioned),
            chunks_mentioned=list(chunks_mentioned)
        )
        
        return consolidated_entity
    
    async def detect_entity_variants(
        self, 
        text: str, 
        base_entity: str
    ) -> List[str]:
        """
        Detect possible variants of an entity in text
        """
        # Create a prompt to find variants
        prompt = f"""
        Find all possible variants or alternative forms of the entity '{base_entity}' in the following text.
        Variants might include different capitalizations, abbreviations, or alternative names that refer to the same entity.
        
        TEXT:
        {text}
        
        Return a JSON list of all detected variants:
        """
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                json_mode=True
            )
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            # Parse the response
            import json
            result = json.loads(response["content"])
            
            if isinstance(result, list):
                return [variant.strip() for variant in result if isinstance(variant, str)]
            else:
                return [base_entity]  # Fallback
        
        except Exception as e:
            logger.error(f"Error detecting entity variants: {str(e)}")
            return [base_entity]  # Fallback to base entity
    
    def calculate_entity_linking_confidence(
        self, 
        relationships: List[EntityRelationship], 
        entity_registry: List[Entity]
    ) -> float:
        """
        Calculate overall confidence in entity linking
        """
        if not relationships and not entity_registry:
            return 0.0
        
        # Calculate confidence based on relationship strength and entity consolidation
        total_relationship_confidence = sum(rel.confidence_score for rel in relationships)
        avg_relationship_confidence = (
            total_relationship_confidence / len(relationships) if relationships else 0.0
        )
        
        # Entity consolidation score
        total_occurrences = sum(ent.occurrence_count for ent in entity_registry)
        unique_entities = len(entity_registry)
        
        # Higher consolidation score if many mentions map to few unique entities
        consolidation_score = (
            total_occurrences / unique_entities if unique_entities > 0 else 0.0
        )
        # Normalize consolidation score to 0-1 range
        consolidation_score = min(1.0, consolidation_score / 10.0)  # Assuming 10 is a high threshold
        
        # Weighted average
        linking_confidence = (
            0.6 * avg_relationship_confidence + 
            0.4 * consolidation_score
        )
        
        return linking_confidence