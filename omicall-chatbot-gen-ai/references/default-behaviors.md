# Bảng mặc định kịch bản: callbot cổ điển, SmartAgent, chatbot

Chỉ ghi quy tắc đã có trong SKILL.md của từng skill. Ô "—" nghĩa là skill chưa quy định, không suy diễn: hỏi user hoặc ghi "Cần xác nhận". Quy tắc gốc nằm ở skill tương ứng; sửa ở đó rồi cập nhật bảng này.

| Tình huống | Callbot cổ điển (`omicall-callbot-flow`) | SmartAgent (`omicall-callbot-gen-ai`) | Chatbot (`omicall-chatbot-gen-ai`) |
|---|---|---|---|
| Không trả lời được / ngoài phạm vi | Nhắc lại câu của bước 1 lần, lần hai chuyển nhân viên | Nhánh `bot_can_not_answer` luôn nối `TRANSFER_CALL` | — |
| Hỏi đáp | Trả lời 1 lần; hỏi lại cùng chủ đề → báo chuyển máy → chuyển nhân viên | Truy xuất tri thức (RAG) | RAG từ Dữ liệu khác |
| Khách đòi gặp nhân viên | Báo chuyển → chuyển máy (`transfer_collected_info:true`) | `TRANSFER_CALL` | Chuyển nhân viên qua trường hợp → ACTION; bot vẫn gửi 1 câu LLM tự soạn (giới hạn nền tảng) |
| Khách tức giận | Xin lỗi, kết thúc | — | — |
| Khách im lặng | Nhắc 1 lần, vẫn im thì kết thúc lịch sự | Hỏi lại 1 lần còn nhu cầu nào không, vẫn im thì kết thúc lịch sự | — |
| Từ chối / bận / sai người | — | Không nối `END_CALL`; dừng ở node cuối, bot vẫn hỏi khách còn cần hỗ trợ gì | — |
| Trước khi kết thúc | Hỏi "còn cần hỗ trợ gì không", rồi chào cảm ơn + tạm biệt | Hỏi còn nhu cầu nào không, khách xác nhận hết mới `END_CALL` | — |
| Xưng hô | `{{gender1_ai}}` thay mọi "anh/chị" | — | — |
| Mặc định khi lưu | Không Xuất bản, không gắn hotline | `--new` + `is_publish:false`; không ghi đè script đang chạy | Lưu bản nháp; Xuất bản chỉ khi user yêu cầu |

Khác biệt có chủ đích: callbot cổ điển chuyển nhân viên sau lần thứ hai vì kịch bản cố định; SmartAgent tự xử lý trong hội thoại nên chỉ chuyển khi không trả lời được hoặc khách yêu cầu. Cùng một khách dùng cả hai loại: báo user các khác biệt này trong bản Tóm tắt.
