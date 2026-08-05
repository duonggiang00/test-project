export const ERROR_MESSAGES: Record<string, string> = {
  // Auth & User Errors
  USER_ALREADY_EXISTS: 'Email này đã được sử dụng. Vui lòng chọn email khác.',
  INVALID_CREDENTIALS: 'Email hoặc mật khẩu không chính xác.',
  USER_NOT_FOUND: 'Không tìm thấy thông tin người dùng.',
  INVALID_ROLE: 'Vai trò không hợp lệ.',
  NOT_ENOUGH_PERMISSIONS: 'Bạn không có quyền thực hiện hành động này.',
  UNAUTHORIZED: 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn.',

  // Content Management Errors (Topics, Exams, Questions)
  TOPIC_NOT_FOUND: 'Không tìm thấy chủ đề được yêu cầu.',
  TOPIC_IN_USE: 'Chủ đề này đang được sử dụng trong bài thi hoặc câu hỏi, không thể xóa.',
  EXAM_NOT_FOUND: 'Không tìm thấy đề thi hoặc đề thi chưa được xuất bản.',
  QUESTION_NOT_FOUND: 'Không tìm thấy câu hỏi được yêu cầu.',
  SUBMISSION_NOT_FOUND: 'Không tìm thấy kết quả làm bài.',

  // Student & Exam Submission Errors
  ALREADY_SUBMITTED: 'Bạn đã nộp bài thi này rồi.',
  NOT_STARTED_YET: 'Bạn chưa bắt đầu bài thi này.',
  NOT_SUBMITTED: 'Bài thi này chưa được nộp.',
  TIME_LIMIT_EXCEEDED: 'Đã hết thời gian làm bài. Kết quả không được chấp nhận.',

  // Generic & Validation Errors
  VALIDATION_ERROR: 'Dữ liệu nhập vào không hợp lệ. Vui lòng kiểm tra lại.',
  UNKNOWN_ERROR: 'Đã có lỗi xảy ra, vui lòng thử lại sau.'
};

export const getErrorMessage = (code: string | null | undefined): string => {
  if (!code) return ERROR_MESSAGES.UNKNOWN_ERROR;
  return ERROR_MESSAGES[code] || ERROR_MESSAGES.UNKNOWN_ERROR;
};
