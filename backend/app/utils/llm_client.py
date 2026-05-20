"""
LLM Client - Unified interface for LLM calls (OpenAI-compatible)
Supports OpenAI, DeepSeek, Qwen, and any OpenAI-format API
"""

import json
from typing import List, Dict, Any, Optional

from openai import OpenAI

from ..config import Config
from .logger import get_logger

logger = get_logger('memecoin.utils.llm')


class LLMClient:
    """Unified LLM client using OpenAI SDK format"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(self, prompt: str, temperature: float = 0.7,
             max_tokens: int = 4096, system_prompt: str = None) -> str:
        """
        Simple chat completion with a single prompt
        
        Args:
            prompt: User message
            temperature: Creativity (0.0 = deterministic, 1.0 = creative)
            max_tokens: Max response length
            system_prompt: Optional system message
            
        Returns:
            Response text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.chat_messages(messages, temperature=temperature, max_tokens=max_tokens)
    
    def chat_messages(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = 4096) -> str:
        """
        Chat completion with full message history
        
        Args:
            messages: List of {"role": "...", "content": "..."} messages
            temperature: Creativity level
            max_tokens: Max response length
            
        Returns:
            Response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            
            # Log usage
            usage = response.usage
            if usage:
                logger.debug(
                    f"LLM call: model={self.model}, "
                    f"prompt_tokens={usage.prompt_tokens}, "
                    f"completion_tokens={usage.completion_tokens}"
                )
            
            return content or ""
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def chat_json(self, prompt: str, temperature: float = 0.3,
                  system_prompt: str = None) -> Dict[str, Any]:
        """
        Chat completion expecting JSON response
        Automatically parses JSON from response
        
        Args:
            prompt: User message (should instruct JSON output)
            temperature: Lower is better for structured output
            system_prompt: Optional system message
            
        Returns:
            Parsed JSON dictionary
        """
        response = self.chat(
            prompt=prompt,
            temperature=temperature,
            system_prompt=system_prompt
        )
        
        return self._parse_json(response)
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks"""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code block
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                pass
        
        if "```" in text:
            try:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                pass
        
        # Try finding JSON object in text
        try:
            start = text.index('{')
            end = text.rindex('}') + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass
        
        # Try finding JSON array
        try:
            start = text.index('[')
            end = text.rindex(']') + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass
        
        logger.warning(f"Failed to parse JSON from LLM response: {text[:200]}...")
        return {"raw_response": text, "parse_error": True}
