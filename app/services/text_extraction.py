import io

from pypdf import PdfReader

from app.core.exceptions import UnsupportedFileTypeError

_SUPPORTED_EXTENSIONS = (".pdf", ".txt")


def extract_text(filename: str, content: bytes) -> str:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return _extract_pdf_text(content)
    if lowered.endswith(".txt"):
        return _extract_txt_text(content)
    raise UnsupportedFileTypeError(
        f"Unsupported file type for '{filename}'. Supported extensions: {_SUPPORTED_EXTENSIONS}"
    )


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text).strip()


def _extract_txt_text(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore").strip()
