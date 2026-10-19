---
name: ai-chatbot-builder
description: ""
---

# AI Chatbot Builder — Generic Playbook (mọi nền tảng, mọi nghiệp vụ)

# Overview
Skill **tổng quát, không ràng buộc nền tảng** để thiết kế và (khi có thể) tự dựng một AI chatbot hội thoại (text — Zalo OA/Fanpage/Website/Slack/Telegram/…) từ tài liệu nghiệp vụ do người dùng cung cấp. Đúc kết từ kinh nghiệm xây bot trên OMICall/OMICRM (xem skill chị em `omicall-chatbot-gen-ai` / `omicall-callbot-gen-ai` cho phần đặc thù nền tảng đó), nhưng phần **phương pháp luận** ở đây áp dụng được cho bất kỳ builder nào (Dialogflow, Voiceflow, Botpress, custom LLM app, v.v.) — kể cả khi không có API, chỉ có UI để click.

# Khi nào dùng skill này
- User đưa tài liệu nghiệp vụ (docx/xlsx/pdf/txt, hoặc mô tả bằng lời) và muốn: (1) một **system prompt**, (2) **danh sách ý định** bot cần xử lý, (3) một **file RAG tổng hợp** kiến thức, và/hoặc (4) dựng thẳng lên một nền tảng chatbot thật qua UI/API.
- Không có tài liệu nghiệp vụ cụ thể → **hỏi lại** trước khi bịa (không đoán ngành nghề/công ty).

# Quy trình

## Bước 1 — Đọc hết tài liệu nghiệp vụ, KHÔNG bịa
- Đọc từng file (docx → unzip + strip XML hoặc pandoc; xlsx → `openpyxl`, đọc TẤT CẢ sheet, không chỉ sheet đầu).
- Nếu tài liệu đã có sẵn cấu trúc rõ (vd: bảng "STT | Nhu cầu | Thông tin cần thu | Bot cần làm gì | Điều kiện | Kết quả mong muốn") → đó gần như là spec hoàn chỉnh, **dùng luôn**, đừng tự vẽ lại từ đầu.
- Nếu chỉ có tài liệu tri thức rời rạc (FAQ, chính sách...) mà chưa có spec ý định → tự suy luận nhóm ý định từ nội dung + vai trò bot.
- Trích xuất NGUYÊN VĂN mọi số liệu (giá, %, ngày, mã số) — không làm tròn, không tự suy diễn thêm.

## Bước 2 — Viết System Prompt (mô tả CHUNG, không lặp chi tiết từng ý định)
Khung 7 phần dùng lại được cho mọi bot:
1. **Vai trò & mục tiêu** — bot là ai, đại diện cho ai, mục tiêu ưu tiên theo thứ tự.
2. **Xưng hô & giọng văn** — ngôi xưng, độ dài tin nhắn, số tin liên tiếp tối đa, emoji có/không, khi nào tự nhận là AI.
3. **Nguyên tắc dữ liệu** — chỉ nói điều có trong tài liệu/hồ sơ đã cấp; không bịa; số liệu chép nguyên văn; thứ tự xử lý bắt buộc (vd: "vấn đề A trước, vấn đề B sau" nếu nghiệp vụ yêu cầu).
4. **Giới hạn cam kết** — liệt kê rõ điều bot KHÔNG được hứa (giờ, kết quả, có người gọi lại...) + kênh liên hệ chính thức duy nhất khi vượt phạm vi.
5. **Khung giờ hoạt động** (nếu có) — khi nào bot được chủ động nhắn.
6. **Định dạng số liệu/tin nhắn** — SĐT, tiền, ngày tháng trình bày thế nào.
7. **Định nghĩa một hội thoại thành công** — điều kiện coi là hoàn tất đúng nghiệp vụ.
- **Không** mô tả chi tiết từng ý định trong prompt chính — để riêng ở danh sách ý định, prompt chỉ nói luồng xử lý tổng quát (thứ tự ưu tiên các nhóm ý định).

## Bước 3 — Danh sách ý định (file riêng)
Mỗi ý định gồm: **tên ngắn gọn**, **khi nào dùng** (mô tả trigger), **3–5 câu ví dụ khách nói**, **hành động/rẽ nhánh** (kể cả biến cần thu/ghi nếu nghiệp vụ có), **kết quả mong muốn**. Tối thiểu nên có các nhóm: xác thực/định danh (nếu cần), nhu cầu chính (≥1, chia theo nghiệp vụ), đồng ý/xác nhận, từ chối → kết thúc lịch sự, hỏi kiến thức chung → RAG, ngoài phạm vi/khiếu nại → kênh chính thức, (tuỳ) hẹn giờ nhắn lại, (tuỳ) nhắc khi khách im lặng.

## Bước 4 — File RAG tổng hợp
- Nếu có nhiều tài liệu tri thức rời rạc → **gộp thành 1 file** có cấu trúc rõ (Heading theo chủ đề nguồn → Heading phụ theo câu hỏi → đoạn trả lời), giữ **nguyên văn** nội dung gốc để tránh sai lệch số liệu khi RAG trích dẫn.
- Không nhét dữ liệu cá nhân hoá theo từng khách hàng/đối tác (giá riêng, mã số riêng...) vào RAG chung — loại dữ liệu đó nên nằm ở CRM/biến hội thoại (đọc theo từng khách đã định danh), không train chung cho mọi người.
- Tạo file bằng `docx` (npm) theo skill `docx` có sẵn (xem gotchas riêng của skill đó: page size, numbering, table width...).

