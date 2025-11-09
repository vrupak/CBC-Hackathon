"""
Utility functions for processing uploaded files
"""
from pathlib import Path
from typing import Optional
import PyPDF2
import aiofiles
import mimetypes # New import

# Mimetypes setup to ensure common types are known
mimetypes.init()
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("text/plain", ".txt")


def get_mime_type_for_path(file_path: Path) -> str:
    """
    Determines the file's MIME type based on its extension.
    Raises ValueError for unsupported types.
    """
    mime_type, _ = mimetypes.guess_type(file_path.name)
    
    # Simple check for the types we support
    if mime_type == "application/pdf":
        return "application/pdf"
    elif mime_type == "text/plain":
        return "text/plain"
    else:
        # Fallback to check extension if mimetypes fails for common types
        extension = file_path.suffix.lower()
        if extension == '.pdf':
            return "application/pdf"
        elif extension == '.txt':
            return "text/plain"
        
        # Raise error for unsupported file types
        raise ValueError(f"Unsupported file type for path {file_path}: {mime_type or extension}")


async def extract_text_from_file(file_path: Path) -> str:
    """
    Extract text content from uploaded file (PDF or TXT).
    The file type is now determined internally from the path.
    """
    try:
        file_type = get_mime_type_for_path(file_path)
        
        if file_type == "application/pdf":
            return await extract_text_from_pdf(file_path)
        elif file_type == "text/plain":
            return await extract_text_from_txt(file_path)
        else:
            # Should be caught by get_mime_type_for_path, but here for robustness
            raise ValueError(f"Unsupported file type: {file_type}")
    except Exception as e:
        # Re-raise with better context
        raise Exception(f"Error extracting text from file {file_path}: {str(e)}")


async def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file"""
    text = ""
    # PyPDF2 needs a file-like object, so we use regular open for PDF
    with open(file_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


async def extract_text_from_txt(file_path: Path) -> str:
    """Extract text from TXT file"""
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    return content.strip()