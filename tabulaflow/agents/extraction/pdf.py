"""PDF text extraction for browser and local-file documents.

Turns raw PDF bytes into plain text for an LLM to read while keeping the pypdf
dependency and extraction logic in one testable place.
"""


def extract_pdf_text(data: bytes) -> tuple[str, str]:
    """Extract ``(title, body_text)`` from PDF bytes with pypdf.

    Uses pypdf's default extraction mode (not ``layout``): on prose-heavy PDFs
    the layout mode collapses inter-word spaces, whereas the default preserves
    them. The multi-column reconstruction layout mode buys is irrelevant for the
    plain-text dump this returns. pypdf's per-page warnings (rotated text, etc.)
    are suppressed — they're advisory and would otherwise spam the logs under
    fan-out. Synchronous and CPU-bound; call via ``asyncio.to_thread``.

    Pages are prefixed with ``--- Page N ---`` markers so the agent can cite and
    navigate by page; empty pages are dropped. Output is NFKC-normalized so
    ligatures (``ﬁ`` -> ``fi``) and split accents come out as plain characters.
    """
    import io
    import unicodedata
    import warnings

    from pypdf import PdfReader

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reader = PdfReader(io.BytesIO(data))
        title = ""
        try:
            title = (reader.metadata.title if reader.metadata else "") or ""
        except Exception:
            pass
        parts = []
        for i, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(f"--- Page {i} ---\n{text}")
    title = unicodedata.normalize("NFKC", title).strip()
    body = unicodedata.normalize("NFKC", "\n\n".join(parts)).strip()
    return title, body
