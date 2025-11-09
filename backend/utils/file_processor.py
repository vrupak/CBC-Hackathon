"""
Utility functions for processing uploaded files
"""
from pathlib import Path
from typing import Optional
import PyPDF2
import aiofiles


async def extract_text_from_file(file_path: Path, file_type: str) -> str:
    """
    Extract text content from uploaded file (PDF or TXT)
    """
    try:
        if file_type == "application/pdf":
            return await extract_text_from_pdf(file_path)
        elif file_type == "text/plain":
            return await extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    except Exception as e:
        raise Exception(f"Error extracting text from file: {str(e)}")


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

