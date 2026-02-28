import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url or "https://api.openai.com/v1"
        self.default_model = settings.llm_default_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response from LLM with retry logic
        """
        model = model or self.default_model
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add response format for JSON mode if supported by the provider
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            start_time = time.time()
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Calculate token usage
            usage = result.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            
            logger.info(f"LLM call completed - model: {model}, "
                       f"in_tokens: {tokens_in}, out_tokens: {tokens_out}, "
                       f"duration: {time.time() - start_time:.2f}s")
            
            # Extract the content
            content = result["choices"][0]["message"]["content"]
            
            return {
                "content": content,
                "model": model,
                "tokens_used": tokens_in + tokens_out,
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "processing_time": time.time() - start_time
            }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM API: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling LLM API: {str(e)}")
            raise
    
    async def validate_and_repair_json(
        self, 
        content: str, 
        schema_description: str,
        repair_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Validate JSON content and attempt repairs if needed
        """
        # First, try to parse the content as JSON
        parsed_json = None
        for attempt in range(repair_attempts + 1):
            try:
                parsed_json = json.loads(content)
                # If successful, break out of the loop
                break
            except json.JSONDecodeError as e:
                if attempt == repair_attempts:
                    # Last attempt, raise the error
                    raise ValueError(f"Could not parse JSON after {repair_attempts} repair attempts. Error: {str(e)}")
                
                # Try to repair the JSON
                logger.warning(f"JSON parsing failed, attempting repair (attempt {attempt + 1}/{repair_attempts}). Error: {str(e)}")
                content = await self.repair_json(content, schema_description)
        
        return parsed_json
    
    async def repair_json(self, content: str, schema_description: str) -> str:
        """
        Attempt to repair malformed JSON using LLM
        """
        repair_prompt = f"""
        The following JSON content is malformed and needs to be repaired according to the schema:
        
        SCHEMA DESCRIPTION:
        {schema_description}
        
        MALFORMED CONTENT:
        {content}
        
        Please return only the corrected JSON content without any additional explanation or markdown formatting.
        """
        
        repair_result = await self.generate_response(
            prompt=repair_prompt,
            temperature=0.1,
            max_tokens=2000,
            json_mode=False  # We don't want to enforce JSON mode during repair
        )
        
        # Clean up the response to extract just the JSON
        repaired_content = self._extract_json_from_response(repair_result["content"])
        return repaired_content
    
    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from LLM response that might contain additional text
        """
        # Look for JSON within code blocks
        if "```json" in content:
            start_idx = content.find("```json") + 7
            end_idx = content.find("```", start_idx)
            if end_idx != -1:
                return content[start_idx:end_idx].strip()
        
        # Look for general code blocks
        if "```" in content:
            first_block = content.split("```")[1]
            # Check if it looks like JSON
            if first_block.strip().startswith("{") or first_block.strip().startswith("["):
                return first_block.strip()
        
        # If no code blocks, return the original content
        return content
    
    async def batch_generate_responses(
        self, 
        prompts: List[str], 
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate responses for multiple prompts concurrently
        """
        tasks = [
            self.generate_response(prompt, model, temperature)
            for prompt in prompts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing prompt {i}: {str(result)}")
                processed_results.append({
                    "error": str(result),
                    "content": None,
                    "tokens_used": 0,
                    "processing_time": 0
                })
            else:
                processed_results.append(result)
        
        return processed_results