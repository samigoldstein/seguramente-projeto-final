"""Recepção e extração de documentos PDF/imagem."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from .models import DocumentPage, PolicyDocument

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


class IngestionError(RuntimeError):
    """Erro controlado na leitura de documentos."""


def document_id_for(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()[:12].upper()


def extract_pdf_pages(path: str | Path) -> list[DocumentPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise IngestionError("Instale pypdf para ler PDFs.") from exc
    document_id = document_id_for(path)
    reader = PdfReader(str(path))
    pages: list[DocumentPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        method = "pdf-text"
        if len(text) < 20:
            text = _ocr_pdf_page(path, index) or text
            method = "ocr" if len(text) >= 20 else "pdf-text-empty"
        pages.append(DocumentPage(document_id, index, text, method))
    return pages


def extract_image_pages(path: str | Path) -> list[DocumentPage]:
    text = _ocr_image(path)
    document_id = document_id_for(path)
    return [DocumentPage(document_id, 1, text, "ocr" if text else "ocr-empty")]


def load_document(path: str | Path, name: str | None = None, source: str = "documento fornecido pelo usuário") -> PolicyDocument:
    path_obj = Path(path)
    if path_obj.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise IngestionError(f"Formato não suportado: {path_obj.suffix or 'sem extensão'}")
    if not path_obj.exists() or path_obj.stat().st_size == 0:
        raise IngestionError(f"Arquivo inexistente ou vazio: {path_obj}")
    if path_obj.suffix.lower() == ".pdf":
        pages = extract_pdf_pages(path_obj)
    else:
        pages = extract_image_pages(path_obj)
    return PolicyDocument(
        document_id=document_id_for(path_obj),
        name=name or path_obj.name,
        path=str(path_obj),
        source=source,
        pages=pages,
    )


def _ocr_pdf_page(path: str | Path, page_number: int) -> str:
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(path), dpi=180, first_page=page_number, last_page=page_number)
        return _ocr_image_object(images[0]) if images else ""
    except Exception:
        return ""


def _ocr_image(path: str | Path) -> str:
    try:
        from PIL import Image

        return _ocr_image_object(Image.open(path))
    except Exception:
        return ""


def _ocr_image_object(image: object) -> str:
    try:
        import pytesseract

        return str(pytesseract.image_to_string(image, lang="por+eng")).strip()
    except Exception:
        return ""
