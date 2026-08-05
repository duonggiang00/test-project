# **Task Breakdown Structure (WBS)**

**Dự án:** Hệ thống Thi Trắc nghiệm Trực tuyến tích hợp AI

**Thời gian dự kiến:** 4 Tuần (Đồ án cá nhân)

**Công cụ quản lý khuyến nghị:** Trello, Jira, hoặc Github Projects.

## **Tuần 1: Khởi tạo, Cơ sở dữ liệu & Xác thực (Foundation & Auth)**

**Mục tiêu:** Xây dựng xong bộ khung backend, kết nối Database, và hoàn thiện luồng đăng nhập/đăng ký.

* \[ \] **Task 1.1: Thiết lập Project Backend (FastAPI)**  
  * Khởi tạo môi trường ảo (Virtual Environment).  
  * Cài đặt thư viện: fastapi, uvicorn, sqlalchemy, psycopg2, pydantic, alembic.  
  * Tạo cấu trúc thư mục Clean Architecture (routers, services, repositories, schemas, models).  
* \[ \] **Task 1.2: Thiết lập Database & ORM**  
  * Định nghĩa các Class Models bằng SQLAlchemy dựa trên 14 bảng trong PRD.  
  * Cấu hình Alembic và chạy migration đầu tiên để tạo bảng trong PostgreSQL.  
* \[ \] **Task 1.3: Module Xác thực (Auth Service)**  
  * Viết logic mã hóa mật khẩu (hashing) bằng passlib.  
  * Viết logic tạo và xác thực JWT Token bằng python-jose.  
  * Viết API POST /auth/register (Tạo tài khoản).  
  * Viết API POST /auth/login (Trả về access\_token).  
  * Viết Middleware/Dependency kiểm tra role (Admin/Teacher vs Student).  
* \[ \] **Task 1.4: Quản lý Đề thi cơ bản (CRUD Exams)**  
  * Viết API POST /exams (Giáo viên tạo đề thi).  
  * Viết API GET /exams (Lấy danh sách đề thi).  
  * Viết API PUT /exams/{id} (Sửa thông tin đề thi).

## **Tuần 2: Tích hợp AI & Quản lý Tài liệu (Core Feature)**

**Mục tiêu:** Hoàn thiện luồng upload file, bóc tách chữ, và dùng BackgroundTasks gọi LLM sinh câu hỏi.

* \[ \] **Task 2.1: Xử lý Upload File (Document Service)**  
  * Viết API POST /materials/upload nhận file từ form-data.  
  * Lưu file vào thư mục local (hoặc mock đường dẫn).  
  * Lưu record vào bảng study\_materials.  
* \[ \] **Task 2.2: Bóc tách văn bản (Text Extraction)**  
  * Tích hợp PyMuPDF (hoặc pdfplumber) để đọc text từ file PDF.  
  * Tích hợp python-docx để đọc file Word.  
  * Cập nhật trường parsed\_text trong DB.  
* \[ \] **Task 2.3: Tích hợp AI Agent (LLM Integration)**  
  * Viết hàm gọi API của OpenAI hoặc Gemini (dùng thư viện openai hoặc google-generativeai).  
  * Thiết kế Prompt: *"Đọc đoạn văn bản sau và tạo 5 câu trắc nghiệm. Trả về định dạng JSON mảng các object gồm câu hỏi và 4 đáp án (1 đáp án đúng)."*  
* \[ \] **Task 2.4: Xử lý Bất đồng bộ (BackgroundTasks)**  
  * Viết hàm tổng hợp kết nối Task 2.2 và 2.3.  
  * Tích hợp hàm này vào BackgroundTasks trong route Upload file để API trả về phản hồi ngay lập tức, trong khi AI vẫn chạy ngầm.  
  * Viết logic parse JSON từ AI và lưu vào bảng questions \+ options (đánh dấu is\_ai\_generated \= True).  
* \[ \] **Task 2.5: Ghép câu hỏi vào Đề thi**  
  * Viết API GET /materials/{id}/questions để giáo viên xem câu hỏi AI vừa tạo.  
  * Viết API POST /exams/{id}/questions/bulk để add câu hỏi vào đề.

## **Tuần 3: Trải nghiệm Thi & Chấm điểm (Execution & Grading)**

**Mục tiêu:** Hoàn thiện luồng học viên vào thi, đếm giờ, nộp bài và chấm điểm an toàn.

* \[ \] **Task 3.1: API Lấy đề thi cho Học viên (Bảo mật)**  
  * Viết API GET /student/exams/{id}/start (Bắt đầu thi).  
  * Ghi nhận record vào bảng submissions với start\_time là giờ hiện tại hệ thống.  
  * **CRITICAL:** Cấu hình Pydantic Schema để *loại bỏ hoàn toàn* trường is\_correct của bảng options trước khi trả JSON về cho Học viên.  
* \[ \] **Task 3.2: API Nộp bài (Submit Service)**  
  * Viết API POST /student/exams/{id}/submit nhận mảng các {question\_id, selected\_option\_id}.  
  * Viết logic kiểm tra thời gian: Kiểm tra xem current\_time \- start\_time có vượt quá duration\_minutes của đề thi không (cộng thêm 1-2 phút bù trừ mạng lag).  
* \[ \] **Task 3.3: Logic Chấm điểm (Grading Service)**  
  * Query database lấy đáp án đúng cho các câu hỏi trong đề.  
  * So sánh đáp án của học viên, lưu vào bảng submission\_answers.  
  * Tính total\_score và cập nhật bảng submissions.  
  * Trả về điểm số ngay lập tức.

## **Tuần 4: Frontend, Ghép nối & Sửa lỗi (UI & Refinement)**

**Mục tiêu:** Dựng giao diện cơ bản (ReactJS hoặc HTML/JS thuần) để demo ứng dụng chạy thực tế.

* \[ \] **Task 4.1: UI Xác thực & Điều hướng**  
  * Giao diện Đăng nhập / Đăng ký.  
  * Lưu JWT vào localStorage hoặc cookies.  
  * Phân luồng: Admin vào Dashboard Giáo viên, Student vào màn hình chọn đề thi.  
* \[ \] **Task 4.2: Giao diện Giáo viên (Teacher Workspace)**  
  * Màn hình Upload Tài liệu (có trạng thái "Đang xử lý AI", "Hoàn tất").  
  * Màn hình tạo Đề thi và Review danh sách câu hỏi.  
* \[ \] **Task 4.3: Giao diện Học viên (Student Workspace)**  
  * Màn hình danh sách đề thi đang mở.  
  * **Màn hình Làm bài thi:** Hiển thị đồng hồ đếm ngược (Countdown timer) bằng Javascript. Tự động gọi hàm Submit khi đồng hồ về 00:00.  
  * Màn hình Xem điểm.  
* \[ \] **Task 4.4: Kiểm thử và Hoàn thiện (Testing & Polish)**  
  * Test luồng end-to-end từ tạo tài khoản đến nộp bài.  
  * Xử lý các lỗi ngoại lệ (vd: Học viên submit 2 lần, AI trả về JSON sai định dạng).  
  * Viết tài liệu README hướng dẫn chạy dự án.