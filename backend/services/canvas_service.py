"""
Canvas API integration service
"""
import os
import httpx
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

# Load .env from root directory (parent of backend/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- Configuration ---
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://canvas.instructure.com/api/v1")


class CanvasService:
    """
    Service for interacting with the Canvas LMS API.
    """
    
    def __init__(self, token: str):
        if not token:
            raise ValueError("Canvas Access Token is required for CanvasService.")
        
        self.token = token
        self.base_url = CANVAS_API_URL.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        # httpx client is initialized with the base_url
        self.client = httpx.AsyncClient(headers=self.headers, base_url=self.base_url, timeout=30.0)
    
    async def get_user_courses(self) -> List[Dict[str, Any]]:
        """
        Fetches the user's current course enrollments from the Canvas API.
        """
        print(f"[INFO] Attempting to fetch live courses from Canvas API at {self.base_url}/courses...")
        
        # --- LIVE API CALL START ---
        response = await self.client.get("/courses?enrollment_state=active&per_page=100")
        
        response.raise_for_status() 
        
        return response.json()
        # --- LIVE API CALL END ---

    async def get_course_files(
        self, 
        canvas_course_id: str, 
        # file_types: Optional[List[str]] = None  # Removed to test without file type filter
    ) -> List[Dict[str, Any]]:
        """
        Fetches the list of files for a specific Canvas course ID.
        """
        endpoint = f"/courses/{canvas_course_id}/files"
        
        params = {
            "per_page": 5000, 
            "sort": "filename", 
        }
        
        # --- CONDITIONAL FILTERING ---
        # NOTE: Temporarily commented out file type filtering based on user feedback
        # if file_types is None:
        #     # Expanded list to cover common study materials, including images and archives
        #     file_types = [
        #         "pdf", "doc", "docx", "pptx", "txt", "rtf", 
        #         "xls", "xlsx", "csv", 
        #         "jpg", "jpeg", "png", "gif", 
        #         "zip", "rar", "7z",
        #         "html", "htm", "xml", "json" # Add web/code formats
        #     ] 
        
        # params["content_types"] = file_types
        # print(f"[INFO] Fetching files for course {canvas_course_id} using types: {file_types}")

        print(f"[INFO] Fetching ALL files for course {canvas_course_id} (No file type filter applied).")
        
        response = await self.client.get(endpoint, params=params)
        
        response.raise_for_status() 
        
        raw_files = response.json()
        
        # Post-filter: Canvas file list may contain folders or files without a download URL.
        # We only want files that have a URL to download (i.e., not a folder and not a hidden resource).
        # This filter is essential and must remain.
        downloadable_files = [f for f in raw_files if f.get('url')]
        
        total_raw_files = len(raw_files)
        total_downloadable = len(downloadable_files)
        
        print(f"[INFO] Raw files received: {total_raw_files}. Downloadable files returned: {total_downloadable}.")
        
        return downloadable_files


    # --- File Download Logic (FIXED for modern httpx streaming) ---
    async def download_file(self, file_url: str, save_path: Path):
        """
        Downloads a file from a Canvas secure URL to a local path.
        """
        # Using a separate client instance here for the download request
        async with httpx.AsyncClient(headers=self.headers, timeout=120.0) as download_client:
            print(f"[INFO] Starting download from: {file_url} to {save_path}")
            
            # --- FIX: Use client.stream() context manager instead of stream=True in get() ---
            async with download_client.stream("GET", file_url, follow_redirects=True) as response:
                response.raise_for_status()

                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(save_path, 'wb') as f:
                    # Use response.aiter_bytes() on the streamed response
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            
            print(f"[INFO] Download successful. File saved at: {save_path}")
            return save_path

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure the AsyncClient is closed."""
        await self.client.aclose()