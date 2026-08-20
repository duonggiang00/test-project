"""Rebuild the checked-in demo-standard-v1 JSON and PDF fixture assets.

This authoring utility is not part of the runtime dependency set. Run it with
the workspace document runtime, which provides ReportLab.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
MATERIALS = ROOT / "materials"
DATASET_ID = "demo-standard-v1"
# DATA-DEMO-002: the fixture's minimum compatible revision, not an
# exact pin -- see DemoManifest.minimum_alembic_revision. This is the
# earliest revision at which SINGLE_CHOICE (used by 24 seeded questions)
# existed; every later migration to date is additive and does not
# change the meaning of any column this fixture writes.
MINIMUM_ALEMBIC_REVISION = "a83c1d7e9f02"
NAMESPACE = "playstudy/demo-standard-v1"


def write_json(name: str, value: Any) -> None:
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def question(
    key: str,
    topic: str,
    material: str,
    kind: str,
    difficulty: str,
    content: str,
    *,
    options: list[tuple[str, bool]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "topic": topic,
        "material": material,
        "question_type": kind,
        "difficulty": difficulty,
        "content": content,
        "points": 10,
        "is_ai_generated": False,
        "options": [
            {"content": option_content, "is_correct": is_correct}
            for option_content, is_correct in (options or [])
        ],
        "metadata": metadata or {},
    }


TOPICS = [
    {
        "key": "math",
        "name": "Toán cao cấp",
        "description": "Kiến thức giải tích nền tảng cho sinh viên năm nhất.",
        "parent": None,
    },
    {
        "key": "math-limits",
        "name": "Giới hạn và tính liên tục",
        "description": "Giới hạn hàm số, quy tắc tính giới hạn và tính liên tục.",
        "parent": "math",
    },
    {
        "key": "math-derivatives",
        "name": "Đạo hàm và ứng dụng",
        "description": "Đạo hàm, tiếp tuyến, cực trị và bài toán tối ưu cơ bản.",
        "parent": "math",
    },
    {
        "key": "python",
        "name": "Nhập môn lập trình Python",
        "description": "Tư duy lập trình và cú pháp Python cho người mới bắt đầu.",
        "parent": None,
    },
    {
        "key": "python-foundations",
        "name": "Nền tảng Python",
        "description": "Biến, kiểu dữ liệu, biểu thức và cấu trúc dữ liệu cơ bản.",
        "parent": "python",
    },
    {
        "key": "python-control",
        "name": "Điều khiển luồng và hàm",
        "description": "Rẽ nhánh, vòng lặp, hàm và phạm vi biến trong Python.",
        "parent": "python",
    },
    {
        "key": "english",
        "name": "Tiếng Anh học thuật",
        "description": "Kỹ năng đọc và viết học thuật ở mức nhập môn.",
        "parent": None,
    },
    {
        "key": "english-reading",
        "name": "Chiến lược đọc học thuật",
        "description": "Đọc lướt, đọc tìm thông tin và xác định luận điểm chính.",
        "parent": "english",
    },
    {
        "key": "english-writing",
        "name": "Từ vựng và viết đoạn học thuật",
        "description": "Từ vựng học thuật, câu chủ đề và tính mạch lạc của đoạn văn.",
        "parent": "english",
    },
]


MATERIAL_TEXT = {
    "math_limits.txt": (
        "GIỚI HẠN VÀ TÍNH LIÊN TỤC\n\n"
        "Giới hạn mô tả giá trị mà hàm số tiến gần tới khi biến số tiến gần một điểm. "
        "Ký hiệu lim x->a f(x)=L không yêu cầu f(a) phải bằng L hoặc thậm chí phải xác định.\n\n"
        "Các quy tắc tổng, hiệu, tích và thương cho phép kết hợp các giới hạn đã biết. "
        "Với dạng vô định 0/0, có thể phân tích nhân tử, rút gọn hoặc dùng giới hạn lượng giác cơ bản.\n\n"
        "Hàm f liên tục tại a khi f(a) xác định, lim x->a f(x) tồn tại và giới hạn đó bằng f(a). "
        "Hàm đa thức liên tục trên R; hàm hữu tỉ liên tục tại nơi mẫu khác 0.\n\n"
        "Định lý giá trị trung gian khẳng định rằng hàm liên tục trên đoạn [a,b] nhận mọi giá trị "
        "nằm giữa f(a) và f(b). Đây là công cụ quan trọng để chứng minh phương trình có nghiệm."
    ),
    "math_derivatives.pdf": (
        "ĐẠO HÀM VÀ ỨNG DỤNG\n\n"
        "Đạo hàm f'(x) là giới hạn của tỉ số thay đổi và biểu diễn tốc độ biến thiên tức thời. "
        "Về hình học, f'(a) là hệ số góc của tiếp tuyến tại điểm có hoành độ a.\n\n"
        "Các quy tắc cơ bản gồm đạo hàm tổng, tích, thương và quy tắc dây chuyền. "
        "Ví dụ, đạo hàm của x^n là n*x^(n-1), còn đạo hàm của hàm hợp dùng quy tắc dây chuyền.\n\n"
        "Điểm tới hạn xuất hiện khi f'(x)=0 hoặc đạo hàm không xác định. Dấu của f' cho biết "
        "khoảng đồng biến, nghịch biến và hỗ trợ xác định cực trị địa phương.\n\n"
        "Trong bài toán tối ưu, cần xác định đại lượng mục tiêu, miền khả thi, tìm điểm tới hạn "
        "và so sánh giá trị tại điểm tới hạn với các biên của miền."
    ),
    "python_foundations.txt": (
        "NỀN TẢNG PYTHON\n\n"
        "Python dùng thụt lề để biểu diễn khối lệnh. Biến được tạo khi gán giá trị và tên biến "
        "nên mô tả rõ ý nghĩa. Các kiểu cơ bản gồm int, float, str và bool.\n\n"
        "Toán tử số học xử lý phép tính; toán tử so sánh trả về True hoặc False. Hàm type() "
        "cho biết kiểu hiện tại và các hàm int(), float(), str() hỗ trợ chuyển kiểu có kiểm soát.\n\n"
        "List là dãy có thứ tự và có thể thay đổi; tuple có thứ tự nhưng bất biến; dictionary "
        "lưu cặp khóa-giá trị; set lưu các phần tử không trùng nhau.\n\n"
        "Chỉ số của dãy bắt đầu từ 0. Biểu thức cắt list[start:stop] lấy từ start đến trước stop. "
        "Cần chọn cấu trúc dữ liệu theo thao tác chính thay vì theo thói quen."
    ),
    "python_control.pdf": (
        "ĐIỀU KHIỂN LUỒNG VÀ HÀM TRONG PYTHON\n\n"
        "Câu lệnh if, elif và else chọn nhánh thực thi dựa trên biểu thức Boolean. "
        "Các điều kiện nên ngắn, rõ và tránh lồng quá nhiều mức.\n\n"
        "Vòng lặp for phù hợp khi duyệt iterable; while phù hợp khi lặp đến lúc điều kiện đổi. "
        "break kết thúc vòng lặp, continue bỏ qua phần còn lại của lượt hiện tại.\n\n"
        "Hàm được khai báo bằng def, có thể nhận tham số và trả kết quả bằng return. "
        "Một hàm tốt thực hiện một trách nhiệm, có tên rõ và không phụ thuộc trạng thái toàn cục.\n\n"
        "Biến tạo trong hàm thường có phạm vi cục bộ. Tham số mặc định được đánh giá khi định nghĩa hàm, "
        "vì vậy không nên dùng list hoặc dictionary có thể thay đổi làm giá trị mặc định."
    ),
    "academic_reading.txt": (
        "ACADEMIC READING STRATEGIES\n\n"
        "Skimming means reading quickly to identify the topic, structure, and main claim. Readers often "
        "inspect the title, introduction, topic sentences, and conclusion before reading in detail.\n\n"
        "Scanning means searching for a specific name, date, definition, or result. It is efficient when "
        "the reader already knows what information is needed.\n\n"
        "A main idea states the central point of a paragraph. Supporting details explain, illustrate, or "
        "provide evidence for that point. Signal words reveal contrast, cause, sequence, and conclusion.\n\n"
        "Critical reading also asks who produced the source, what evidence supports the claim, and whether "
        "alternative explanations were considered. Notes should distinguish the author's claim from the reader's response."
    ),
    "academic_writing.pdf": (
        "ACADEMIC VOCABULARY AND PARAGRAPH WRITING\n\n"
        "An academic paragraph normally develops one controlling idea. The topic sentence introduces that idea, "
        "supporting sentences provide evidence or explanation, and the closing sentence reinforces the focus.\n\n"
        "Cohesion comes from accurate reference words, repeated key terms, and logical connectors. However signals "
        "contrast, therefore signals a result, and for example introduces an illustration.\n\n"
        "Academic style favors precise verbs and cautious claims. Writers may use suggests or indicates when evidence "
        "does not justify certainty. Informal expressions should be replaced with clear, discipline-appropriate wording.\n\n"
        "Revision should check unity, coherence, evidence, grammar, and citation. A source must be acknowledged when its "
        "ideas, data, or exact words are used, even when the wording has been paraphrased."
    ),
}


MATERIALS_DATA = [
    {"key": "math-limits-text", "topic": "math-limits", "title": "Giới hạn và tính liên tục - Tóm tắt", "source_file": "math_limits.txt", "file_type": "txt"},
    {"key": "math-derivatives-pdf", "topic": "math-derivatives", "title": "Đạo hàm và ứng dụng - Ghi chú học tập", "source_file": "math_derivatives.pdf", "file_type": "pdf"},
    {"key": "python-foundations-text", "topic": "python-foundations", "title": "Nền tảng Python - Tóm tắt", "source_file": "python_foundations.txt", "file_type": "txt"},
    {"key": "python-control-pdf", "topic": "python-control", "title": "Điều khiển luồng và hàm - Ghi chú học tập", "source_file": "python_control.pdf", "file_type": "pdf"},
    {"key": "english-reading-text", "topic": "english-reading", "title": "Academic Reading Strategies", "source_file": "academic_reading.txt", "file_type": "txt"},
    {"key": "english-writing-pdf", "topic": "english-writing", "title": "Academic Vocabulary and Paragraph Writing", "source_file": "academic_writing.pdf", "file_type": "pdf"},
]


BRIEFS = [
    {"key": "brief-math-limits", "topic": "math-limits", "material": "math-limits-text", "title": "Tóm lược giới hạn và liên tục", "content": "Phân biệt giá trị hàm và giới hạn; áp dụng quy tắc tính giới hạn; kiểm tra ba điều kiện liên tục; dùng định lý giá trị trung gian để chứng minh sự tồn tại nghiệm."},
    {"key": "brief-math-derivatives", "topic": "math-derivatives", "material": "math-derivatives-pdf", "title": "Tóm lược đạo hàm và ứng dụng", "content": "Hiểu đạo hàm như tốc độ biến thiên và hệ số góc; vận dụng các quy tắc đạo hàm; xét dấu đạo hàm để phân tích cực trị; kiểm tra cả điểm tới hạn và biên khi tối ưu."},
    {"key": "brief-python-foundations", "topic": "python-foundations", "material": "python-foundations-text", "title": "Tóm lược nền tảng Python", "content": "Sử dụng kiểu dữ liệu và phép chuyển kiểu đúng mục đích; phân biệt list, tuple, dictionary và set; truy cập dãy bằng chỉ số và lát cắt; đặt tên biến rõ nghĩa."},
    {"key": "brief-python-control", "topic": "python-control", "material": "python-control-pdf", "title": "Tóm lược điều khiển luồng và hàm", "content": "Chọn nhánh bằng if/elif/else; dùng for hoặc while theo điều kiện bài toán; tách trách nhiệm thành hàm; hiểu phạm vi cục bộ và tránh giá trị mặc định có thể thay đổi."},
    {"key": "brief-english-reading", "topic": "english-reading", "material": "english-reading-text", "title": "Academic Reading Strategy Brief", "content": "Use skimming for structure and the main claim, scanning for specific information, topic sentences for main ideas, signal words for relationships, and source evaluation for critical reading."},
    {"key": "brief-english-writing", "topic": "english-writing", "material": "english-writing-pdf", "title": "Academic Paragraph Writing Brief", "content": "Build one controlling idea with a topic sentence, evidence and explanation; use cohesive signals accurately; make cautious claims; revise for unity, coherence, grammar and citation."},
]


QUESTIONS: list[dict[str, Any]] = []


def add_lesson_questions(topic: str, material: str, rows: list[dict[str, Any]]) -> None:
    difficulties = ["EASY", "EASY", "MEDIUM", "MEDIUM", "MEDIUM", "HARD", "EASY", "MEDIUM", "MEDIUM", "HARD"]
    types = ["SINGLE_CHOICE"] * 4 + ["MULTIPLE_CHOICE"] * 2 + ["MATCHING"] * 2 + ["FILL_IN_BLANK"] * 2
    for index, row in enumerate(rows, start=1):
        QUESTIONS.append(
            question(
                f"{topic}-q{index:02d}",
                topic,
                material,
                types[index - 1],
                difficulties[index - 1],
                row["content"],
                options=row.get("options"),
                metadata=row.get("metadata"),
            )
        )


add_lesson_questions("math-limits", "math-limits-text", [
    {"content": "Điều kiện nào không bắt buộc để lim x->a f(x)=L tồn tại?", "options": [("f(a) phải xác định", True), ("Giá trị x tiến gần a", False), ("f(x) tiến gần L", False), ("Giới hạn trái và phải bằng nhau", False)]},
    {"content": "Hàm đa thức liên tục trên tập nào?", "options": [("Toàn bộ R", True), ("Chỉ số dương", False), ("R trừ 0", False), ("Chỉ đoạn hữu hạn", False)]},
    {"content": "Khi tính giới hạn dạng 0/0 của phân thức đại số, thao tác phù hợp đầu tiên là gì?", "options": [("Phân tích nhân tử và rút gọn", True), ("Kết luận giới hạn bằng 0", False), ("Bỏ mẫu số", False), ("Thay x bằng vô cực", False)]},
    {"content": "Hàm f liên tục tại a khi điều kiện nào đúng?", "options": [("lim x->a f(x)=f(a)", True), ("f(a)=0", False), ("f'(a)=0", False), ("a phải dương", False)]},
    {"content": "Chọn tất cả phát biểu đúng về tính liên tục.", "options": [("Đa thức liên tục trên R", True), ("Hàm hữu tỉ liên tục nơi mẫu khác 0", True), ("Mọi hàm đều liên tục tại điểm xác định", False), ("Liên tục tại a đòi hỏi f(a) xác định", True)]},
    {"content": "Chọn các bước có thể xử lý giới hạn đại số dạng 0/0.", "options": [("Phân tích nhân tử", True), ("Rút gọn nhân tử chung", True), ("Thay trực tiếp rồi dừng", False), ("Dùng hằng đẳng thức thích hợp", True)]},
    {"content": "Ghép khái niệm giới hạn với mô tả đúng.", "metadata": {"pairs": [{"left": "Giới hạn hai phía", "right": "Giới hạn trái và phải cùng tồn tại và bằng nhau"}, {"left": "Liên tục tại a", "right": "Giới hạn tại a bằng giá trị hàm tại a"}]}},
    {"content": "Ghép loại hàm với miền liên tục mặc định.", "metadata": {"pairs": [{"left": "Đa thức", "right": "R"}, {"left": "Hàm hữu tỉ", "right": "Nơi mẫu khác 0"}]}},
    {"content": "Điền điều kiện còn thiếu: f liên tục tại a nếu f(a) xác định và lim x->a f(x) bằng ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["f(a)", "giá trị f(a)"]}]}},
    {"content": "Điền tên định lý: Hàm liên tục trên [a,b] nhận mọi giá trị nằm giữa f(a) và f(b) là định lý ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["giá trị trung gian", "intermediate value"]}]}},
])

add_lesson_questions("math-derivatives", "math-derivatives-pdf", [
    {"content": "Ý nghĩa hình học của f'(a) là gì?", "options": [("Hệ số góc tiếp tuyến tại a", True), ("Diện tích dưới đồ thị", False), ("Giá trị lớn nhất của hàm", False), ("Khoảng cách đến gốc tọa độ", False)]},
    {"content": "Đạo hàm của x^n là biểu thức nào?", "options": [("n*x^(n-1)", True), ("x^(n+1)", False), ("n*x^n", False), ("x/n", False)]},
    {"content": "Điểm tới hạn có thể xuất hiện khi nào?", "options": [("f'(x)=0 hoặc f' không xác định", True), ("f(x)=1", False), ("x luôn dương", False), ("f liên tục mọi nơi", False)]},
    {"content": "Trong tối ưu trên đoạn đóng, cần so sánh giá trị tại đâu?", "options": [("Điểm tới hạn và hai đầu mút", True), ("Chỉ điểm giữa", False), ("Chỉ nghiệm f=0", False), ("Mọi số thực", False)]},
    {"content": "Chọn các diễn giải đúng của đạo hàm.", "options": [("Tốc độ biến thiên tức thời", True), ("Hệ số góc tiếp tuyến", True), ("Tổng diện tích", False), ("Giới hạn của tỉ số thay đổi", True)]},
    {"content": "Chọn các bước cần thiết trong một bài toán tối ưu cơ bản.", "options": [("Lập hàm mục tiêu", True), ("Xác định miền khả thi", True), ("Tìm điểm tới hạn", True), ("Bỏ qua giá trị biên", False)]},
    {"content": "Ghép dấu của đạo hàm với tính đơn điệu.", "metadata": {"pairs": [{"left": "f'(x)>0", "right": "Hàm đồng biến"}, {"left": "f'(x)<0", "right": "Hàm nghịch biến"}]}},
    {"content": "Ghép quy tắc đạo hàm với tình huống sử dụng.", "metadata": {"pairs": [{"left": "Quy tắc tích", "right": "Tích của hai hàm"}, {"left": "Quy tắc dây chuyền", "right": "Hàm hợp"}]}},
    {"content": "Điền kết quả: đạo hàm của x^3 là ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["3x^2", "3*x^2"]}]}},
    {"content": "Điền thuật ngữ: nghiệm của f'(x)=0 trong miền xác định là một điểm ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["tới hạn", "critical"]}]}},
])

add_lesson_questions("python-foundations", "python-foundations-text", [
    {"content": "Kiểu dữ liệu nào biểu diễn giá trị đúng hoặc sai trong Python?", "options": [("bool", True), ("str", False), ("float", False), ("list", False)]},
    {"content": "Chỉ số đầu tiên của một list trong Python là bao nhiêu?", "options": [("0", True), ("1", False), ("-2", False), ("Không có chỉ số", False)]},
    {"content": "Cấu trúc nào lưu các cặp khóa-giá trị?", "options": [("dictionary", True), ("tuple", False), ("set", False), ("string", False)]},
    {"content": "Điểm khác biệt cơ bản giữa list và tuple là gì?", "options": [("List có thể thay đổi, tuple bất biến", True), ("Tuple không có thứ tự", False), ("List không có chỉ số", False), ("Tuple chỉ chứa số", False)]},
    {"content": "Chọn các kiểu dữ liệu cơ bản của Python.", "options": [("int", True), ("float", True), ("str", True), ("compile", False)]},
    {"content": "Chọn các phát biểu đúng về cấu trúc dữ liệu Python.", "options": [("Set loại bỏ phần tử trùng", True), ("Dictionary dùng khóa", True), ("Tuple có thể sửa trực tiếp", False), ("List có thứ tự", True)]},
    {"content": "Ghép cấu trúc với đặc điểm.", "metadata": {"pairs": [{"left": "list", "right": "Có thứ tự và có thể thay đổi"}, {"left": "tuple", "right": "Có thứ tự và bất biến"}]}},
    {"content": "Ghép hàm chuyển kiểu với kết quả mong muốn.", "metadata": {"pairs": [{"left": "int('12')", "right": "Số nguyên 12"}, {"left": "str(12)", "right": "Chuỗi '12'"}]}},
    {"content": "Điền kết quả: len([10, 20, 30]) trả về ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["3", "ba"]}]}},
    {"content": "Điền cú pháp lát cắt lấy phần tử chỉ số 1 và 2 của values: values[___].", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["1:3"]}]}},
])

add_lesson_questions("python-control", "python-control-pdf", [
    {"content": "Câu lệnh nào khai báo một hàm trong Python?", "options": [("def", True), ("func", False), ("method", False), ("return", False)]},
    {"content": "Từ khóa nào kết thúc ngay vòng lặp hiện tại?", "options": [("break", True), ("continue", False), ("pass", False), ("yield", False)]},
    {"content": "Vòng lặp nào phù hợp để duyệt từng phần tử của một list?", "options": [("for", True), ("if", False), ("def", False), ("import", False)]},
    {"content": "Biến được tạo bên trong hàm thường có phạm vi nào?", "options": [("Cục bộ", True), ("Toàn hệ thống", False), ("Chỉ đọc", False), ("Không có phạm vi", False)]},
    {"content": "Chọn các thành phần thuộc cấu trúc rẽ nhánh Python.", "options": [("if", True), ("elif", True), ("else", True), ("repeat", False)]},
    {"content": "Chọn các đặc điểm của một hàm được thiết kế tốt.", "options": [("Một trách nhiệm rõ ràng", True), ("Tên mô tả mục đích", True), ("Phụ thuộc nhiều biến toàn cục", False), ("Trả về kết quả khi phù hợp", True)]},
    {"content": "Ghép từ khóa vòng lặp với tác dụng.", "metadata": {"pairs": [{"left": "break", "right": "Kết thúc vòng lặp"}, {"left": "continue", "right": "Chuyển sang lượt lặp tiếp theo"}]}},
    {"content": "Ghép cấu trúc với tình huống phù hợp.", "metadata": {"pairs": [{"left": "for", "right": "Duyệt một iterable"}, {"left": "while", "right": "Lặp đến khi điều kiện thay đổi"}]}},
    {"content": "Điền từ khóa: Hàm gửi kết quả về nơi gọi bằng câu lệnh ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["return"]}]}},
    {"content": "Điền từ khóa: Nhánh được kiểm tra sau if và trước else là ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["elif"]}]}},
])

add_lesson_questions("english-reading", "english-reading-text", [
    {"content": "Which strategy is used to identify a text's overall structure quickly?", "options": [("Skimming", True), ("Scanning", False), ("Copying", False), ("Translating every word", False)]},
    {"content": "Which strategy is best for finding a specific date?", "options": [("Scanning", True), ("Skimming", False), ("Predicting", False), ("Memorizing", False)]},
    {"content": "What usually states the central point of a paragraph?", "options": [("The topic sentence", True), ("A page number", False), ("A citation style", False), ("A footnote marker", False)]},
    {"content": "Which question belongs to critical reading?", "options": [("What evidence supports the claim?", True), ("How many letters are in the title?", False), ("Is every sentence the same length?", False), ("Can I skip the source?", False)]},
    {"content": "Select the elements commonly inspected while skimming.", "options": [("Title", True), ("Topic sentences", True), ("Conclusion", True), ("Every dictionary entry", False)]},
    {"content": "Select the functions of supporting details.", "options": [("Explain the main idea", True), ("Provide evidence", True), ("Illustrate the claim", True), ("Replace the topic completely", False)]},
    {"content": "Match the reading strategy to its purpose.", "metadata": {"pairs": [{"left": "Skimming", "right": "Identify topic and structure"}, {"left": "Scanning", "right": "Locate specific information"}]}},
    {"content": "Match the signal word to its relationship.", "metadata": {"pairs": [{"left": "however", "right": "contrast"}, {"left": "therefore", "right": "result"}]}},
    {"content": "Complete the sentence: The central point of a paragraph is its ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["main idea", "central idea"]}]}},
    {"content": "Complete the sentence: Critical readers evaluate the claim and the supporting ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["evidence"]}]}},
])

add_lesson_questions("english-writing", "english-writing-pdf", [
    {"content": "What is the primary role of a topic sentence?", "options": [("Introduce the paragraph's controlling idea", True), ("List every citation", False), ("End the document", False), ("Define all vocabulary", False)]},
    {"content": "Which connector normally signals contrast?", "options": [("However", True), ("Therefore", False), ("For example", False), ("Similarly", False)]},
    {"content": "Which verb makes a claim appropriately cautious?", "options": [("suggests", True), ("proves forever", False), ("guarantees", False), ("ignores", False)]},
    {"content": "When must a source be acknowledged?", "options": [("When its ideas, data, or words are used", True), ("Only for a long quotation", False), ("Only when the author is famous", False), ("Never after paraphrasing", False)]},
    {"content": "Select the parts of a focused academic paragraph.", "options": [("Topic sentence", True), ("Supporting evidence", True), ("Explanation", True), ("Unrelated anecdote", False)]},
    {"content": "Select qualities to check during revision.", "options": [("Unity", True), ("Coherence", True), ("Grammar", True), ("Random topic changes", False)]},
    {"content": "Match the connector to its function.", "metadata": {"pairs": [{"left": "therefore", "right": "result"}, {"left": "for example", "right": "illustration"}]}},
    {"content": "Match the paragraph element to its role.", "metadata": {"pairs": [{"left": "Topic sentence", "right": "Introduces the controlling idea"}, {"left": "Supporting sentence", "right": "Develops evidence or explanation"}]}},
    {"content": "Complete the sentence: A paragraph with one controlling idea has ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["unity"]}]}},
    {"content": "Complete the sentence: Logical connections between sentences create ___.", "metadata": {"blanks": [{"blank_index": 0, "acceptable_answers": ["coherence", "cohesion"]}]}},
])


EXAMS: list[dict[str, Any]] = []
for subject, lesson_a, lesson_b, title in [
    ("math", "math-limits", "math-derivatives", "Toán cao cấp"),
    ("python", "python-foundations", "python-control", "Nhập môn lập trình Python"),
    ("english", "english-reading", "english-writing", "Academic English"),
]:
    EXAMS.append({
        "key": f"{subject}-published",
        "topic": subject,
        "title": f"Bài đánh giá {title}",
        "description": "Đề tổng hợp đã công bố cho dữ liệu demo.",
        "duration_minutes": 45,
        "is_published": True,
        "questions": [
            *[f"{lesson_a}-q{i:02d}" for i in range(5, 10)],
            *[f"{lesson_b}-q{i:02d}" for i in range(5, 10)],
        ],
    })
    EXAMS.append({
        "key": f"{subject}-draft",
        "topic": subject,
        "title": f"Bản nháp {title}",
        "description": "Đề đang biên soạn, chưa công bố cho sinh viên.",
        "duration_minutes": 30,
        "is_published": False,
        "questions": [
            f"{lesson_a}-q01", f"{lesson_a}-q02",
            f"{lesson_b}-q03", f"{lesson_b}-q04", f"{lesson_b}-q10",
        ],
    })


FLASHCARD_CONTENT = {
    "math-limits": [
        ("Giới hạn tại a", "Giá trị mà f(x) tiến gần khi x tiến gần a."),
        ("Giới hạn hai phía", "Tồn tại khi giới hạn trái và phải tồn tại và bằng nhau."),
        ("Liên tục tại a", "f(a) xác định và lim x->a f(x)=f(a)."),
        ("Hàm đa thức", "Liên tục trên toàn bộ tập số thực."),
        ("Hàm hữu tỉ", "Liên tục tại mọi điểm có mẫu khác 0."),
        ("Dạng 0/0", "Một dạng vô định, cần biến đổi thêm trước khi kết luận."),
        ("Định lý giá trị trung gian", "Hàm liên tục trên đoạn nhận mọi giá trị giữa hai giá trị đầu mút."),
        ("Rút gọn giới hạn", "Phân tích nhân tử rồi loại nhân tử chung khi hợp lệ."),
    ],
    "math-derivatives": [
        ("Đạo hàm", "Tốc độ biến thiên tức thời của hàm số."),
        ("Ý nghĩa hình học", "Hệ số góc của tiếp tuyến với đồ thị."),
        ("Đạo hàm x^n", "n*x^(n-1)."),
        ("Quy tắc dây chuyền", "Dùng để đạo hàm hàm hợp."),
        ("Điểm tới hạn", "Điểm f'=0 hoặc f' không xác định trong miền."),
        ("f'>0", "Hàm đồng biến trên khoảng đang xét."),
        ("f'<0", "Hàm nghịch biến trên khoảng đang xét."),
        ("Tối ưu trên đoạn", "So sánh giá trị tại điểm tới hạn và hai đầu mút."),
    ],
    "python-foundations": [
        ("int", "Kiểu số nguyên."), ("float", "Kiểu số thực dấu phẩy động."),
        ("str", "Kiểu chuỗi văn bản."), ("bool", "Kiểu logic True hoặc False."),
        ("list", "Dãy có thứ tự và có thể thay đổi."), ("tuple", "Dãy có thứ tự và bất biến."),
        ("dictionary", "Cấu trúc cặp khóa-giá trị."), ("set", "Tập phần tử không trùng nhau."),
    ],
    "python-control": [
        ("if", "Bắt đầu cấu trúc rẽ nhánh."), ("elif", "Kiểm tra điều kiện bổ sung."),
        ("else", "Nhánh khi các điều kiện trước đều sai."), ("for", "Duyệt phần tử của iterable."),
        ("while", "Lặp trong khi điều kiện còn đúng."), ("break", "Kết thúc vòng lặp."),
        ("continue", "Bỏ qua phần còn lại của lượt hiện tại."), ("return", "Trả kết quả từ hàm."),
    ],
    "english-reading": [
        ("Skimming", "Reading quickly for topic, structure, and main claim."),
        ("Scanning", "Searching for a specific detail."),
        ("Main idea", "The central point developed in a paragraph."),
        ("Supporting detail", "Evidence, explanation, or illustration of the main idea."),
        ("However", "A signal of contrast."), ("Therefore", "A signal of result."),
        ("Source evaluation", "Checking author, evidence, purpose, and alternatives."),
        ("Critical note", "Separates the author's claim from the reader's response."),
    ],
    "english-writing": [
        ("Topic sentence", "Introduces the controlling idea."),
        ("Supporting sentence", "Develops evidence or explanation."),
        ("Unity", "All sentences support one controlling idea."),
        ("Coherence", "Ideas follow a clear logical order."),
        ("Cohesion", "Language links sentences and references clearly."),
        ("Cautious claim", "Uses wording such as suggests or indicates."),
        ("Paraphrase", "Restates a source idea in new wording and still requires citation."),
        ("Revision", "Checks focus, evidence, organization, grammar, and citation."),
    ],
}


FLASHCARDS: list[dict[str, Any]] = []
for topic, cards in FLASHCARD_CONTENT.items():
    material = next(item["key"] for item in MATERIALS_DATA if item["topic"] == topic)
    FLASHCARDS.append({
        "key": f"deck-{topic}",
        "topic": topic,
        "material": material,
        "title": f"Flashcards - {next(item['name'] for item in TOPICS if item['key'] == topic)}",
        "description": "Bộ thẻ ôn tập do giáo viên biên soạn.",
        "cards": [
            {"key": f"card-{topic}-{index:02d}", "front": front, "back": back, "order_index": index}
            for index, (front, back) in enumerate(cards, start=1)
        ],
    })


STUDENTS = [
    {"key": "student-primary", "email": "student@example.com", "full_name": "Demo Student", "interactive": True},
    {"key": "student-analytics-01", "email": "analytics.student01@example.invalid", "full_name": "Nguyễn Minh Anh", "interactive": False},
    {"key": "student-analytics-02", "email": "analytics.student02@example.invalid", "full_name": "Trần Gia Bảo", "interactive": False},
    {"key": "student-analytics-03", "email": "analytics.student03@example.invalid", "full_name": "Lê Hoàng Chi", "interactive": False},
    {"key": "student-analytics-04", "email": "analytics.student04@example.invalid", "full_name": "Phạm Đức Duy", "interactive": False},
    {"key": "student-analytics-05", "email": "analytics.student05@example.invalid", "full_name": "Vũ Khánh Linh", "interactive": False},
]


SUBMISSIONS: list[dict[str, Any]] = []
submitted_profiles = [
    ("student-primary", 10),
    ("student-analytics-01", 8),
    ("student-analytics-02", 6),
    ("student-analytics-03", 3),
]
for exam_index, subject in enumerate(("math", "python", "english")):
    for student_key, correct_count in submitted_profiles:
        SUBMISSIONS.append({
            "key": f"submission-{subject}-{student_key}",
            "exam": f"{subject}-published",
            "student": student_key,
            "status": "submitted",
            "correct_count": max(0, min(10, correct_count - exam_index % 2)),
        })
    SUBMISSIONS.append({
        "key": f"submission-{subject}-in-progress",
        "exam": f"{subject}-published",
        "student": "student-analytics-04",
        "status": "in_progress",
        "correct_count": 0,
    })


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if not regular.is_file() or not bold.is_file():
        raise RuntimeError("Required Arial fonts are unavailable")
    pdfmetrics.registerFont(TTFont("FixtureArial", regular))
    pdfmetrics.registerFont(TTFont("FixtureArialBold", bold))
    return "FixtureArial", "FixtureArialBold"


def build_pdf(path: Path, title: str, text: str) -> None:
    regular, bold = register_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FixtureTitle",
        parent=styles["Title"],
        fontName=bold,
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    )
    body_style = ParagraphStyle(
        "FixtureBody",
        parent=styles["BodyText"],
        fontName=regular,
        fontSize=11,
        leading=16,
        spaceAfter=4 * mm,
    )
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="PlayStudy demo dataset",
    )
    blocks = [part.strip() for part in text.split("\n\n") if part.strip()]
    story = [Paragraph(blocks[0], title_style)]
    for block in blocks[1:]:
        story.extend((Paragraph(block, body_style), Spacer(1, 1 * mm)))
    document.build(story)


def content_hash(file_names: list[str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(file_names):
        path = ROOT / name
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> None:
    MATERIALS.mkdir(parents=True, exist_ok=True)
    for filename, text in MATERIAL_TEXT.items():
        output = MATERIALS / filename
        if output.suffix == ".pdf":
            title = text.split("\n\n", maxsplit=1)[0]
            build_pdf(output, title, text)
        else:
            output.write_text(text + "\n", encoding="utf-8")

    write_json("topics.json", TOPICS)
    write_json("materials.json", MATERIALS_DATA)
    write_json("briefs.json", BRIEFS)
    write_json("questions.json", QUESTIONS)
    write_json("exams.json", EXAMS)
    write_json("flashcards.json", FLASHCARDS)
    write_json("students.json", STUDENTS)
    write_json("submissions.json", SUBMISSIONS)

    fixture_files = [
        "topics.json", "materials.json", "briefs.json", "questions.json",
        "exams.json", "flashcards.json", "students.json", "submissions.json",
        *[f"materials/{name}" for name in sorted(MATERIAL_TEXT)],
    ]
    manifest = {
        "dataset_id": DATASET_ID,
        "version": 1,
        "minimum_alembic_revision": MINIMUM_ALEMBIC_REVISION,
        "namespace": NAMESPACE,
        "teacher_email": "teacher@example.com",
        "interactive_student_email": "student@example.com",
        "files": {
            "topics": "topics.json",
            "materials": "materials.json",
            "briefs": "briefs.json",
            "questions": "questions.json",
            "exams": "exams.json",
            "flashcards": "flashcards.json",
            "students": "students.json",
            "submissions": "submissions.json",
        },
        "material_directory": "materials",
        "content_files": fixture_files,
        "content_sha256": content_hash(fixture_files),
        "expected_counts": {
            "users": 6,
            "topics": 9,
            "materials": 6,
            "document_chunks": 6,
            "topic_briefs": 6,
            "questions": 60,
            "options": 144,
            "flashcard_decks": 6,
            "flashcards": 48,
            "exams": 6,
            "submissions": 15,
            "submission_answers": 120,
            "flashcard_progress": 24,
        },
    }
    write_json("manifest.json", manifest)


if __name__ == "__main__":
    main()
