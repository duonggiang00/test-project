"""
Idempotent seed script: inserts Topic, Exams, Questions, and Options.
Run from D:/projects/test-project/backend:
    python seed_detailed_data.py
"""

import sys
import os

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(__file__))

# Import ALL models so SQLAlchemy mapper can resolve all relationships
from app.db.session import SessionLocal
from app.models.topic import Topic
from app.models.exam import Exam, Question, Option
from app.models.enums import QuestionType, DifficultyLevel
from app.models.user import User
from app.models.material import StudyMaterial  # noqa: F401 — required to resolve mapper
from app.models.submission import Submission, SubmissionAnswer  # noqa: F401

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_mc_question(content: str, options: list[tuple[str, bool]], exam_id, topic_id) -> Question:
    """MULTIPLE_CHOICE question (single or multi correct)."""
    q = Question(
        exam_id=exam_id,
        topic_id=topic_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        difficulty=DifficultyLevel.MEDIUM,
        content=content,
    )
    q.options = [Option(content=c, is_correct=correct) for c, correct in options]
    return q


def make_matching_question(content: str, pairs: list[dict], exam_id, topic_id) -> Question:
    """MATCHING question."""
    q = Question(
        exam_id=exam_id,
        topic_id=topic_id,
        question_type=QuestionType.MATCHING,
        difficulty=DifficultyLevel.MEDIUM,
        content=content,
        metadata_json={"pairs": pairs},
    )
    # Each left-side item becomes an Option with is_correct=True
    q.options = [Option(content=p["left"], is_correct=True) for p in pairs]
    return q


