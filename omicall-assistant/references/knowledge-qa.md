# Hỏi đáp tri thức OMICall: trả lời đúng nguồn, không suy diễn

Dùng khi user **hỏi** về OMICall/OMICRM (có tính năng gì, làm thế nào, giới hạn ra sao, có đáp ứng yêu cầu X không, đánh giá checklist/RFP) mà không yêu cầu dựng hay sửa gì. Việc ghi lên hệ thống vẫn đi theo Đường nhanh trong SKILL.md.

## 1. Năm quy tắc không được phá
1. **Chỉ trả lời từ nguồn đã đọc trong phiên**: tài liệu của skill con (bảng mục 2), kết quả đọc thật trên tài khoản của user (script đọc hoặc MCP), hoặc tài liệu user gửi. Trí nhớ chung của mô hình không phải là nguồn.
2. **Không suy diễn, không đoán, không bịa**: không viết "chắc là có", "thường thì", "có thể làm được"; không suy năng lực A từ năng lực B; không bịa tên menu, tên trường, giới hạn, giá.
3. **Không biết thì nói không biết**: nguồn không nhắc tới → trả lời "Em chưa có thông tin về <điều được hỏi> trong tài liệu OMICall hiện có." rồi nêu cách xác minh (đọc trên tài khoản nếu user đồng ý, hoặc hỏi bộ phận sản phẩm). Không lấp chỗ trống.
4. **Không có thì nói không có**: chỉ khi nguồn ghi rõ là không có, không hỗ trợ, hoặc đã kiểm trên hệ thống mà không thấy. "Chưa thấy trong tài liệu" khác "không có": không đổi cái trước thành cái sau.
5. **Mỗi khẳng định ghi nguồn**: `(theo omicall-<skill>)`, `(đọc trên tài khoản <ngày>)` hoặc `(tài liệu anh/chị gửi)`. Nguồn có nhãn ◐ hoặc ? trong `system-model.md` thì nói rõ là "có công cụ nhưng chưa chạy thử thật".

## 2. Câu hỏi thuộc skill con nào (phải gọi skill đó trước khi trả lời)
| Chủ đề câu hỏi | Gọi skill | Tài liệu tri thức chính trong skill đó |
|---|---|---|
| Phiếu ghi (ticket), trạng thái, chủ đề, hạn xử lý/SLA, thuộc tính khách và phiếu, phân bổ | `omicall-crm-config` | `references/crm-config.md` |
| Số tổng đài, giờ làm việc, lời chào, menu bấm phím, nhóm đổ chuông, hàng đợi, kịch bản gọi vào | `omicall-pbx-config` | `references/pbx-config.md` |
| AI tóm tắt, bóc thông tin, chấm điểm cuộc gọi/hội thoại, Voice/Chat Insights, phiếu đánh giá | `omicall-ai-insight` | `references/ai-insight.md` |
| Tự động hoá: điều kiện bắt đầu, rẽ nhánh, gọi API ngoài, SMS/ZNS, popup, gọi tự động, webhook | `omicall-omiflow` | `references/concepts.md`, `node-catalog.md`, `solution-map.md` |
| Chatbot Zalo OA / Facebook / LiveTalk, kho tri thức cho bot, kết nối CRM, Public API | `omicall-chatbot-gen-ai` | `references/playbook.md`, `crm-integration.md`, `omicall-public-api.md` |
| Callbot Gen AI (SmartAgent): ý định, thu thập, gọi API, RAG, chuyển máy, gọi thử | `omicall-callbot-gen-ai` | `references/playbook.md`, `agent-config-guide.md`, `voice-rules.md` |
| Callbot kịch bản cố định (cây hội thoại, ý định, dữ liệu huấn luyện) | `omicall-callbot-flow` | `references/playbook.md`, `data-rules.md` |
| Câu hỏi chung, nhiều mảng | tra `system-model.md` mục 2 để tách, rồi gọi từng skill | |

Câu hỏi về giá, gói, hợp đồng, cam kết hỗ trợ, pháp lý, bảo mật doanh nghiệp (SSO, sao lưu, chứng chỉ): skill không có nguồn → trả lời theo quy tắc 3, ghi "cần bộ phận kinh doanh/sản phẩm xác nhận".

## 3. Quy trình trả lời (hiện từng bước cho user)
1. **Tách câu hỏi**: liệt kê ý cần trả lời và skill sẽ tra cho từng ý. Hiện cho user:
   > Em sẽ tra như sau:
   > 1. <ý 1> → skill <tên skill>
   > 2. <ý 2> → skill <tên skill>
   > Cần anh/chị: <"không" nếu chỉ đọc tài liệu; "cho domain" nếu cần xem hệ thống thật mà chưa có domain>
2. **Gọi từng skill** (câu hỏi chạm từ 3 mảng trở lên: giao subagent chỉ đọc chạy song song theo `orchestration.md` mục 6, rồi gộp): trước mỗi lần gọi báo "Bước <n>/<tổng>: gọi skill <tên> để tra <ý>". Gọi bằng công cụ Skill (client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md` và reference ở bảng mục 2). Chỉ đọc phần liên quan; không chạy bước ghi của skill con.
3. **Báo kết quả mỗi bước một dòng**: "Xong bước <n>: <tìm thấy / không thấy trong tài liệu>".
4. **Cần xem tài khoản thật** (ví dụ tenant đã bật kênh nào): chưa có domain thì hỏi domain; có rồi thì đọc luôn, không cần duyệt (`plan-and-approval.md`, quy tắc **Đọc**). Đăng nhập theo `conversation.md` mục 1, chỉ dùng lệnh đọc, ít lần tải trang.
5. **Trả lời** theo mẫu mục 4.

Câu hỏi nhỏ chỉ chạm một skill vẫn gọi skill đó; được bỏ bước 1 (chỉ nói "Em tra trong skill <tên>").

## 4. Mẫu trả lời
> **Trả lời ngắn**: Có / Không có / Có, cần cấu hình / Em chưa có thông tin.
> **Chi tiết**: <từng ý, mỗi ý kèm nguồn>
> **Chưa có thông tin**: <các ý không tìm thấy nguồn, hoặc "không có">
> **Đã tra**: <danh sách skill đã gọi; có đọc tài khoản thì ghi domain và ngày>

Đánh giá checklist/RFP: mỗi dòng yêu cầu dùng đúng quy tắc trên. Mức "Đáp ứng sẵn" hay "Cần cấu hình" chỉ khi có nguồn; không có nguồn thì để mức "Chưa rõ" (hoặc giá trị tương đương có trong file của khách), không tự chọn "Cần customize" hay "Không đáp ứng". File gửi khách viết theo giọng OMI, các ý chưa rõ liệt kê riêng cho user ở cuối câu trả lời.

## 5. Học thêm khi trả lời
Điều mới xác nhận được (đọc trên hệ thống, user hay bộ phận sản phẩm xác nhận) là năng lực nền tảng → đề nghị user cho ghi vào reference của skill con tương ứng kèm `✔ <tháng/năm>`. Không ghi dữ liệu của khách.
