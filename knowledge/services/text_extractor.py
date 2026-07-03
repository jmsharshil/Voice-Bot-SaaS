import os
import io
from PyPDF2 import PdfReader
from docx import Document


def extract_text(file_source):
    # Determine the file name / extension
    if isinstance(file_source, (str, os.PathLike)):
        filename = os.fspath(file_source)
        ext = os.path.splitext(filename)[1].lower()
        
        # Read the file content
        if ext == ".txt":
            with open(file_source, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            with open(file_source, "rb") as f:
                stream = io.BytesIO(f.read())
    else:
        filename = getattr(file_source, "name", "")
        ext = os.path.splitext(filename)[1].lower()
        
        # Open and read the stream
        if hasattr(file_source, "open"):
            # Django's FieldFile should be opened
            with file_source.open("rb") as f:
                content = f.read()
        else:
            content = file_source.read()
            
        if ext == ".txt":
            if isinstance(content, bytes):
                return content.decode("utf-8", errors="ignore")
            return content
        else:
            stream = io.BytesIO(content)

    # Process PDF or DOCX using the in-memory stream
    if ext == ".pdf":
        reader = PdfReader(stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif ext == ".docx":
        doc = Document(stream)
        return "\n".join([p.text for p in doc.paragraphs])

    return ""