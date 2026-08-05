# **Product Requirements Document (PRD): Thiết kế UI/UX Toàn Hệ thống**

**Dự án:** Hệ thống Thi Trắc nghiệm Trực tuyến tích hợp AI

**Phân hệ:** Full-stack (Teacher Workspace & Student Portal)

**Định hướng UI:** Modern, Minimalist, ưu tiên sử dụng các UI Component libraries (như Shadcn UI, Ant Design, hoặc Tailwind CSS cơ bản) để tiết kiệm thời gian (Dự án 4 tuần).

## **1\. Triết lý Thiết kế (Design Philosophy)**

Hệ thống phục vụ 2 nhóm người dùng với nhu cầu trái ngược nhau, do đó layout cần phân tách rõ ràng:

* **Giáo viên / Quản trị viên (Teacher/Admin):**  
  * *Mục tiêu:* Quản lý dữ liệu phức tạp, thao tác nhiều bước (Upload file \-\> Đợi AI \-\> Tạo đề \-\> Gắn câu hỏi).  
  * *Triết lý UI:* **Data-Dense & Workflow-Oriented**. Sử dụng giao diện Sidebar (Menu bên trái) dạng Dashboard chuyên nghiệp. Màn hình ưu tiên Desktop. Hiển thị rõ ràng các trạng thái hệ thống (Loading, Thành công, Lỗi).  
* **Học viên (Student):**  
  * *Mục tiêu:* Tìm đề thi, làm bài tập trung, xem điểm.  
  * *Triết lý UI:* **Focus & Distraction-Free**. Sử dụng giao diện Topbar (Menu trên cùng). Ẩn mọi thứ không cần thiết khi vào thi. Ưu tiên Mobile-first.

## **2\. Hệ thống Thiết kế Chung (Design System)**