## Bước 5 — (Tuỳ chọn) Dựng thật lên nền tảng qua UI/API
Khi user muốn build thẳng lên một hệ thống thật (không chỉ giao file):
1. **Ưu tiên UI** nếu chưa nắm chắc schema/API, hoặc nền tảng không có API công khai — dùng browser pane, thao tác y hệt người dùng thật.
2. **Không tự động hoá đăng nhập**: không tự điền username/password bằng script, không tự trích xuất session token/cookie của tài khoản thật để gọi API thay user (kể cả khi user đã cung cấp mật khẩu trong chat) — nhờ **user tự đăng nhập** trong browser pane, sau đó thao tác tiếp bằng click/type. Đây là ranh giới an toàn cố định, không thương lượng dù user đồng ý.
3. **Trước khi sửa** một cấu trúc có sẵn (nhiều ý định/node đã tồn tại): đọc/ghi lại state hiện tại trước khi động vào, để có gì đối chiếu nếu lỡ tay làm mất.
4. **Sau khi lưu**: luôn **tải lại toàn trang** (navigate lại URL, không chỉ đóng/mở lại panel) rồi đọc nội dung để xác nhận server thực sự giữ đúng — đừng tin trạng thái UI ngay sau khi bấm lưu, nhất là app có nhiều tab với cơ chế lưu khác nhau (có tab tự động lưu ngay, có tab cần bấm nút lưu riêng — trộn lẫn dễ làm mất dữ liệu của tab kia).
5. **Tránh phím Escape** để đóng dialog/drawer trong các app editor phức tạp — có thể kích hoạt hành vi ngoài ý muốn (reset state, cảnh báo rời trang). Luôn dùng nút đóng hiển thị rõ trên UI.
6. **Upload file qua UI**: nếu nền tảng mở dialog chọn file cấp hệ điều hành (không phải phần tử trong DOM), cách an toàn nhất là gõ thẳng **đường dẫn tuyệt đối** vào ô tên file rồi Enter — tránh điều hướng bằng click toạ độ trên máy nhiều màn hình/độ phân giải cao (rủi ro click nhầm sang cửa sổ khác của người dùng).
7. Nếu nền tảng giới hạn số lượng file/dữ liệu theo gói — kiểm tra và gỡ dữ liệu cũ không còn cần trước khi thêm mới.
8. **Chỉ liệt kê intent nào cần rẽ nhánh flow xử lý riêng** — không liệt kê những ý định thuần Q&A (bot đã tự trả lời qua system_prompt + RAG). Trước khi thêm 1 intent, hỏi: "ý định này có phải bot làm gì đặc biệt ngoài trả lời văn bản không?" — nếu chỉ trả lời từ RAG thì bỏ qua. Điều này giữ danh sách intent gọn và dễ bảo trì.
9. **Phân biệt "API gọi trước mỗi lượt" vs "API gọi trong 1 case cụ thể"** — nhiều nền tảng có 2 chỗ khai báo API khác nhau (VD: OMICall có "Truy vấn" trong Ngữ cảnh bắt đầu = chạy mỗi lượt, và "Hành động → API" đặt sau case = chỉ chạy khi case match). Chọn đúng theo mục đích.
10. **Xác thực người dùng qua thuộc tính chuẩn, không phải thuộc tính tùy chỉnh** — nhiều nền tảng có cơ chế auto-lookup theo trường "Số điện thoại"/"Email" chuẩn của Contact. Khi import dữ liệu, đặt SĐT/email THẬT vào field chuẩn thay vì thuộc tính tùy chỉnh, để cơ chế auto-lookup hoạt động. Custom attribute chỉ dùng cho dữ liệu bổ sung.
11. **Trước khi tạo Flow/Workflow mới, kiểm tra quota gói dịch vụ** — trên Trial thường bị giới hạn (1 flow, 1 file văn bản, ...). Nếu sắp chạm quota, thiết kế 1 flow đa mục đích thay vì tách nhiều flow nhỏ, hoặc yêu cầu user nâng gói trước khi làm tiếp.

# Nguyên tắc chung
- Prompt viết bằng ngôn ngữ khách hàng cuối dùng (thường là tiếng Việt), ý định liệt kê riêng để người quản trị tự bổ sung ngữ cảnh khi cần.
- Khi tài liệu nghiệp vụ đã rất chi tiết (đã có sẵn tên ý định, biến, rẽ nhánh) → **dùng đúng theo đó**, việc của mình là chuyển thể sang định dạng prompt/ý định/RAG chuẩn, không sáng tác lại từ đầu.
- Khi thiếu tài liệu nghiệp vụ → hỏi lại, đừng đoán ngành nghề.
- Ghi lại schema/UI mới học được (của nền tảng cụ thể) vào skill đặc thù nền tảng đó (vd: `omicall-chatbot-gen-ai`), không nhét vào skill tổng quát này.

# Tham khảo
- `references/prompt-template.md` — khung system prompt 7 phần, điền trực tiếp.
- `references/intent-template.md` — khung mô tả 1 ý định.
- Skill `docx` (anthropic-skills) — tạo/đọc file .docx.
- Skill nền tảng cụ thể (vd: `omicall-chatbot-gen-ai`, `omicall-callbot-gen-ai`, `omicall-omiflow`) — schema/API/gotcha riêng từng hệ thống.
- Khi bot cần thao tác CRM nâng cao (search Contact by attribute, tạo/cập nhật KH có điều kiện): thường cần workflow engine phụ trợ như OMIFlow — xem `omicall-omiflow` cho hình dạng chuẩn.
