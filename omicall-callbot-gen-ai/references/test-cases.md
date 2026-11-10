# Bộ tình huống kiểm thử chung (callbot chấm n/12; chatbot chấm G1–G14, dùng bảng này làm kịch bản thử)

Chạy sau mỗi lần dựng hoặc sửa, trước khi giao. Kỳ vọng lấy từ `references/default-behaviors.md`; ô nào bảng đó ghi "—" thì kỳ vọng là "Cần xác nhận với user", không tự đoán. Callbot: gọi thử bằng số user đưa (callbot gen-ai có `scripts/webcall_test.py`). Chatbot: chat thử trên LiveTalk, gõ `/end` sau mỗi lần cập nhật bot rồi dùng hội thoại mới.

| # | Tình huống | Cách thử | Đạt khi |
|---|---|---|---|
| 1 | Khách đồng ý đúng mục đích kịch bản | Trả lời đồng ý ở bước chính | Đi tiếp đúng nhánh, không cúp |
| 2 | Khách từ chối / bận | Nói không cần, đang bận | Không `END_CALL` ngay; theo bảng mặc định của loại bot |
| 3 | Hỏi ngoài phạm vi | Hỏi chuyện không có trong tài liệu | Không bịa; theo bảng mặc định (callbot cổ điển: nhắc lại 1 lần rồi chuyển; SmartAgent: chuyển nhân viên) |
| 4 | Hỏi lại cùng chủ đề hỏi đáp | Hỏi hai lần cùng câu | Theo bảng mặc định (callbot cổ điển: lần hai báo chuyển máy) |
| 5 | Đòi gặp nhân viên | "Cho tôi gặp người thật" | Báo chuyển rồi chuyển máy/nhân viên đúng nhóm |
| 6 | Khách tức giận | Nói lời gay gắt | Xin lỗi; hành vi tiếp theo theo bảng (callbot cổ điển: kết thúc) |
| 7 | Khách im lặng | Không nói gì | Nhắc 1 lần; vẫn im thì kết thúc lịch sự |
| 8 | Yêu cầu lặp lại | "Nói lại giúp tôi" | Đọc lại 1 lần (callbot cổ điển); lần sau chuyển nhân viên |
| 9 | Sai người / số nhầm | "Tôi không phải anh A" | Theo bảng mặc định; ô "—" thì Cần xác nhận |
| 10 | Thu thông tin (ngày, số, tên) | Đọc giá trị bằng lời nói tự nhiên | Biến thu đúng, đọc xác nhận lại nếu kịch bản yêu cầu |
| 11 | Kết thúc bình thường | Nói hết nhu cầu | Bot hỏi "còn cần hỗ trợ gì không" rồi mới chào kết thúc |
| 12 | Nói nhiều ý trong một câu | Vừa đồng ý vừa hỏi giá | Xử lý ý chính, không rơi vào nhánh sai |

Báo kết quả theo mẫu: callbot `Đạt n/12`; chatbot chấm theo G1–G14 (`livetalk-test-optimize.md`). Liệt kê tình huống không đạt kèm câu thực tế của bot, và tình huống bỏ qua (kèm lý do). Không đạt: sửa rồi chạy lại đúng tình huống đó; không tự cho là đạt khi chưa thử.
