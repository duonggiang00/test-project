"""Prompt for `MaterialService.generate_questions`.

Extracted verbatim from `material_service.py`.
"""
from __future__ import annotations

PROMPT_ID = "question_generation"
PROMPT_VERSION = 3


def render(*, context_text: str, count: int, question_types: str, difficulty: str) -> str:
    return f"""Bạn là AI chuyên sinh câu hỏi giáo dục chất lượng cao bằng Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới để sinh câu hỏi. KHÔNG bịa đặt.

TÀI LIỆU:
{context_text}

Sinh {count} câu hỏi phân bổ trong các loại sau: {question_types}. Độ khó mong muốn: {difficulty}.
Với mỗi câu hỏi PHẢI bao gồm 'difficulty' (EASY, MEDIUM, hoặc HARD), 'source_reference' (trích dẫn đoạn nào của tài liệu) và 'explanation' (giải thích).
Với câu hỏi loại SINGLE_CHOICE và MULTIPLE_CHOICE, PHẢI sinh đúng 4 đáp án (options) cho mỗi câu — không được ít hơn hoặc nhiều hơn 4.
Với câu hỏi loại FILL_IN_BLANK, nội dung PHẢI chứa chính xác token `[BLANK]` tại mỗi vị trí người học cần nhập; không dùng dấu gạch dưới thay thế.

TRẢ VỀ DUY NHẤT MỘT JSON ARRAY HỢP LỆ (KHÔNG có text xung quanh), định dạng như sau:
[
  {{
    "type": "SINGLE_CHOICE",
    "difficulty": "MEDIUM",
    "content": "Câu hỏi 1 đáp án đúng...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [
      {{"content": "A", "is_correct": true}},
      {{"content": "B", "is_correct": false}},
      {{"content": "C", "is_correct": false}},
      {{"content": "D", "is_correct": false}}
    ]
  }},
  {{
    "type": "MULTIPLE_CHOICE",
    "difficulty": "MEDIUM",
    "content": "Câu hỏi nhiều đáp án đúng...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [
      {{"content": "A", "is_correct": true}},
      {{"content": "B", "is_correct": true}},
      {{"content": "C", "is_correct": false}},
      {{"content": "D", "is_correct": false}}
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
    "content": "Điền khuyết: nội dung cần điền là [BLANK].",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [],
    "metadata_json": {{"blanks": [{{"blank_index": 0, "acceptable_answers": ["đáp án 1", "đáp án 2"]}}]}}
  }}
]
"""
