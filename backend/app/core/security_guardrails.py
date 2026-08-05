"""
Security Guardrail Module for AI Chatbot.
Handles: Prompt Injection detection, Message validation, Error sanitization.
"""
import re
from typing import List, Dict, Any

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


def validate_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and sanitize the message history:
    - Limit to last MAX_MESSAGES messages
    - Strip any system-role messages injected by the client
    - Limit content length per message
    """
    # Strip any system messages the client tries to inject
    filtered = [m for m in messages if m.get("role") != "system"]
    
    # Limit message count (keep latest)
    filtered = filtered[-MAX_MESSAGES:]
    
    # Sanitize each message content
    sanitized = []
    for msg in filtered:
        if not isinstance(msg.get("content"), str):
            continue
        sanitized.append({
            "role": msg["role"],
            "content": msg["content"][:MAX_CONTENT_LENGTH]
        })
    
    return sanitized


# ── File Upload Security ──────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx"}
ALLOWED_MAGIC_BYTES = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",  # ZIP-based format
}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


def validate_file_upload(filename: str, content: bytes) -> tuple[bool, str]:
    """
    Validate uploaded file:
    1. Check extension whitelist
    2. Check magic bytes (real content type)
    3. Check file size
    Returns (is_valid, error_message)
    """
    # 1. Check for path traversal
    import os
    safe_name = os.path.basename(filename)
    if safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        return False, "INVALID_FILENAME"
    
    # 2. Check extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, "UNSUPPORTED_FILE_TYPE"
    
    # 3. Check magic bytes for known types
    if ext == "pdf" and not content[:4].startswith(b"%PDF"):
        return False, "INVALID_FILE_CONTENT"
    
    # 4. Check size
    if len(content) > MAX_FILE_SIZE_BYTES:
        return False, "FILE_TOO_LARGE"
    
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
