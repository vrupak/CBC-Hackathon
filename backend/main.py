from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
import aiofiles
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
import uuid
from datetime import datetime

from utils.file_processor import extract_text_from_file
from services.supermemory_service import SupermemoryService
from services.claude_service import ClaudeService
from services.claude_client import ClaudeClient

# Web search support (placeholder for future integration with web search API)
async def web_search(query: str) -> str:
    """
    Placeholder web search function.
    In production, this would integrate with a real web search API (Google, Bing, etc.)
    For now, returns formatted notice that web search would be performed.

    Args:
        query: Search query

    Returns:
        Search results as formatted string
    """
    # TODO: Integrate with actual web search API
    # For now, return a placeholder indicating web search capability
    return f"[Web search results for: '{query}' would appear here with actual search integration]"

# Request/Response models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = None
    file_id: Optional[str] = None  # ID of uploaded material for context

class ChatResponse(BaseModel):
    success: bool
    response: str
    message: Optional[str] = None
    context_used: Optional[bool] = None
    web_search_used: Optional[bool] = None
    stored_in_memory: Optional[bool] = None

app = FastAPI(title="AI Study Buddy API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
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

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with Supermemory RAG + Claude Sonnet 4.5

    Complete workflow:
    1. Retrieve relevant context from Supermemory if file_id provided
    2. Claude answers using study material first, then web if needed
    3. Store Q&A pair in Supermemory for conversation history
    4. Return response to frontend

    Request:
    {
        "message": "user message",
        "conversation_history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "file_id": "optional-file-id-for-context"
    }

    Response:
    {
        "success": true,
        "response": "assistant response",
        "context_used": false,
        "stored_in_memory": true
    }
    """
    try:
        print(f"[INFO] Received chat message: {request.message[:100]}...")

        # Initialize services
        claude_client = ClaudeClient()
        supermemory_service = get_supermemory_service()
        context = None
        context_used = False

        # STEP 1: Retrieve context from Supermemory (if file_id provided)
        if request.file_id and supermemory_service:
            try:
                print(f"[INFO] STEP 1: Retrieving context from Supermemory for file_id: {request.file_id}")
                rag_results = await supermemory_service.query(request.message, limit=3)

                # Extract context from results
                if isinstance(rag_results, dict):
                    if "results" in rag_results:
                        context = "\n\n".join([
                            str(result.get("content", result.get("text", "")))
                            for result in rag_results["results"]
                        ])
                    elif "content" in rag_results:
                        context = str(rag_results["content"])
                    elif "data" in rag_results:
                        data = rag_results["data"]
                        if isinstance(data, list):
                            context = "\n\n".join([
                                str(item.get("content", item.get("text", "")))
                                for item in data
                            ])
                        elif isinstance(data, dict) and "content" in data:
                            context = str(data["content"])

                if context and len(context.strip()) > 0:
                    context_used = True
                    print(f"[INFO] ✓ Retrieved context from Supermemory ({len(context)} chars)")
                else:
                    context = None
                    print("[INFO] No relevant context found in Supermemory (will use general knowledge)")
            except Exception as e:
                print(f"[WARN] Failed to retrieve context from Supermemory: {e}")
                context = None

        # STEP 2: Get Claude's answer using context (or web search if needed)
        chat_history = None
        if request.conversation_history:
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        print(f"[INFO] STEP 2: Sending question to Claude Sonnet 4.5 (context_available={context is not None})")
        # Use answer_with_web_search for smart context + web search fallback
        answer, response_context_used, web_search_used = await claude_client.answer_with_web_search(
            question=request.message,
            context=context,
            chat_history=chat_history,
            web_search_fn=web_search
        )

        print(f"[INFO] ✓ Received answer from Claude ({len(answer)} chars)")
        print(f"[INFO] Response flags: context_used={response_context_used}, web_search_used={web_search_used}")

        # STEP 3: Store Q&A pair in Supermemory for conversation history
        memory_stored = False
        if supermemory_service and request.file_id:
            try:
                print(f"[INFO] STEP 3: Storing Q&A in Supermemory for conversation history...")

                # Create conversation entry combining question and answer
                conversation_entry = f"Q: {request.message}\n\nA: {answer}"

                memory_response = await supermemory_service.ingest_document(
                    content=conversation_entry,
                    filename=f"conversation-{request.file_id[:8]}.md",
                    metadata={
                        "type": "conversation",
                        "file_id": request.file_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "context_used": str(response_context_used),
                        "web_search_used": str(web_search_used),
                        "model": "claude-sonnet-4-5"
                    }
                )

                memory_stored = True
                print(f"[INFO] ✓ Conversation stored in Supermemory (ID: {memory_response.get('id', 'unknown')})")
            except Exception as e:
                print(f"[WARN] Failed to store conversation in Supermemory: {e}")
                memory_stored = False

        # STEP 4: Return response
        print(f"[INFO] Returning chat response to frontend")
        return ChatResponse(
            success=True,
            response=answer,
            context_used=response_context_used,
            web_search_used=web_search_used,
            stored_in_memory=memory_stored,
            message=f"Context used: {response_context_used}, Web search used: {web_search_used}, Stored in memory: {memory_stored}"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Chat request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint - returns tokens as they are generated

    Request format same as /api/chat
    Response: Server-Sent Events (SSE) with JSON chunks

    Each line contains JSON:
    - {"metadata": {"context_used": bool, "web_search_used": bool}} (first chunk)
    - {"text": "token"} (subsequent chunks)
    - {"done": true} (final chunk)
    """
    try:
        print(f"[INFO] Received streaming chat request: {request.message[:100]}...")

        # Initialize services
        try:
            claude_client = ClaudeClient()
        except ValueError as e:
            print(f"[ERROR] Claude service initialization failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="Claude API is not configured. Please set ANTHROPIC_API_KEY in your .env file."
            )

        supermemory_service = get_supermemory_service()
        context = None
        context_used = False

        # STEP 1: Retrieve context from Supermemory (if file_id provided)
        if request.file_id and supermemory_service:
            try:
                print(f"[INFO] Retrieving context from Supermemory for file_id: {request.file_id}")
                # Increase retry count and delay to give documents more time to index
                rag_results = await supermemory_service.query(
                    request.message,
                    limit=3,
                    retry_count=5,  # Increased from 3
                    retry_delay=2.0  # Increased from 1.0
                )

                # Extract context from results
                if isinstance(rag_results, dict):
                    if "results" in rag_results:
                        context = "\n\n".join([
                            str(result.get("content", result.get("text", "")))
                            for result in rag_results["results"]
                        ])
                    elif "content" in rag_results:
                        context = str(rag_results["content"])
                    elif "data" in rag_results:
                        data = rag_results["data"]
                        if isinstance(data, list):
                            context = "\n\n".join([
                                str(item.get("content", item.get("text", "")))
                                for item in data
                            ])
                        elif isinstance(data, dict) and "content" in data:
                            context = str(data["content"])

                if context and len(context.strip()) > 0:
                    context_used = True
                    print(f"[INFO] Retrieved context from Supermemory ({len(context)} chars)")
                else:
                    context = None
                    print("[INFO] No relevant context found in Supermemory")
            except Exception as e:
                print(f"[WARN] Failed to retrieve context from Supermemory: {e}")
                context = None

        # STEP 2: Stream response from Claude
        chat_history = None
        if request.conversation_history:
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        print(f"[INFO] Streaming response from Claude Sonnet 4.5")

        # Create streaming generator (async)
        async def generate():
            import sys
            import json
            import asyncio

            full_response = ""
            response_context_used = False
            web_search_used = False
            chunk_count = 0

            try:
                # Stream from Claude (async generator)
                async for chunk in claude_client.answer_with_web_search_stream(
                    question=request.message,
                    context=context,
                    chat_history=chat_history,
                    web_search_fn=web_search
                ):
                    chunk_count += 1
                    print(f"[STREAM] Yielding chunk {chunk_count}", file=sys.stderr, flush=True)

                    # Ensure chunk ends with newline for proper line delimitering
                    chunk_to_send = chunk + "\n" if not chunk.endswith("\n") else chunk
                    yield chunk_to_send

                    # Force a brief async yield to allow client to receive this chunk immediately
                    await asyncio.sleep(0.001)

                    # Extract metadata and text from chunks for memory storage
                    try:
                        data = json.loads(chunk.strip())
                        if "metadata" in data:
                            response_context_used = data["metadata"]["context_used"]
                            web_search_used = data["metadata"]["web_search_used"]
                        elif "text" in data:
                            full_response += data["text"]
                    except:
                        pass

                # STEP 3: Store Q&A pair in Supermemory after streaming completes
                if supermemory_service and request.file_id and full_response:
                    try:
                        print(f"[INFO] Storing Q&A in Supermemory...")
                        conversation_entry = f"Q: {request.message}\n\nA: {full_response}"

                        await supermemory_service.ingest_document(
                            content=conversation_entry,
                            filename=f"conversation-{request.file_id[:8]}.md",
                            metadata={
                                "type": "conversation",
                                "file_id": request.file_id,
                                "timestamp": datetime.utcnow().isoformat(),
                                "context_used": str(response_context_used),
                                "web_search_used": str(web_search_used),
                                "model": "claude-sonnet-4-5"
                            }
                        )
                        print(f"[INFO] Conversation stored in Supermemory")
                    except Exception as e:
                        print(f"[WARN] Failed to store conversation in Supermemory: {e}")

            except Exception as e:
                print(f"[ERROR] Streaming error: {str(e)}")
                error_chunk = json.dumps({
                    "error": str(e),
                    "text": "An error occurred while streaming the response."
                }) + "\n"
                yield error_chunk

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Streaming chat request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing streaming chat request: {str(e)}"
        )

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

