from __future__ import annotations
import io
from pathlib import Path
from typing import Optional

import pypdf
import docx

def parse_pdf(file_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)

def parse_docx(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs])

def parse_file(file_bytes: bytes, filename: str) -> str:
    """Parse text from PDF, DOCX, or TXT file bytes."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(file_bytes)
    elif ext in [".docx", ".doc"]:
        return parse_docx(file_bytes)
    else:
        # Default to text, treating as utf-8 (ignoring errors)
        return file_bytes.decode("utf-8", errors="replace")