* **Màu sắc chủ đạo (Primary):** Xanh dương (\#2563EB) \- Phù hợp cho giáo dục, tạo sự tin cậy.  
* **Màu hệ thống:**  
  * *Success (AI tạo xong, nộp bài thành công):* Xanh lá (\#10B981)  
  * *Warning/Processing (AI đang chạy, sắp hết giờ):* Vàng cam (\#F59E0B)  
  * *Danger (Lỗi file, xóa đề):* Đỏ (\#EF4444)  
* **Typography:** Font Inter hoặc Roboto. Giao diện giáo viên dùng chữ nhỏ hơn (14px cơ bản) để hiển thị nhiều thông tin, giao diện học viên dùng chữ to hơn (16px cơ bản) để dễ đọc.

## **3\. Chi tiết Giao diện Khối Quản lý (Teacher Workspace)**

Giao diện sử dụng cấu trúc **Admin Dashboard** tiêu chuẩn: Sidebar bên trái cố định để điều hướng, Header trên cùng chứa Avatar/Đăng xuất, phần Content ở giữa để thao tác.

### **3.1. Màn hình Dashboard (Tổng quan)**

* **Mục đích:** Nắm bắt nhanh tình hình hệ thống.  
* **Thành phần (Widgets):**  
  * Các thẻ thống kê nhanh (Cards): Tổng số Đề thi, Tổng số Câu hỏi AI đã tạo, Tổng số Học viên, Lượt thi trong tuần.  
  * Bảng "Đề thi đang mở gần đây": Hiển thị trạng thái số người đã nộp bài.  
  * Bảng "Tài liệu đang xử lý": Hiển thị trạng thái các file PDF/Word đang được AI phân tích.

### **3.2. Màn hình Quản lý Tài liệu & AI (Knowledge Base)**

* **Mục đích:** Nơi giáo viên upload tài liệu để AI tự động sinh câu hỏi.  
* **Bố cục & UX Flow:**  
  * **Khu vực Upload:** Khối kéo thả file (Drag & Drop zone) to ở giữa màn hình. Chấp nhận .pdf, .docx, .txt.  
  * **Danh sách tài liệu (Table):** Hiển thị danh sách các file đã tải lên.  
  * **Cột Trạng thái (Status Badge) \- Rất quan trọng:**  
    * Pending (Màu xám): Mới tải lên.  
    * Processing (Màu vàng \+ Icon xoay tròn): AI đang đọc và tạo câu hỏi.  
    * Completed (Màu xanh): Kèm theo nút *"Xem X câu hỏi"*.  
  * **UX Tương tác:** Khi giáo viên bấm Upload, file chuyển sang trạng thái Processing. Giao diện hiển thị Toast Notification *"Hệ thống đang nhờ AI phân tích tài liệu, quá trình này mất khoảng 30s. Bạn có thể làm việc khác trong lúc chờ."*

### **3.3. Màn hình Ngân hàng Câu hỏi (Question Bank)**

* **Mục đích:** Xem lại, chỉnh sửa hoặc xóa các câu hỏi (cả tạo tay và AI tạo).  
* **Thành phần:**  
  * Bộ lọc (Filter): Lọc câu hỏi theo nguồn (Từ file tài liệu nào, hoặc phân biệt Sinh bởi AI / Tạo thủ công).  
  * Danh sách (List/Grid): Hiển thị nội dung câu hỏi, chỉ rõ đáp án đúng (màu xanh). Có nhãn dán (Tag) ✨ AI Generated để giáo viên chú ý kiểm duyệt.

### **3.4. Màn hình Quản lý Đề thi (Exam Builder)**

* **Mục đích:** Tạo lập cấu trúc đề thi và phát hành.  
* **Flow gồm 3 bước (Tabs):**  
  * **Bước 1 \- Cấu hình chung:** Form nhập Tên kỳ thi, Mô tả, Thời gian làm bài (phút). Nút Toggle "Xuất bản" (Publish).  
  * **Bước 2 \- Thêm câu hỏi:**  
    * Chia làm 2 cột. Cột trái là danh sách câu hỏi trong ngân hàng (có thanh Search). Cột phải là danh sách câu hỏi đã được add vào Đề thi.  
    * Có nút *"Thêm nhanh toàn bộ câu hỏi từ tài liệu A"*.  
  * **Bước 3 \- Xem trước (Preview):** Hiển thị đề thi dưới góc nhìn của học viên để giáo viên kiểm tra lần cuối.

### **3.5. Màn hình Báo cáo (Submissions & Reports)**

* **Mục đích:** Xem điểm của học viên.  
* **Thành phần:**  
  * Dropdown chọn Đề thi.  
  * Bảng danh sách học viên đã thi: Họ tên, Giờ nộp, Điểm số.  
  * Nút "Xem chi tiết": Mở ra Modal hiển thị bài làm của học viên đó (câu nào đúng, câu nào sai).

## **4\. Chi tiết Giao diện Khối Học viên (Student Portal)**

Giao diện loại bỏ Sidebar, sử dụng **Top Navigation Bar** đơn giản gồm Logo và Avatar/Tên học sinh.

### **4.1. Màn hình Trang chủ (Student Dashboard)**

* **Mục đích:** Chọn đề thi để bắt đầu.  
* **Thành phần:**  
  * Banner chào mừng: *"Chào buổi sáng, hôm nay bạn muốn ôn tập môn gì?"*  
  * **Grid Đề thi (Card):** Hiển thị các bài thi đang is\_published \= True. Trên thẻ ghi rõ Thời gian (VD: 45 phút) và Tổng số câu (VD: 30 câu). Nút "Vào thi" nổi bật.

### **4.2. Màn hình Làm bài thi (Exam Engine)**

* **Bố cục Desktop (Chia 2 cột):**  
  * **Cột trái (25%):** "Bản đồ câu hỏi". Lưới các ô vuông đánh số 1, 2, 3...  
    * Màu trắng viền xám: Chưa làm.  
    * Màu xanh nhạt: Đã làm.  
  * **Cột phải (75%):** Khu vực làm bài.  
    * **Header cố định (Sticky):** Đồng hồ đếm ngược siêu to. Có hiệu ứng đập (pulse) và chuyển màu Đỏ khi còn dưới 3 phút. Nút "Nộp bài".  
    * **Khu vực Câu hỏi:** Hiển thị 1 câu hỏi duy nhất tại 1 thời điểm. 4 đáp án dạng nút bấm to (Radio Block). Bấm vào đổi màu viền báo hiệu đã chọn.  
    * **Footer:** Nút "Câu trước" và "Câu tiếp".  
* **Bố cục Mobile:**  
  * Đồng hồ đếm ngược bám dính ở cạnh trên màn hình.  
  * Bản đồ câu hỏi được giấu vào một nút bấm (dạng Bottom Sheet) góc dưới màn hình, vuốt lên để xem.

### **4.3. Màn hình Kết quả (Result Screen)**

* **Mục đích:** Thông báo điểm số và giải tỏa áp lực.  
* **Thành phần:**  
  * Hiệu ứng Loading (1-2s) *"Đang tính điểm..."*.  
  * Điểm số hiển thị ở giữa vòng tròn lớn.  
  * Nếu điểm \>= 80%: Đổ hiệu ứng pháo hoa (Confetti) toàn màn hình \+ Lời chúc *"Tuyệt vời\!"*.  
  * Nếu điểm \< 80%: Lời động viên *"Cố lên ở lần sau nhé\!"*.  
  * Nút "Quay về trang chủ" và "Xem lại bài làm" (Nếu giáo viên cho phép xem đáp án đúng/sai).

## **5\. UI/UX Flow & Edge Cases (Xử lý Ngoại lệ)**

* **Toasts & Alerts:** Mọi hành động CRUD (Thêm, sửa, xóa đề thi, tải file) đều phải hiện Toast ở góc phải màn hình để thông báo kết quả.  
* **Trống dữ liệu (Empty States):** Khi giáo viên chưa tải tài liệu nào hoặc chưa tạo đề thi, thay vì hiện bảng trống, hãy hiện một hình ảnh minh họa (Illustration) kèm nút CTA lớn *"Tải tài liệu đầu tiên của bạn lên ngay"*.  
* **Chống gian lận (Nhẹ) cho Học viên:** Nếu học viên đang thi mà chuyển Tab trình duyệt, hiện ra một cảnh báo popup: *"Cảnh báo: Bạn đang rời khỏi trang làm bài. Bài thi sẽ tự động nộp nếu bạn vi phạm quá 3 lần."* (Tuỳ chọn cấu hình).  
* **Mất kết nối mạng khi đang thi:** Lưu log các câu trả lời vào LocalStorage. Hiện banner vàng: *"Bạn đang mất kết nối mạng. Hãy bình tĩnh làm tiếp, đáp án đang được lưu tạm trên máy của bạn."*