def make_fill_question(content: str, blanks: list[str], answer: str, exam_id, topic_id) -> Question:
    """FILL_IN_BLANK question."""
    q = Question(
        exam_id=exam_id,
        topic_id=topic_id,
        question_type=QuestionType.FILL_IN_BLANK,
        difficulty=DifficultyLevel.MEDIUM,
        content=content,
        metadata_json={"blanks": blanks},
    )
    q.options = [Option(content=answer, is_correct=True)]
    return q


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed() -> None:
    db = SessionLocal()
    try:
        # ------------------------------------------------------------------ #
        # Idempotency check                                                    #
        # ------------------------------------------------------------------ #
        existing_topic = db.query(Topic).filter_by(name="Lập trình & Cơ sở dữ liệu").first()
        if existing_topic:
            print("[OK] Seed data already exists -- skipping.")
            return

        # ------------------------------------------------------------------ #
        # Admin user                                                           #
        # ------------------------------------------------------------------ #
        admin = db.query(User).filter_by(email="admin@example.com").first()
        if not admin:
            print("[ERROR] admin@example.com not found. Please create the admin user first.")
            sys.exit(1)

        admin_id = admin.id
        print(f"[OK] Found admin user: {admin.email} ({admin_id})")

        # ------------------------------------------------------------------ #
        # Topic                                                                #
        # ------------------------------------------------------------------ #
        topic = Topic(
            name="Lập trình & Cơ sở dữ liệu",
            description="Bao gồm các kiến thức từ Python cơ bản đến SQL và cơ sở dữ liệu quan hệ.",
        )
        db.add(topic)
        db.flush()  # get topic.id
        print(f"[OK] Created topic: {topic.name} ({topic.id})")

        # ------------------------------------------------------------------ #
        # Exam 1                                                               #
        # ------------------------------------------------------------------ #
        exam1 = Exam(
            creator_id=admin_id,
            topic_id=topic.id,
            title="Bài thi giữa kỳ: Nhập môn Lập trình",
            duration_minutes=45,
            is_published=True,
        )
        db.add(exam1)
        db.flush()
        print(f"[OK] Created exam 1: {exam1.title} ({exam1.id})")

        e1 = exam1.id
        t = topic.id

        questions_exam1: list[Question] = []

        # --- Single Choice (5) ---
        questions_exam1.append(make_mc_question(
            "Ngôn ngữ lập trình nào sau đây là ngôn ngữ thông dịch?",
            [("Python", True), ("C++", False), ("Java", False), ("Assembly", False)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Kiểu dữ liệu nào lưu trữ giá trị True/False trong Python?",
            [("int", False), ("float", False), ("bool", True), ("str", False)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Vòng lặp nào dùng khi không biết trước số lần lặp?",
            [("for", False), ("while", True), ("do-while", False), ("foreach", False)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Hàm nào dùng để in ra màn hình trong Python?",
            [("print()", True), ("echo()", False), ("console.log()", False), ("printf()", False)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Toán tử nào dùng để kiểm tra bằng nhau trong Python?",
            [("=", False), ("==", True), (":=", False), ("!=", False)],
            e1, t,
        ))

        # --- Multiple Choice (5) ---
        questions_exam1.append(make_mc_question(
            "Các kiểu dữ liệu nguyên thủy trong Python bao gồm?",
            [("int", True), ("float", True), ("list", False), ("bool", True)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Đặc điểm của hàm (function) trong Python?",
            [("Có thể có tham số", True), ("Luôn phải return", False), ("Dùng từ khóa def", True), ("Tái sử dụng code", True)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Cấu trúc điều kiện trong Python bao gồm?",
            [("if", True), ("elif", True), ("else", True), ("when", False)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Python hỗ trợ các kiểu collection nào?",
            [("list", True), ("dict", True), ("tuple", True), ("array", False)],
            e1, t,
        ))
        questions_exam1.append(make_mc_question(
            "Tính chất của OOP bao gồm?",
            [("Kế thừa", True), ("Đóng gói", True), ("Đa hình", True), ("Biên dịch", False)],
            e1, t,
        ))

        # --- Matching (5) ---
        questions_exam1.append(make_matching_question(
            "Nối khái niệm Python với mô tả tương ứng",
            [
                {"left": "list", "right": "Danh sách có thứ tự, có thể thay đổi"},
                {"left": "tuple", "right": "Danh sách có thứ tự, không thể thay đổi"},
                {"left": "dict", "right": "Cặp key-value"},
                {"left": "set", "right": "Tập hợp không trùng lặp"},
            ],
            e1, t,
        ))
        questions_exam1.append(make_matching_question(
            "Nối toán tử với chức năng",
            [
                {"left": "+", "right": "Cộng"},
                {"left": "**", "right": "Lũy thừa"},
                {"left": "//", "right": "Chia lấy phần nguyên"},
                {"left": "%", "right": "Chia lấy dư"},
            ],
            e1, t,
        ))
        questions_exam1.append(make_matching_question(
            "Nối từ khóa với ý nghĩa",
            [
                {"left": "break", "right": "Thoát khỏi vòng lặp"},
                {"left": "continue", "right": "Bỏ qua lần lặp hiện tại"},
                {"left": "pass", "right": "Không làm gì"},
                {"left": "return", "right": "Trả về giá trị"},
            ],
            e1, t,
        ))
        questions_exam1.append(make_matching_question(
            "Nối lỗi với nguyên nhân",
            [
                {"left": "SyntaxError", "right": "Lỗi cú pháp"},
                {"left": "TypeError", "right": "Lỗi kiểu dữ liệu"},
                {"left": "IndexError", "right": "Chỉ số ngoài phạm vi"},
                {"left": "KeyError", "right": "Khóa không tồn tại"},
            ],
            e1, t,
        ))
        questions_exam1.append(make_matching_question(
            "Nối phương thức với list",
            [
                {"left": "append()", "right": "Thêm phần tử vào cuối"},
                {"left": "pop()", "right": "Xóa phần tử cuối"},
                {"left": "sort()", "right": "Sắp xếp"},
                {"left": "len()", "right": "Độ dài danh sách"},
            ],
            e1, t,
        ))

        # --- Fill in the Blank (5) ---
        questions_exam1.append(make_fill_question(
            "Để khai báo hàm trong Python, ta dùng từ khóa [...]",
            ["def"], "def", e1, t,
        ))
        questions_exam1.append(make_fill_question(
            "Câu lệnh [...] dùng để thoát khỏi vòng lặp",
            ["break"], "break", e1, t,
        ))
        questions_exam1.append(make_fill_question(
            "Trong Python, [...] là kiểu dữ liệu dùng lưu chuỗi ký tự",
            ["str"], "str", e1, t,
        ))
        questions_exam1.append(make_fill_question(
            "Hàm [...] trả về độ dài của một danh sách",
            ["len"], "len", e1, t,
        ))
        questions_exam1.append(make_fill_question(
            "Từ khóa [...] dùng để tạo một lớp trong Python",
            ["class"], "class", e1, t,
        ))

        for q in questions_exam1:
            db.add(q)

        print(f"[OK] Added {len(questions_exam1)} questions to Exam 1")

        # ------------------------------------------------------------------ #
        # Exam 2                                                               #
        # ------------------------------------------------------------------ #
        exam2 = Exam(
            creator_id=admin_id,
            topic_id=topic.id,
            title="Bài thi cuối kỳ: Cấu trúc dữ liệu & Giải thuật",
            duration_minutes=90,
            is_published=True,
        )
        db.add(exam2)
        db.flush()
        print(f"[OK] Created exam 2: {exam2.title} ({exam2.id})")

        e2 = exam2.id

        questions_exam2: list[Question] = []

        # --- Single Choice (5) ---
        questions_exam2.append(make_mc_question(
            "Cấu trúc dữ liệu nào hoạt động theo nguyên tắc LIFO?",
            [("Queue", False), ("Stack", True), ("Array", False), ("LinkedList", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Độ phức tạp của thuật toán Binary Search?",
            [("O(n)", False), ("O(n²)", False), ("O(log n)", True), ("O(1)", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Cấu trúc dữ liệu nào dùng để cài đặt BFS?",
            [("Stack", False), ("Queue", True), ("Tree", False), ("Graph", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Thuật toán sắp xếp nào có độ phức tạp tốt nhất trường hợp O(n)?",
            [("Quick Sort", False), ("Merge Sort", False), ("Bubble Sort", True), ("Selection Sort", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Trong Binary Tree, nút không có con gọi là?",
            [("Root", False), ("Parent", False), ("Leaf", True), ("Branch", False)],
            e2, t,
        ))

        # --- Multiple Choice (5) ---
        questions_exam2.append(make_mc_question(
            "Các thuật toán sắp xếp có độ phức tạp O(n log n)?",
            [("Merge Sort", True), ("Quick Sort", True), ("Heap Sort", True), ("Bubble Sort", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Đặc điểm của Stack là?",
            [("LIFO", True), ("Push thêm phần tử", True), ("Pop lấy phần tử", True), ("FIFO", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Ứng dụng của Queue bao gồm?",
            [("BFS", True), ("Lịch CPU", True), ("Undo/Redo", False), ("In hàng đợi", True)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Cây nhị phân tìm kiếm (BST) có tính chất?",
            [("Nút trái < Nút gốc", True), ("Nút phải > Nút gốc", True), ("Mọi nút có đúng 2 con", False), ("Cân bằng tự động", False)],
            e2, t,
        ))
        questions_exam2.append(make_mc_question(
            "Big O notation dùng để?",
            [("Đo hiệu suất thuật toán", True), ("So sánh thuật toán", True), ("Tính bộ nhớ", True), ("Debug code", False)],
            e2, t,
        ))

        # --- Matching (5) ---
        questions_exam2.append(make_matching_question(
            "Nối cấu trúc dữ liệu với đặc điểm",
            [
                {"left": "Stack", "right": "LIFO"},
                {"left": "Queue", "right": "FIFO"},
                {"left": "Tree", "right": "Phân cấp"},
                {"left": "Graph", "right": "Đỉnh và cạnh"},
            ],
            e2, t,
        ))
        questions_exam2.append(make_matching_question(
            "Nối thuật toán với độ phức tạp trung bình",
            [
                {"left": "Bubble Sort", "right": "O(n²)"},
                {"left": "Merge Sort", "right": "O(n log n)"},
                {"left": "Binary Search", "right": "O(log n)"},
                {"left": "Linear Search", "right": "O(n)"},
            ],
            e2, t,
        ))
        questions_exam2.append(make_matching_question(
            "Nối thuật toán đồ thị với ứng dụng",
            [
                {"left": "DFS", "right": "Tìm đường trong mê cung"},
                {"left": "BFS", "right": "Tìm đường ngắn nhất"},
                {"left": "Dijkstra", "right": "Đường đi ngắn nhất có trọng số"},
                {"left": "Floyd", "right": "Đường đi ngắn nhất mọi cặp đỉnh"},
            ],
            e2, t,
        ))
        questions_exam2.append(make_matching_question(
            "Nối thao tác với cấu trúc Stack",
            [
                {"left": "push", "right": "Thêm vào đỉnh"},
                {"left": "pop", "right": "Lấy từ đỉnh"},
                {"left": "peek", "right": "Xem phần tử đỉnh"},
                {"left": "isEmpty", "right": "Kiểm tra rỗng"},
            ],
            e2, t,
        ))
        questions_exam2.append(make_matching_question(
            "Nối kiểu duyệt cây với thứ tự",
            [
                {"left": "Inorder", "right": "Trái - Gốc - Phải"},
                {"left": "Preorder", "right": "Gốc - Trái - Phải"},
                {"left": "Postorder", "right": "Trái - Phải - Gốc"},
                {"left": "BFS", "right": "Theo tầng"},
            ],
            e2, t,
        ))

        # --- Fill in the Blank (5) ---
        questions_exam2.append(make_fill_question(
            "Cấu trúc dữ liệu [...] hoạt động theo nguyên tắc LIFO",
            ["Stack"], "Stack", e2, t,
        ))
        questions_exam2.append(make_fill_question(
            "Thuật toán [...] sử dụng Queue để duyệt đồ thị theo chiều rộng",
            ["BFS"], "BFS", e2, t,
        ))
        questions_exam2.append(make_fill_question(
            "Độ phức tạp của Binary Search là O([...])",
            ["log n"], "log n", e2, t,
        ))
        questions_exam2.append(make_fill_question(
            "Nút gốc của cây (Tree) được gọi là [...]",
            ["Root"], "Root", e2, t,
        ))
        questions_exam2.append(make_fill_question(
            "Thuật toán [...] chia mảng làm đôi và gộp lại sau khi sắp xếp",
            ["Merge Sort"], "Merge Sort", e2, t,
        ))

        for q in questions_exam2:
            db.add(q)

        print(f"[OK] Added {len(questions_exam2)} questions to Exam 2")

        # ------------------------------------------------------------------ #
        # Commit                                                               #
        # ------------------------------------------------------------------ #
        db.commit()
        print("\n[DONE] Seed completed successfully!")
        print(f"   Topic   : {topic.name}")
        print(f"   Exam 1  : {exam1.title} - {len(questions_exam1)} questions")
        print(f"   Exam 2  : {exam2.title} - {len(questions_exam2)} questions")
        print(f"   Total Q : {len(questions_exam1) + len(questions_exam2)}")

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Error during seeding: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(
        "Deprecated unsafe seed entry point. Use "
        "'uv run --frozen python -m scripts.seed_demo_data plan' first."
    )
