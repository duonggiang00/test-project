"""Prompt for `MaterialService.generate_topic_brief`.

Extracted verbatim from `material_service.py`.
"""
from __future__ import annotations

PROMPT_ID = "topic_brief_generation"
PROMPT_VERSION = 1


def render(*, context_text: str) -> str:
    return f"""Bạn là AI chuyên tóm tắt tài liệu giáo dục thành Topic Brief (Dàn ý chủ đề) bằng Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới.

TÀI LIỆU:
{context_text}

Sinh bản tóm tắt topic brief dưới dạng JSON THUẦN TÚY (không markdown).
{{
  "content": "Nội dung tóm tắt định dạng markdown..."
}}
"""
