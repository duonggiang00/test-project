"""Prompt for `MaterialService.generate_flashcards`.

Extracted verbatim from `material_service.py`.
"""
from __future__ import annotations

PROMPT_ID = "flashcard_generation"
PROMPT_VERSION = 1


def render(*, context_text: str, count: int) -> str:
    return f"""Bạn là AI chuyên tóm tắt tài liệu giáo dục thành thẻ ghi nhớ (flashcard) Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới.

TÀI LIỆU:
{context_text}

Sinh {count} cặp flashcard dưới dạng JSON THUẦN TÚY (không markdown).
Với mỗi flashcard PHẢI bao gồm 'source_reference' (trích dẫn đoạn nào của tài liệu) và 'explanation' (giải thích thêm hoặc ví dụ mở rộng).
{{
  "flashcards": [
    {{
      "term": "Thuật ngữ hoặc khái niệm",
      "definition": "Định nghĩa hoặc giải thích chi tiết",
      "source_reference": "Trích đoạn từ tài liệu",
      "explanation": "Giải thích thêm ngữ cảnh hoặc ví dụ"
    }},
    ...
  ]
}}
"""
