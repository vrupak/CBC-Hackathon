from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import aiofiles
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime

from utils.file_processor import extract_text_from_file
from services.supermemory_service import SupermemoryService
from services.claude_service import ClaudeService

app = FastAPI(title="AI Study Buddy API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize services
_supermemory_service: Optional[SupermemoryService] = None
_claude_service: Optional[ClaudeService] = None

def get_supermemory_service() -> Optional[SupermemoryService]:
    """Get or initialize Supermemory service"""
    global _supermemory_service
    if _supermemory_service is None:
        try:
            _supermemory_service = SupermemoryService()
        except ValueError as e:
            print(f"[WARN] Supermemory service not available: {e}")
    return _supermemory_service

def get_claude_service() -> Optional[ClaudeService]:
    """Get or initialize Claude service"""
    global _claude_service
    if _claude_service is None:
        try:
            _claude_service = ClaudeService()
        except ValueError as e:
            print(f"[WARN] Claude service not available: {e}")
    return _claude_service

@app.get("/")
async def root():
    return {"message": "AI Study Buddy API", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "supermemory_configured": get_supermemory_service() is not None,
        "claude_configured": get_claude_service() is not None
    }

@app.post("/api/upload-material")
async def upload_material(file: UploadFile = File(...)):
    """
    Upload study material and process it
    
    Returns format expected by frontend:
    {
        "success": boolean,
        "materialId": string,
        "message": string (optional)
    }
    """
    file_id = None
    file_path = None
    
    try:
        print(f"[INFO] Received upload request for file: {file.filename}")
        print(f"[INFO] Content type: {file.content_type}")
        
        # Validate file type
        allowed_types = ["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not supported. Please upload PDF, TXT, or DOCX files."
            )
        
        # Generate unique ID
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        saved_filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename
        
        print(f"[INFO] Saving file to: {file_path}")
        
        # Save file to disk
        file_content_bytes = await file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content_bytes)
        
        print(f"[INFO] File saved successfully. Size: {len(file_content_bytes)} bytes")
        
        # Extract text from file
        print("[INFO] Extracting text from file...")
        extracted_text = await extract_text_from_file(file_path, file.content_type)
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from file. Please ensure the file contains readable text."
            )
        
        print(f"[INFO] Text extracted successfully. Length: {len(extracted_text)} characters")
        
        # Initialize response data (backend format for logging)
        processing_data = {
            "file_id": file_id,
            "filename": file.filename,
            "saved_path": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "text_length": len(extracted_text)
        }
        
        # Try to ingest to Supermemory
        supermemory_service = get_supermemory_service()
        memory_response = None
        if supermemory_service:
            try:
                print(f"[INFO] Ingesting document to Supermemory...")
                memory_response = await supermemory_service.ingest_document(
                    content=extracted_text,
                    filename=file.filename,
                    metadata={
                        "file_id": file_id,
                        "content_type": file.content_type,
                        "uploaded_at": datetime.utcnow().isoformat()
                    }
                )
                print(f"[INFO] Supermemory ingestion successful: {memory_response}")
                processing_data["supermemory_ingested"] = True
                processing_data["memory_id"] = memory_response.get("id")
                processing_data["memory_status"] = memory_response.get("status", "unknown")
            except Exception as e:
                print(f"[ERROR] Supermemory ingestion failed: {e}")
                processing_data["supermemory_ingested"] = False
                processing_data["supermemory_error"] = str(e)
                memory_response = None
        else:
            print("[WARN] Supermemory service not configured")
            processing_data["supermemory_ingested"] = False
        
        # Try to extract topics with Claude
        claude_service = get_claude_service()
        if claude_service:
            try:
                print("[INFO] Extracting topics with Claude...")
                # Check if document is ready for RAG search (not queued)
                memory_status = memory_response.get("status") if memory_response else None
                use_rag = (
                    supermemory_service 
                    and processing_data.get("supermemory_ingested") 
                    and memory_status == "completed"  # Only use RAG if document is fully processed
                )
                
                if use_rag:
                    try:
                        print("[INFO] Attempting to extract topics with RAG...")
                        topics_response = await claude_service.extract_topics_with_rag(
                            query="Extract all main topics and subtopics from this document in order of learning importance",
                            supermemory_service=supermemory_service
                        )
                    except Exception as rag_error:
                        print(f"[WARN] RAG search failed (document may still be processing): {rag_error}")
                        print("[INFO] Falling back to direct text extraction...")
                        # Fall back to direct text extraction if RAG fails
                        topics_response = await claude_service.extract_topics(extracted_text)
                else:
                    if memory_status == "queued":
                        print("[INFO] Document is still queued in Supermemory, using direct text extraction...")
                    # Use direct text extraction (faster and more reliable for immediate processing)
                    topics_response = await claude_service.extract_topics(extracted_text)
                
                print(f"[INFO] Topics extracted successfully")
                processing_data["topics_extracted"] = True
                processing_data["topics"] = topics_response.get("topics_text")
            except Exception as e:
                print(f"[ERROR] Topic extraction failed: {e}")
                processing_data["topics_extracted"] = False
                processing_data["topics_error"] = str(e)
        else:
            print("[WARN] Claude service not configured")
            processing_data["topics_extracted"] = False
        
        # Return response in format expected by frontend
        return JSONResponse({
            "success": True,
            "message": "File uploaded and processed successfully",
            "file_id": file_id,
            "filename": file.filename,
            "saved_path": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "text_extracted": True,
            "text_length": len(extracted_text),
            "supermemory_ingested": processing_data.get("supermemory_ingested", False),
            "memory_id": processing_data.get("memory_id"),
            "supermemory_error": processing_data.get("supermemory_error"),
            "topics_extracted": processing_data.get("topics_extracted", False),
            "topics": processing_data.get("topics"),
            "topics_error": processing_data.get("topics_error")
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Upload failed: {str(e)}")
        # Clean up file on error
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as cleanup_error:
                print(f"[ERROR] Failed to cleanup file: {cleanup_error}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)