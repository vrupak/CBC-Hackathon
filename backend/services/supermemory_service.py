"""
Supermemory service for RAG integration
"""
import os
import httpx
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load .env from root directory (parent of backend/)
# __file__ is in backend/services/, so go up 2 levels to reach root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPERMEMORY_API_KEY = os.getenv("SUPERMEMORY_API_KEY")
SUPERMEMORY_API_URL = os.getenv("SUPERMEMORY_API_URL", "https://api.supermemory.ai")


class SupermemoryService:
    """
    Service for interacting with Supermemory API
    Handles document ingestion for RAG
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or SUPERMEMORY_API_KEY
        if not self.api_key:
            raise ValueError("SUPERMEMORY_API_KEY environment variable is required")
        
        print(f"Loaded Supermemory API Key (first 10 chars): {self.api_key[:10]}...")
        # Remove trailing slash to avoid double slashes in URLs
        self.base_url = SUPERMEMORY_API_URL.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def ingest_document(
        self,
        content: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest document content into Supermemory
        Supermemory will handle: Extraction, Chunking, Embedding, and Indexing
        
        Uses POST /v3/documents endpoint with JSON payload containing content as string.
        
        Args:
            content: The text content of the document
            filename: Original filename
            metadata: Additional metadata about the document
            
        Returns:
            Response from Supermemory API with memory ID and status
        """
        try:
            async with httpx.AsyncClient() as client:
                # Use the correct endpoint: POST /v3/documents
                upload_url = f"{self.base_url}/v3/documents"
                
                # Prepare payload according to Supermemory API documentation
                payload = {
                    "content": content,
                    "containerTag": "uploaded-documents",  # Group all uploaded documents
                }
                
                # Add metadata if provided
                if metadata:
                    # Ensure metadata only contains strings, numbers, or booleans as per API docs
                    filtered_metadata = {}
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            filtered_metadata[key] = value
                        else:
                            # Convert other types to string
                            filtered_metadata[key] = str(value)
                    payload["metadata"] = filtered_metadata
                
                # Add customId using filename (sanitized)
                base_name = Path(filename).stem
                sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', base_name)
                sanitized = re.sub(r'-+', '-', sanitized)
                sanitized = sanitized.strip('-')
                
                if not sanitized:
                    file_id_from_meta = metadata.get("file_id", "") if metadata else ""
                    if file_id_from_meta:
                        sanitized = f"document-{file_id_from_meta[:8]}"
                    else:
                        sanitized = f"document-{int(time.time())}"
                        
                custom_id = sanitized[:255] if len(sanitized) <= 255 else sanitized[:252] + "..."
                payload["customId"] = custom_id
                print(f"[DEBUG] Original filename: {filename}")
                print(f"[DEBUG] Sanitized customId: {custom_id}")
                
                print(f"[DEBUG] Supermemory upload URL: {upload_url}")
                print(f"[DEBUG] Supermemory payload keys: {list(payload.keys())}")
                print(f"[DEBUG] Content length: {len(content)} characters")
                print(f"[DEBUG] Container tag: {payload.get('containerTag')}")
                
                response = await client.post(
                    upload_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60.0  # Increased timeout for large documents
                )
                
                print(f"[DEBUG] Supermemory response status: {response.status_code}")
                
                try:
                    response_data = response.json()
                    print(f"[DEBUG] Supermemory response body: {response_data}")
                except Exception as json_error:
                    response_text = response.text
                    print(f"[DEBUG] Supermemory response text (not JSON): {response_text[:500]}")
                    print(f"[DEBUG] JSON parse error: {json_error}")
                    response_data = {"raw_response": response_text}
                
                response.raise_for_status()
                return response_data
        
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body}"
            except:
                error_detail += f": {e.response.text[:500]}"
            print(f"[ERROR] Supermemory HTTP error: {error_detail}")
            raise Exception(f"Supermemory API HTTP error: {error_detail}")
        except httpx.HTTPError as e:
            error_msg = f"Supermemory API network error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error ingesting document to Supermemory: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)
    
    async def query(
        self,
        query: str,
        container_tag: str = "uploaded-documents",
        limit: int = 5,
        top_k: Optional[int] = None  # Backward compatibility
    ) -> Dict[str, Any]:
        """
        Query Supermemory RAG for relevant context
        """
        if top_k is not None:
            limit = top_k
        
        try:
            async with httpx.AsyncClient() as client:
                search_url = f"{self.base_url}/v3/search"
                
                payload = {
                    "q": query,
                    "limit": limit
                }
                
                if container_tag:
                    payload["containerTag"] = container_tag
                
                print(f"[DEBUG] Supermemory search URL: {search_url}")
                print(f"[DEBUG] Supermemory search payload: {payload}")
                
                response = await client.post(
                    search_url, 
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                print(f"[DEBUG] Supermemory search response status: {response.status_code}")
                
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body}"
            except:
                error_detail += f": {e.response.text[:500]}"
            print(f"[ERROR] Supermemory search HTTP error: {error_detail}")
            # Raising the specific error detail to the FastAPI layer
            raise Exception(f"Supermemory search HTTP error: HTTP {e.response.status_code}: {e.response.reason_phrase}")
        except httpx.HTTPError as e:
            error_msg = f"Supermemory search network error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error querying Supermemory: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)