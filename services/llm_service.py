import asyncio
import json
from typing import Dict, Any, List, Optional
from ..core.llm_client import LLMClient
from ..core.validator import AutoRepairValidator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.validator = AutoRepairValidator(llm_client)
    
    async def extract_structured_data(
        self, 
        text: str, 
        schema_description: str,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from text using LLM
        """
        if custom_prompt:
            prompt = custom_prompt.format(text=text, schema=schema_description)
        else:
            prompt = f"""
            Extract structured information from the following text according to the specified schema.
            
            SCHEMA DESCRIPTION:
            {schema_description}
            
            TEXT TO PROCESS:
            {text}
            
            Please return only the structured data in valid JSON format without any additional explanation or markdown formatting:
            """
        
        try:
            # Generate response from LLM
            response = await self.llm_client.generate_response(
                prompt=prompt,
                json_mode=True
            )
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            # Validate and repair the JSON if needed
            validated_data = await self.validator.validate_and_repair(
                response["content"],
                # Using a generic model here - in practice you'd use specific Pydantic models
                type('TempModel', (), {'model_validate': staticmethod(lambda x: x)})(),
                schema_description
            )
            
            return {
                "success": True,
                "data": validated_data["data"],
                "raw_response": response["content"],
                "tokens_used": response["tokens_used"],
                "processing_time": response["processing_time"]
            }
        
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "tokens_used": 0,
                "processing_time": 0
            }
    
    async def generate_summary(
        self, 
        text: str, 
        summary_type: str = "general",
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate summary of text using LLM
        """
        if custom_prompt:
            prompt = custom_prompt.format(text=text)
        else:
            if summary_type == "concise":
                prompt = f"""
                Provide a concise summary of the following text in 2-3 sentences:
                
                TEXT:
                {text}
                
                SUMMARY:
                """
            elif summary_type == "detailed":
                prompt = f"""
                Provide a detailed summary of the following text covering all key points:
                
                TEXT:
                {text}
                
                SUMMARY:
                """
            else:  # general
                prompt = f"""
                Provide a comprehensive yet concise summary of the following text:
                
                TEXT:
                {text}
                
                SUMMARY:
                """
        
        try:
            response = await self.llm_client.generate_response(prompt)
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            return {
                "success": True,
                "summary": response["content"].strip(),
                "tokens_used": response["tokens_used"],
                "processing_time": response["processing_time"]
            }
        
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "summary": None,
                "tokens_used": 0,
                "processing_time": 0
            }
    
    async def detect_anomalies(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect anomalies in text using LLM
        """
        context_str = json.dumps(context) if context else "{}"
        
        prompt = f"""
        Analyze the following text for anomalies, inconsistencies, or unusual patterns.
        
        CONTEXT:
        {context_str}
        
        TEXT TO ANALYZE:
        {text}
        
        Identify any anomalies and return them in the following JSON format:
        {{
          "anomalies": [
            {{
              "type": "string",
              "description": "string",
              "severity": "low|medium|high|critical",
              "confidence_score": 0.0-1.0,
              "location": "string (page, section, etc.)"
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
                raise Exception(f"LLM error: {response['error']}")
            
            # Validate the response
            validated_data = await self.validator.validate_and_repair(
                response["content"],
                type('AnomalyModel', (), {'model_validate': staticmethod(lambda x: x)})(),
                "JSON with 'anomalies' array containing objects with 'type', 'description', 'severity', 'confidence_score', and 'location' properties"
            )
            
            return {
                "success": True,
                "anomalies": validated_data["data"].get("anomalies", []),
                "raw_response": response["content"],
                "tokens_used": response["tokens_used"],
                "processing_time": response["processing_time"]
            }
        
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "anomalies": [],
                "tokens_used": 0,
                "processing_time": 0
            }
    
    async def classify_text(
        self, 
        text: str, 
        categories: List[str]
    ) -> Dict[str, Any]:
        """
        Classify text into predefined categories using LLM
        """
        categories_str = ", ".join(categories)
        
        prompt = f"""
        Classify the following text into one of these categories: {categories_str}
        
        TEXT:
        {text}
        
        CATEGORY:
        """
        
        try:
            response = await self.llm_client.generate_response(prompt)
            
            if response.get("error"):
                raise Exception(f"LLM error: {response['error']}")
            
            # Extract category from response
            predicted_category = response["content"].strip()
            
            # Validate that the category is in the allowed list
            matched_category = None
            for cat in categories:
                if cat.lower() in predicted_category.lower():
                    matched_category = cat
                    break
            
            if matched_category is None:
                # If no match found, return the first category as fallback
                matched_category = categories[0]
            
            return {
                "success": True,
                "category": matched_category,
                "confidence": 0.8,  # Placeholder - would be determined by LLM in practice
                "raw_response": response["content"],
                "tokens_used": response["tokens_used"],
                "processing_time": response["processing_time"]
            }
        
        except Exception as e:
            logger.error(f"Error classifying text: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "category": categories[0],  # Default fallback
                "confidence": 0.0,
                "tokens_used": 0,
                "processing_time": 0
            }
    
    async def batch_process_requests(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple LLM requests concurrently
        """
        tasks = []
        
        for req in requests:
            func_name = req.get("function", "generate_response")
            args = req.get("args", {})
            
            if func_name == "extract_structured_data":
                task = self.extract_structured_data(**args)
            elif func_name == "generate_summary":
                task = self.generate_summary(**args)
            elif func_name == "detect_anomalies":
                task = self.detect_anomalies(**args)
            elif func_name == "classify_text":
                task = self.classify_text(**args)
            else:
                # Default to generate_response
                task = self.llm_client.generate_response(**args)
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in batch request {i}: {str(result)}")
                processed_results.append({
                    "request_index": i,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "request_index": i,
                    "success": True,
                    "result": result
                })
        
        return processed_results