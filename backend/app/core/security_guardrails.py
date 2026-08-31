"""
Security Guardrail Module for AI Chatbot.
Handles: Prompt Injection detection, Message validation, Error sanitization.
"""
import io
import re
import zipfile
from pathlib import Path
from typing import Any

# ── Prompt Injection Detection ────────────────────────────────────────────────

INJECTION_PATTERNS = [
    # Classic override attempts
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(everything|all|your)\s+(you've|you\s+have\s+|)learned",
    r"(disregard|override|bypass)\s+(your\s+)?(system|instructions?|rules?|guidelines?)",
    r"you\s+are\s+now\s+(a|an|DAN|jailbreak)",
    r"(act|pretend|roleplay|simulate)\s+(as|like|you're|you are)\s+(a\s+)?(different|new|free|unfiltered)",
    r"(DAN|jailbreak|evil\s+mode|developer\s+mode|god\s+mode)",
    r"new\s+(persona|personality|role|instructions?)",
    r"system\s*prompt\s*[:=]",
    r"\[INST\]|\[\/INST\]",  # LLaMA instruction tags
    r"<\s*(system|user|assistant)\s*>",  # XML-style injection
    # Data exfiltration attempts
    r"(print|output|show|reveal|display)\s+(your\s+)?(system\s+prompt|instructions?|api\s+key|secret)",
    r"what\s+(are\s+your\s+|is\s+your\s+)?(instructions?|prompt|rules?|constraints?)",
    r"repeat\s+(everything|the\s+above|your\s+system)",
    # Role confusion
    r"you\s+(are\s+not|aren't)\s+(an?\s+)?(AI|assistant|bot|educational)",
    r"your\s+true\s+(self|nature|purpose)",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]


def detect_prompt_injection(text: str) -> bool:
    """
    Returns True if the input contains potential prompt injection patterns.
    Used as a pre-filter before sending to LLM.
    """
    if not text or len(text) > 4000:
        return True  # Reject empty or excessively long messages
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_user_message(text: str) -> str:
    """
    Strip potential control characters and limit message length.
    """
    # Remove null bytes and control characters
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    # Limit length for RAG query safety
    return text[:1000].strip()


# ── Message History Validation ────────────────────────────────────────────────

MAX_MESSAGES = 20
MAX_CONTENT_LENGTH = 4000


def validate_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Validate and sanitize the message history:
    - Limit to last MAX_MESSAGES messages
    - Retain only the client roles allowed by the public request schema
    - Limit content length per message
    """
    # Defense in depth for service-level callers that bypass Pydantic request
    # validation. Provider-priority roles such as system, developer, and tool
    # must never be forwarded from client-controlled history.
    filtered = [m for m in messages if m.get("role") in {"user", "assistant"}]
    
    # Limit message count (keep latest)
    filtered = filtered[-MAX_MESSAGES:]
    
    # Sanitize each message content
    sanitized: list[dict[str, str]] = []
    for msg in filtered:
        if not isinstance(msg.get("content"), str):
            continue
        sanitized.append({
            "role": msg["role"],
            "content": msg["content"][:MAX_CONTENT_LENGTH]
        })
    
    return sanitized


# ── File Upload Security ──────────────────────────────────────────────────────

ALLOWED_CONTENT_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    "pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    },
    "txt": {"text/plain"},
}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


def validate_file_upload(
    filename: str, content_type: str | None, content: bytes
) -> tuple[bool, str]:
    """
    Validate uploaded file:
    1. Check extension whitelist
    2. Check magic bytes (real content type)
    3. Check file size
    Returns (is_valid, error_message)
    """
    # 1. Check for path traversal and ambiguous dot segments.
    safe_name = Path(filename).name
    if not filename or safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        return False, "INVALID_FILENAME"
    
    # 2. Check extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_CONTENT_TYPES:
        return False, "UNSUPPORTED_FILE_TYPE"

    # 3. Reject oversized content before parsing it.
    if len(content) > MAX_FILE_SIZE_BYTES:
        return False, "FILE_TOO_LARGE"

    # 4. MIME must agree with the approved extension.
    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_content_type not in ALLOWED_CONTENT_TYPES[ext]:
        return False, "INVALID_FILE_CONTENT_TYPE"

    # 5. Verify signatures and distinguish Office Open XML containers by entry.
    if ext == "pdf" and not content.startswith(b"%PDF-"):
        return False, "INVALID_FILE_CONTENT"
    if ext in {"docx", "pptx"}:
        required_entry = "word/document.xml" if ext == "docx" else "ppt/presentation.xml"
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
        except (OSError, zipfile.BadZipFile):
            return False, "INVALID_FILE_CONTENT"
        if "[Content_Types].xml" not in names or required_entry not in names:
            return False, "INVALID_FILE_CONTENT"
    if ext == "txt":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return False, "INVALID_FILE_CONTENT"
        if b"\x00" in content:
            return False, "INVALID_FILE_CONTENT"

    return True, ""


# ── Error Sanitization ────────────────────────────────────────────────────────

SENSITIVE_PATTERNS = [
    r"sk-[a-zA-Z0-9\-_]{20,}",   # API keys
    r"postgresql://[^\s]+",        # DB connection strings
    r"password\s*=\s*[^\s]+",     # Passwords in URLs
    r"Bearer\s+[a-zA-Z0-9\-_\.]+", # JWT tokens
]
COMPILED_SENSITIVE = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]


def sanitize_error(error: Exception) -> str:
    """
    Returns a safe error message that does not expose internal details.
    Strips any sensitive data like API keys, connection strings.
    """
    err_str = str(error)
    for pattern in COMPILED_SENSITIVE:
        err_str = pattern.sub("[REDACTED]", err_str)
    
    # Map known exception types to safe messages
    err_lower = err_str.lower()
    if "connection" in err_lower or "database" in err_lower:
        return "AI_SERVICE_UNAVAILABLE"
    if "rate limit" in err_lower or "429" in err_lower:
        return "AI_RATE_LIMIT_EXCEEDED"
    if "timeout" in err_lower:
        return "AI_TIMEOUT"
    if "api" in err_lower and "key" in err_lower:
        return "AI_AUTHENTICATION_FAILED"
    
    return "AI_INTERNAL_ERROR"
