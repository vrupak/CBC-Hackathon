"""
Claude (Anthropic) service for LLM interactions
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from anthropic import Anthropic
from dotenv import load_dotenv

# Load .env from backend directory
# __file__ is in backend/services/, so go up 1 level to reach backend/
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# Default to Claude Haiku 4.5 (fastest model with near-frontier intelligence)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")


class ClaudeService:
    """
    Service for interacting with Anthropic Claude API
    Handles topic extraction and LLM prompts
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = Anthropic(api_key=self.api_key)
        # Use model from parameter, environment variable, or default to stable version
        self.model = model or CLAUDE_MODEL
        print(f"[INFO] Using Claude model: {self.model}")
    
    # --- JSON SCHEMA DEFINITION ---
    TOPIC_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Unique, sequential ID for the topic, starting at 1."},
                "title": {"type": "string", "description": "The main topic title."},
                "description": {"type": "string", "description": "A brief description explaining why this topic is important and should be learned in this order."},
                "subtopics": {
                    "type": "array",
                    "description": "A list of key subtopics or concepts under this main topic.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "description": "Unique, sequential ID for the subtopic within the main topic."},
                            "title": {"type": "string", "description": "The subtopic or concept name."},
                        },
                        "required": ["id", "title"]
                    }
                }
            },
            "required": ["id", "title", "description", "subtopics"]
        }
    }


    def _build_extraction_prompt(self, document_content: str, supermemory_context: Optional[str] = None) -> str:
        """Helper to build the prompt for topic extraction."""
        # Use the JSON schema to guide the output format
        json_schema_str = json.dumps(self.TOPIC_SCHEMA, indent=2)
        
        prompt_parts = []
        if supermemory_context:
            prompt_parts.append(f"""Given this document and its context, extract a list of all main topics and subtopics in order of learning importance.

Context from document:
{supermemory_context}""")
        
        # Include a smaller snippet of the document content if RAG is used, 
        # or the full content if RAG is skipped (original behavior)
        if not supermemory_context or "[Document content is implicit" in document_content:
             prompt_parts.append(f"""
Document content:
{document_content}""")
        
        prompt_parts.append(f"""
Your task is to analyze the material and create a comprehensive, organized study path.

Instructions:
1. List all **Main Topics** in the most logical learning order.
2. For each Main Topic, list relevant **Subtopics**.
3. Provide a **brief description** explaining the rationale for the learning order.
4. **STRICTLY** output the result as a single JSON array that conforms to this schema, enclosed in a ```json ... ``` block.

JSON Schema:
{json_schema_str}
""")
        return "\n".join(prompt_parts)

    
    async def extract_topics(
        self,
        document_content: str,
        supermemory_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract topics and subtopics from document using LLM.
        """
        try:
            prompt = self._build_extraction_prompt(document_content, supermemory_context)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000, 
                temperature=0.3,
                # --- FIX: Removed 'response_format' and pre-filled message ---
                system="You are an expert educational content analyzer. Your task is to extract and organize topics from study materials in the most logical learning order. You MUST output a JSON object only, enclosed in ```json ... ```.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract the raw text response
            topics_text = message.content[0].text
            
            return {
                "topics_text": topics_text.strip(), # This will be a parsable JSON string
                "model": self.model,
                "raw_response": message
            }
        
        except Exception as e:
            # Added self.model for better error logging
            raise Exception(f"Error extracting topics with Claude model {self.model}: {str(e)}")
    
    async def extract_topics_with_rag(
        self,
        query: str,
        supermemory_service: Any  # SupermemoryService instance
    ) -> Dict[str, Any]:
        """
        Extract topics using Supermemory RAG context
        """
        try:
            # Get relevant context from Supermemory
            rag_context = await supermemory_service.query(query, limit=5)
            
            # Extract context text from RAG results
            context_text = ""
            if isinstance(rag_context, dict):
                # Handle different possible response structures
                if "results" in rag_context:
                    context_text = "\n\n".join([
                        str(result.get("content", result.get("text", ""))) 
                        for result in rag_context["results"]
                    ])
                elif "content" in rag_context:
                    context_text = str(rag_context["content"])
                elif "data" in rag_context:
                    # Handle nested data structure
                    data = rag_context["data"]
                    if isinstance(data, list):
                        context_text = "\n\n".join([
                            str(item.get("content", item.get("text", ""))) 
                            for item in data
                        ])
                    elif isinstance(data, dict) and "content" in data:
                        context_text = str(data["content"])

            # Build prompt using RAG context and the JSON schema
            # Pass document_content as empty string since RAG context is separate
            prompt = self._build_extraction_prompt(
                document_content="",
                supermemory_context=context_text
            )

            # Claude API uses different message structure
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                # --- FIX: Removed 'response_format' and pre-filled message ---
                system="You are an expert educational content analyzer. Your task is to extract and organize topics from study materials in the most logical learning order using the provided context. You MUST output a JSON object only, enclosed in ```json ... ```.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract the raw text response
            topics_text = message.content[0].text

            return {
                "topics_text": topics_text.strip(), # This will be a parsable JSON string
                "model": self.model,
                "rag_context_used": True,
                "raw_response": message
            }
        
        except Exception as e:
            # Added self.model for better error logging
            raise Exception(f"Error extracting topics with RAG with Claude model {self.model}: {str(e)}")