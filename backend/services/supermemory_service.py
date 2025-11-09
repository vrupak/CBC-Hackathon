"""
Supermemory service for RAG integration
"""
import os
import httpx
import re
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load .env from backend directory first, then fall back to root directory
# __file__ is in backend/services/, so go up 1 level to reach backend/
backend_env_path = Path(__file__).parent.parent / ".env"
root_env_path = Path(__file__).parent.parent.parent / ".env"

if backend_env_path.exists():
    load_dotenv(dotenv_path=backend_env_path)
elif root_env_path.exists():
    load_dotenv(dotenv_path=root_env_path)
else:
    load_dotenv()

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
                # content: string (required) - The content to process into a document
                # containerTag: string (optional) - Single tag to group related memories
                # metadata: object (optional) - Additional key-value metadata
                # customId: string (optional) - Your own identifier for this document
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
                # Must contain only alphanumeric characters, hyphens, and underscores
                # Remove file extension and sanitize
                base_name = Path(filename).stem  # Get filename without extension
                # Replace spaces and special characters with hyphens
                # Keep only alphanumeric, hyphens, and underscores
                sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', base_name)
                # Remove consecutive hyphens
                sanitized = re.sub(r'-+', '-', sanitized)
                # Remove leading/trailing hyphens
                sanitized = sanitized.strip('-')
                # Ensure we have a valid ID (if empty after sanitization, use a default)
                if not sanitized:
                    # Use file_id from metadata if available, otherwise use a timestamp-based ID
                    file_id_from_meta = metadata.get("file_id", "") if metadata else ""
                    if file_id_from_meta:
                        sanitized = f"document-{file_id_from_meta[:8]}"
                    else:
                        sanitized = f"document-{int(time.time())}"
                # Max 255 characters as per API docs
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
                print(f"[DEBUG] Supermemory response headers: {dict(response.headers)}")
                
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
        top_k: Optional[int] = None,  # Backward compatibility
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Query Supermemory RAG for relevant context with retry logic.

        Documents must be fully processed (status != "queued") before they can be searched.
        This method implements exponential backoff retry if search fails initially,
        as documents may still be processing.

        Args:
            query: The search query
            container_tag: The container to search in
            limit: Number of results to return
            top_k: Alias for limit (backward compatibility)
            retry_count: Number of times to retry if search fails (default 3)
            retry_delay: Initial delay between retries in seconds (exponential backoff)

        Returns:
            Relevant context from Supermemory
        """
        # Use top_k if provided (backward compatibility), otherwise use limit
        if top_k is not None:
            limit = top_k

        last_error = None

        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient() as client:
                    payload = {
                        "q": query,
                        "limit": limit
                    }

                    if container_tag:
                        payload["containerTag"] = container_tag

                    print(f"[DEBUG] Supermemory search attempt {attempt + 1}/{retry_count}")
                    print(f"[DEBUG] Supermemory search URL: {self.base_url}/search")
                    print(f"[DEBUG] Supermemory search payload: {payload}")

                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self.headers,
                        json=payload,
                        timeout=30.0
                    )

                    print(f"[DEBUG] Supermemory search response status: {response.status_code}")

                    # Handle 404 - document may still be processing
                    if response.status_code == 404:
                        if attempt < retry_count - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            print(f"[WARN] Supermemory search returned 404 (attempt {attempt + 1})")
                            print(f"[INFO] Retrying in {wait_time}s... (documents may still be processing)")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"[WARN] Supermemory search returned 404 after {retry_count} attempts")
                            return {"results": [], "message": "Documents still being processed"}

                    response.raise_for_status()
                    result = response.json()
                    result_count = len(result.get('results', []))
                    print(f"[DEBUG] Supermemory search returned {result_count} results")
                    return result

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    last_error += f": {error_body}"
                except:
                    last_error += f": {e.response.text[:500]}"

                if attempt < retry_count - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"[WARN] Supermemory search error: {last_error} (attempt {attempt + 1})")
                    print(f"[INFO] Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[ERROR] Supermemory search HTTP error after {retry_count} attempts: {last_error}")
                    raise Exception(f"Supermemory search HTTP error: {last_error}")

            except httpx.HTTPError as e:
                error_msg = f"Supermemory search network error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                if attempt == retry_count - 1:
                    raise Exception(error_msg)
                else:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"[INFO] Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                error_msg = f"Error querying Supermemory: {str(e)}"
                print(f"[ERROR] {error_msg}")
                if attempt == retry_count - 1:
                    raise Exception(error_msg)
                else:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"[INFO] Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

        # If we've exhausted all retries without returning, raise the last error
        if last_error:
            raise Exception(f"Supermemory search failed after {retry_count} attempts: {last_error}")
        raise Exception("Supermemory search failed: Unknown error")

