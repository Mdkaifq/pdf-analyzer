import json
import re
from typing import Any, Dict, Type, Union
from pydantic import BaseModel, ValidationError
from .llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JSONValidator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def validate_json_format(self, content: str, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """
        Validate that content is valid JSON and conforms to the expected Pydantic model
        """
        try:
            # Parse the JSON content
            parsed_json = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        
        # Validate against the Pydantic model
        try:
            validated_model = model_class.model_validate(parsed_json)
            return {
                "valid": True,
                "data": validated_model.model_dump(),
                "raw_content": parsed_json
            }
        except ValidationError as e:
            raise ValueError(f"JSON does not conform to expected schema: {str(e)}")
    
    def validate_basic_json(self, content: str) -> bool:
        """
        Basic check to see if content is valid JSON
        """
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False


class AutoRepairValidator(JSONValidator):
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self.max_repair_attempts = 3
    
    async def validate_and_repair(
        self, 
        content: str, 
        model_class: Type[BaseModel], 
        schema_description: str = ""
    ) -> Dict[str, Any]:
        """
        Validate content and attempt to repair if validation fails
        """
        # First, try basic validation
        try:
            result = await self.validate_json_format(content, model_class)
            if result["valid"]:
                return result
        except ValueError:
            pass  # Continue to repair attempts
        
        # If initial validation fails, attempt repairs
        original_content = content
        repair_count = 0
        
        while repair_count < self.max_repair_attempts:
            try:
                # Use LLM to repair the JSON
                repaired_content = await self.llm_client.repair_json(original_content, schema_description)
                
                # Validate the repaired content
                result = await self.validate_json_format(repaired_content, model_class)
                if result["valid"]:
                    result["repair_attempts"] = repair_count + 1
                    logger.info(f"Successfully repaired JSON after {repair_count + 1} attempt(s)")
                    return result
                
            except Exception as e:
                logger.warning(f"Repair attempt {repair_count + 1} failed: {str(e)}")
            
            repair_count += 1
        
        # If all repair attempts fail, raise an error
        raise ValueError(f"Failed to validate and repair JSON after {self.max_repair_attempts} attempts")
    
    def validate_structural_consistency(self, data_list: list, required_fields: list) -> Dict[str, Any]:
        """
        Validate that all items in a list have consistent structure
        """
        missing_fields = {}
        type_mismatches = {}
        
        for i, item in enumerate(data_list):
            if not isinstance(item, dict):
                continue
                
            # Check for missing required fields
            for field in required_fields:
                if field not in item:
                    if field not in missing_fields:
                        missing_fields[field] = []
                    missing_fields[field].append(i)
            
            # Check for type consistency if we have previous items to compare
            if i > 0:
                first_item = data_list[0]
                for field in item.keys():
                    if field in first_item:
                        expected_type = type(first_item[field])
                        actual_type = type(item[field])
                        
                        if expected_type != actual_type:
                            if field not in type_mismatches:
                                type_mismatches[field] = []
                            type_mismatches[field].append({
                                "index": i,
                                "expected": expected_type.__name__,
                                "actual": actual_type.__name__
                            })
        
        return {
            "missing_fields": missing_fields,
            "type_mismatches": type_mismatches,
            "is_consistent": len(missing_fields) == 0 and len(type_mismatches) == 0
        }
    
    def validate_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform quality checks on extracted data
        """
        issues = []
        
        # Check for empty values
        for key, value in data.items():
            if value is None or (isinstance(value, (list, str)) and len(value) == 0):
                issues.append(f"Empty value found for field: {key}")
        
        # Check for extremely long text fields that might indicate data corruption
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 10000:
                issues.append(f"Extremely long text value found for field: {key}")
            elif isinstance(value, list) and len(value) > 1000:
                issues.append(f"Extremely large array found for field: {key}")
        
        # Check for common hallucinations or artifacts
        if isinstance(data.get('entities'), list):
            for entity in data['entities']:
                if isinstance(entity, dict) and 'entity_value' in entity:
                    val = entity['entity_value']
                    if re.search(r'\[.*\]', val) or re.search(r'\{.*\}', val):
                        issues.append(f"Possible JSON artifact found in entity: {val}")
        
        return {
            "issues": issues,
            "quality_score": 1.0 - min(len(issues) / 10.0, 1.0),  # Simple quality score
            "is_valid": len(issues) == 0
        }