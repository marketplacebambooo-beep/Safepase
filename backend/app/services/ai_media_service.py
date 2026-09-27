"""File extraction and audio transcription for AI chat."""

import base64
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_EXCERPT_CHARS = 6000
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _openai_headers() -> dict:
    return {"Authorization": f"Bearer {settings.openai_api_key}"}


def transcribe_audio(content: bytes, filename: str) -> str | None:
    if not settings.openai_api_key:
        return None
    try:
        resp = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/audio/transcriptions",
            headers=_openai_headers(),
            files={"file": (filename or "recording.webm", content, "audio/webm")},
            data={"model": "whisper-1"},
            timeout=60.0,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code == 200:
            return (data.get("text") or "").strip()
        logger.error("Whisper error (%s): %s", resp.status_code, data)
    except Exception as exc:
        logger.exception("Whisper transcription failed: %s", exc)
    return None


def _describe_image(content: bytes, filename: str) -> str | None:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "jpeg").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    if mime not in ("jpeg", "png", "webp", "gif"):
        mime = "jpeg"
    b64 = base64.b64encode(content).decode("ascii")
    try:
        resp = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={**_openai_headers(), "Content-Type": "application/json"},
            json={
                "model": settings.openai_model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe this image for a maternal health clinic assistant. "
                                "Extract any visible text, forms, or clinical notes. Be concise."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
                    ],
                }],
                "max_tokens": 400,
            },
            timeout=45.0,
        )
        data = resp.json()
        if resp.status_code == 200:
            return data["choices"][0]["message"]["content"].strip()
        logger.error("Vision error (%s): %s", resp.status_code, data)
    except Exception as exc:
        logger.exception("Image analysis failed: %s", exc)
    return None


def extract_file_content(content: bytes, filename: str) -> tuple[str, str]:
    """Return (message_type, excerpt) for chat context."""
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("File too large (max 5 MB).")

    lower = filename.lower()
    ext = lower.rsplit(".", 1)[-1] if "." in lower else ""

    if f".{ext}" in TEXT_EXTENSIONS or ext in {e.lstrip(".") for e in TEXT_EXTENSIONS}:
        text = content.decode("utf-8", errors="replace").strip()
        excerpt = text[:MAX_EXCERPT_CHARS]
        if len(text) > MAX_EXCERPT_CHARS:
            excerpt += "\n\n[Truncated for length]"
        return "file", excerpt or "(Empty file)"

    if f".{ext}" in IMAGE_EXTENSIONS:
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key required to analyze images.")
        description = _describe_image(content, filename)
        if not description:
            raise ValueError("Could not analyze image.")
        return "file", description

    raise ValueError("Unsupported file type. Use text (.txt, .csv, .md) or image (.jpg, .png).")
