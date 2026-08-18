"""Prompt for `MaterialService.generate_questions`.

Extracted verbatim from `material_service.py`.
"""
from __future__ import annotations

PROMPT_ID = "question_generation"
PROMPT_VERSION = 1


def render(*, context_text: str, count: int, question_types: str, difficulty: str) -> str:
    return f"""Bạn là AI chuyên sinh câu hỏi giáo dục chất lượng cao bằng Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới để sinh câu hỏi. KHÔNG bịa đặt.

TÀI LIỆU:
{context_text}

Sinh {count} câu hỏi phân bổ trong các loại sau: {question_types}. Độ khó mong muốn: {difficulty}.
Với mỗi câu hỏi PHẢI bao gồm 'difficulty' (EASY, MEDIUM, hoặc HARD), 'source_reference' (trích dẫn đoạn nào của tài liệu) và 'explanation' (giải thích).

TRẢ VỀ DUY NHẤT MỘT JSON ARRAY HỢP LỆ (KHÔNG có text xung quanh), định dạng như sau:
[
  {{
    "type": "SINGLE_CHOICE",
    "difficulty": "MEDIUM",
    "content": "Câu hỏi 1 đáp án...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [
      {{"content": "A", "is_correct": true}},
      {{"content": "B", "is_correct": false}}
    ]
  }},
  {{
    "type": "MATCHING",
    "difficulty": "HARD",
    "content": "Ghép nối...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [],
    "metadata_json": {{"pairs": [{{"left": "Vế 1", "right": "Vế 2"}}]}}
  }},
  {{
    "type": "FILL_IN_BLANK",
    "difficulty": "EASY",
    "content": "Điền khuyết...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [],
    "metadata_json": {{"blanks": [{{"blank_index": 0, "acceptable_answers": ["đáp án 1", "đáp án 2"]}}]}}
  }}
]
"""
