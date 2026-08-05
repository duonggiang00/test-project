# **Product Requirements Document (PRD): AI-Powered Online Quiz Web App**

**Tên dự án:** Hệ thống Thi Trắc nghiệm Trực tuyến tích hợp AI

**Mục tiêu:** Đồ án / Dự án cá nhân (Thời gian phát triển: 3-4 tuần)

**Nền tảng:** Web Application

**Phiên bản:** 1.0 (MVP)

## **1\. Tổng quan dự án (Project Overview)**

### **1.1. Vấn đề (Problem Statement)**

Việc tạo đề thi trắc nghiệm thủ công tốn rất nhiều thời gian của giáo viên, đặc biệt là khâu đọc tài liệu (giáo trình, slide) và trích xuất thành các câu hỏi chuẩn định dạng.

### **1.2. Giải pháp (Solution)**

Xây dựng một Web Application với 2 luồng tính năng chính:

1. Cho phép học viên tham gia thi trắc nghiệm trực tuyến, tự động chấm điểm và tính giờ.  
2. Cung cấp công cụ cho giáo viên upload tài liệu học tập (PDF, Word, Text) và sử dụng AI Agent để tự động sinh ra ngân hàng câu hỏi trắc nghiệm từ tài liệu đó.

## **2\. Đối tượng Người dùng (User Roles / Actors)**

Hệ thống được thiết kế với 2 vai trò chính (Non-SaaS, hệ thống nội bộ):

1. **Giáo viên / Quản trị viên (Teacher/Admin):**  
   * Người tạo ra nội dung (đề thi, tài liệu).  
   * Kiểm duyệt các câu hỏi do AI tạo ra.  
   * Theo dõi kết quả thi của học viên.  
2. **Học viên (Student):**  
   * Người tham gia làm bài kiểm tra.  
   * Chỉ được phép tương tác với các đề thi đã được "Xuất bản" (Published).

## **3\. Yêu cầu Chức năng (Functional Requirements)**

### **3.1. Module Xác thực & Tài khoản (Authentication)**

* **F1. Đăng ký / Đăng nhập:** Người dùng đăng nhập bằng Email và Password. Sử dụng JWT (JSON Web Token) để xác thực phiên làm việc.  
* **F2. Phân quyền Role-based:** Chặn học viên truy cập vào các API tạo đề thi hoặc xem tài liệu quản trị.

### **3.2. Module Dành cho Giáo viên (Teacher Workspace)**

* **F3. Quản lý Tài liệu học tập (Knowledge Base):**  
  * Upload file tài liệu (.pdf, .docx, .md).  
  * Hệ thống trích xuất text và lưu trữ.  
* **F4. Tích hợp AI sinh câu hỏi (Core Feature):**  
  * Giáo viên bấm nút "Tạo câu hỏi bằng AI" trên một tài liệu đã upload.  
  * Hệ thống chạy ngầm (Background Task) gửi text cho LLM (OpenAI/Gemini) kèm prompt yêu cầu trả về JSON danh sách câu hỏi trắc nghiệm (1 đáp án đúng).  
  * Tự động lưu câu hỏi vào Database với cờ is\_ai\_generated \= TRUE.  
* **F5. Quản lý Đề thi (Exam Management):**  
  * Tạo/Sửa/Xóa Đề thi (Tiêu đề, mô tả, thời gian làm bài).  
  * Thêm câu hỏi vào đề thi (nhập thủ công hoặc chọn từ danh sách câu hỏi AI đã sinh).  
  * Đổi trạng thái is\_published thành TRUE để mở kỳ thi.  
* **F6. Xem Báo cáo:** Xem danh sách học viên đã nộp bài và điểm số.

### **3.3. Module Dành cho Học viên (Student Workspace)**

