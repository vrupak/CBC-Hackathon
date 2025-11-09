"""
Canvas API integration service
"""
import os
import httpx
from typing import List, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Load .env from root directory (parent of backend/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- Configuration ---
# You can set CANVAS_API_URL in your .env if needed (e.g., your university's Canvas URL)
# The default is the global Canvas instance
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
        
        Note: This is now a live API call, assuming the environment variable 
        CANVAS_API_URL is correctly set (e.g., to https://canvas.asu.edu/api/v1)
        and CANVAS_TOKEN is a valid token for that instance.
        """
        print(f"[INFO] Attempting to fetch live courses from Canvas API at {self.base_url}/courses...")
        
        # --- LIVE API CALL START ---
        # Request only 'active' enrollments to filter out past/future courses
        # per_page=100 is a good practice to minimize pagination calls
        response = await self.client.get("/courses?enrollment_state=active&per_page=100")
        
        # Raise an exception for 4xx or 5xx status codes (e.g., 401 Unauthorized)
        response.raise_for_status() 
        
        return response.json()
        # --- LIVE API CALL END ---


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure the AsyncClient is closed."""
        await self.client.aclose()