# ============================================================================
# PERSISTENCE ENDPOINTS - Save/Load study state and progress from Supermemory
# ============================================================================

class StudyProgress(BaseModel):
    """Study progress data to persist"""
    file_id: str
    filename: str
    topics: list  # List of topics with subtopic completion status
    overall_progress: float  # Percentage complete
    last_updated: str
    title: str = "Study Progress"

@app.post("/api/study-progress/save")
async def save_study_progress(progress: StudyProgress):
    """
    Study progress endpoint (disabled - no longer saving to Supermemory)

    Progress is now stored locally in sessionStorage only.
    This endpoint remains for backward compatibility.
    """
    # No-op: Progress is stored locally in sessionStorage only
    print(f"[INFO] Study progress save request received for file_id: {progress.file_id} (not saving to Supermemory)")
    return {
        "success": True,
        "message": "Study progress tracked locally"
    }

@app.get("/api/study-progress/load/{file_id}")
async def load_study_progress(file_id: str):
    """
    Load study progress endpoint (disabled - no longer loading from Supermemory)

    Progress is now stored locally in sessionStorage only.
    This endpoint remains for backward compatibility.
    """
    # No-op: Progress is stored locally in sessionStorage only
    print(f"[INFO] Study progress load request received for file_id: {file_id} (not loading from Supermemory)")
    return {
        "success": False,
        "message": "Progress is tracked locally only",
        "progress_data": None
    }

@app.get("/api/materials/list")
async def list_uploaded_materials():
    """
    List all previously uploaded materials for the current session

    Returns a list of files the user has uploaded, allowing them to
    switch between different study materials.
    """
    try:
        supermemory_service = get_supermemory_service()
        if not supermemory_service:
            return JSONResponse(
                status_code=503,
                content={"error": "Supermemory service not available"}
            )

        print("[INFO] Listing uploaded materials...")

        # Query for all uploaded documents (not conversations or progress)
        search_results = await supermemory_service.query(
            query="uploaded document material study",
            limit=20
        )

        materials = []
        if search_results and search_results.get("results"):
            for result in search_results["results"]:
                content = result.get("content", "")
                # Filter out conversation and progress records
                if "progress" not in content.lower() and "Q:" not in content:
                    materials.append({
                        "id": result.get("id"),
                        "content_preview": content[:200],
                        "timestamp": result.get("timestamp"),
                    })

        return {
            "success": True,
            "materials": materials,
            "count": len(materials)
        }

    except Exception as e:
        print(f"[ERROR] Failed to list materials: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "materials": []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)