* **F7. Danh sách Đề thi:** Xem các kỳ thi đang mở (Published).  
* **F8. Trải nghiệm Thi (Exam Interface):**  
  * Giao diện hiển thị 1 câu hỏi trên 1 trang hoặc danh sách cuộn.  
  * Có đồng hồ đếm ngược (Countdown Timer) hoạt động dựa trên duration\_minutes.  
  * Hệ thống cảnh báo và tự động nộp bài khi hết giờ.  
* **F9. Nộp bài & Xem điểm:**  
  * Gửi danh sách đáp án đã chọn về server.  
  * Hiển thị điểm số ngay lập tức (Tổng số điểm / Tổng số câu).

## **4\. Yêu cầu Phi chức năng (Non-Functional Requirements)**

* **Công nghệ Backend:** **FastAPI** (Python). Phù hợp nhất cho xử lý AI bất đồng bộ và API hiệu năng cao.  
* **Cơ sở dữ liệu:** **PostgreSQL** kết hợp SQLAlchemy 2.0 (ORM).  
* **Kiến trúc Code:** Áp dụng **Clean Architecture** cơ bản (Tách biệt Route, Service, và Repository).  
* **Xử lý AI Background:** Không sử dụng Celery/RabbitMQ để giữ dự án ở quy mô 3-4 tuần. Thay vào đó, sử dụng tính năng **BackgroundTasks** tích hợp sẵn của FastAPI.  
* **Bảo mật thi cử:**  
  * API lấy đề thi **TUYỆT ĐỐI KHÔNG** được trả về trường is\_correct của bảng options (chặn học viên xem source code để gian lận).  
  * Logic chấm điểm phải thực hiện 100% trên server.

## **5\. Luồng Giao diện cơ bản (UI/UX Flow)**

### **5.1. Luồng AI sinh câu hỏi (Teacher)**

1. Màn hình Dashboard \-\> Chọn Tài liệu học tập.  
2. Bấm Upload File (Giao diện hiển thị loading bar).  
3. Sau khi upload, file ở trạng thái "Sẵn sàng". Bấm Generate Quiz.  
4. Giao diện hiển thị Toast Notification: *"Đang xử lý AI. Vui lòng đợi..."*.  
5. Sau \~10-20 giây, load lại trang, xem danh sách câu hỏi AI vừa tạo ra. Có thể chỉnh sửa nội dung nếu AI làm sai.

### **5.2. Luồng làm bài thi (Student)**

1. Màn hình Trang chủ Học viên \-\> Bấm vào thẻ Kỳ thi giữa kỳ.  
2. Hiển thị trang giới thiệu \-\> Bấm nút Bắt đầu làm bài.  
3. Chuyển sang Giao diện Thi (Full màn hình). Bên trái là danh sách số thứ tự câu hỏi, bên phải là nội dung câu hỏi và 4 đáp án (Radio buttons). Góc trên cùng là đồng hồ đếm ngược.  
4. Bấm Nộp bài \-\> Chuyển sang màn hình Kết quả hiển thị điểm số.

## **6\. Lộ trình phát triển (Timeline Estimate \- 3 Tuần)**

* **Tuần 1: Nền tảng & Database**  
  * Khởi tạo dự án FastAPI, cấu hình PostgreSQL.  
  * Code hệ thống Đăng ký/Đăng nhập (JWT).  
  * Viết CRUD API cho Exam, Question, Options.  
* **Tuần 2: Tích hợp AI Agent**  
  * Viết code bóc tách chữ từ file PDF/Word.  
  * Viết Service gọi API của mô hình ngôn ngữ (OpenAI/Gemini).  
  * Kết nối BackgroundTasks và lưu câu hỏi vào DB.  
* **Tuần 3: UI, Thi & Chấm điểm**  
  * Viết API Bắt đầu thi (ghi nhận start\_time).  
  * Viết API Nộp bài (so khớp đáp án đúng, tính total\_score).  
  * Ghép nối Frontend (nếu có) và Fix bug tổng thể.