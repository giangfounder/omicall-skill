# Chatbot — thao tác giao diện OMiCRM

Đọc khi phải làm trên trình biên tập thay vì API.

## Interactive OMiCRM (user xem realtime)
Chrome CDP port 9222, profile riêng theo tenant: `Start-Process chrome.exe -ArgumentList '--remote-debugging-port=9222',"--user-data-dir=%TEMP%\omicrm-<profile>",'--no-first-run','https://<domain>.omicrm.io/ai/bot/edit/<bot_id>?lng=vi'`. Dùng `cdp.py` (`find_omicrm_tab()` + `CDP(ws).eval_js/navigate`).
**Học schema từ UI**: inject fetch/XHR captor vào trang editor (ghi `POST body`/`response` vào `window.__omiCaps`) → user thao tác trong Chrome → đọc `window.__omiCaps` → ghi schema học được vào api-reference.md.

## Gotchas giao diện
- **Không dùng phím Escape** trong editor Kịch bản để đóng drawer/dialog — có thể kích hoạt reset state cục bộ (mất sạch ý định chưa lưu) hoặc dialog "Xác nhận rời trang"; Esc cũng không đóng ngăn kéo. **Không bấm nút X của ngăn kéo cuối**: X nằm trùng icon menu "Tổng đài", cú bấm xuyên qua và rời trang (mất thay đổi). Đóng ngăn kéo bằng cách bấm vùng mờ bên trái (vd. x≈150, y≈300); nút "Đóng" dạng chữ trong dialog thì bấm được (SKILL.md Gotchas "Editor kịch bản").
- **Tab "Đào tạo" tự động lưu ngay** (mọi thao tác thêm/xoá "Dữ liệu khác", "Bộ câu hỏi" áp dụng tức thì, hiện toast "Cập nhật thành công"/"Đã lưu") — khác tab **"Kịch bản"** cần bấm **"Lưu lại"** thủ công. Nếu tab Kịch bản đang có state cục bộ bị lỗi/mất dữ liệu (do thao tác nhầm), **tuyệt đối không** chuyển sang tab Đào tạo trước khi xử lý xong, vì autosave của Đào tạo có thể không đụng tới campaign — nhưng để chắc chắn, luôn **F5 reload lại toàn trang và xác nhận qua `get_page_text`** sau mỗi thao tác quan trọng trước khi tin state hiện tại là đúng.
- **Trước khi sửa nhiều node**: chụp/đọc lại state hiện có (số lượng ý định, tên) TRƯỚC khi bắt đầu; sau khi sửa xong và bấm "Lưu lại", **luôn reload trang (navigate lại đúng URL) rồi đọc `get_page_text`** để xác nhận server thực sự giữ đúng — không tin tưởng UI ngay sau khi bấm lưu.
- **Upload file "Dữ liệu khác" qua UI** (không phải API): nút thật để mở dialog chọn file là ô pill xanh **"Dung lượng mỗi file tối đa là Xmb 📎"** — **không phải** ô "+ BOT được đào tạo" (đó là picker chọn bot áp dụng, click nhầm sẽ mở dropdown tìm bot). Dialog "Open" mở ra là **cửa sổ OS thật** (không phải phần tử DOM) — cách an toàn nhất là gõ thẳng **đường dẫn tuyệt đối** vào ô "File name" rồi Enter/Open, tránh click điều hướng thư mục bằng toạ độ (rủi ro cao trên máy nhiều màn hình/độ phân giải lớn, có thể click nhầm sang cửa sổ khác của user như Zalo/Chrome cá nhân).
- **UI thêm ý định (bản mới, đơn giản hơn schema cũ)**: nút **"Thêm trường hợp"** trong drawer "Ngữ cảnh bắt đầu" tạo 1 case mới (tự đặt tên "Trường hợp N", không có ô đổi tên riêng trong flow nhanh này) với 2 chế độ — **"Nhận dạng ý định"** (1 ô textarea tự do "Hướng dẫn BOT": viết mô tả + câu ví dụ khách nói gộp chung, KHÔNG phải chip từng câu như schema `campaign.name_mappings[].conditions[].data[]` cũ) và **"Chủ đề / Ý định mong muốn"** (chưa khảo sát — có thể là chỗ đặt tên tuỳ chỉnh, cần xác minh thêm lần sau). Bot vẫn nhận diện tốt với guidance dạng văn xuôi (đã verify: 9 ý định dạng này + build thành công, hiển thị đúng sau reload).

## Cẩn thận reload/thao tác nhầm làm mất dữ liệu
- Thao tác click nhầm/Escape trong tab Kịch bản có thể xóa các "Trường hợp" khỏi state cục bộ. Nếu **chưa lưu** thì reload trang lấy lại được (dữ liệu server còn nguyên); nhưng nếu bấm "Lưu lại" khi state đang thiếu → **mất data server**.
- Sau mỗi lần bấm "Lưu lại", đổi tab qua "Đào tạo" rồi quay lại là cách ép reload nhẹ để kiểm chứng nhanh; nhưng cách chắc nhất vẫn là `navigate` full URL bot editor rồi `get_page_text` verify.
- Ô "Tên nút" trong drawer khi type text mới sẽ **APPEND vào tên cũ** thay vì thay thế — luôn Ctrl+A trước khi type để clear.


## Nút Điều kiện trong bot không có khung giờ làm việc (✔ UI 10/2026)
- Mở: chuột phải canvas Kịch bản → "Điều kiện". Ngăn kéo có Tên nút, Mô tả, Danh sách trường hợp, "Nút kế tiếp"; nhóm so sánh: **Khách hàng / Đa kênh / Dữ liệu thu thập / Chat Insights / Biến liên kết tùy chỉnh**. Không có mục "Khung giờ làm việc" như nút CONDITION của OMIFlow.
- Đa kênh có "Thời gian khách hàng nhắn tin" (`social_last_customer_message…`), "Thời gian tin nhắn cuối", "Thời gian cập nhật"; giá trị so sánh dạng mốc tuyệt đối `HH:mm dd/MM/yyyy` → không rẽ nhánh được theo giờ trong ngày / thứ trong tuần.
- Cần tách trong giờ / ngoài giờ → rẽ ở OMIFlow (`CONDITION` → `CUSTOM` `TIME_FRAME`, skill `omicall-omiflow` node-catalog) trước nút `OMI_BOT_AI`. Nút `OMI_BOT_AI` trong flow có khoá `ai_analyze.active_time` và `bot_can_not_answer` (thấy `null` khi GET) — ý nghĩa: Cần xác nhận.
- Nút "Kết thúc trò chuyện" (`END_BOT`) trong bot ghi chú "Tiếp tục kịch bản OMIFlow ở nhánh 'BOT kết thúc'"; trong flow, nút `OMI_BOT_AI` hiện "AI Chatbot sẽ kết thúc khi: BOT chủ động kết thúc" kèm "Bước tiếp theo" (✔ UI 10/2026). → Một bot dùng được cho cả trong và ngoài giờ: `bot_can_not_answer` → `END_BOT` → flow rẽ `TIME_FRAME` sau nút `OMI_BOT_AI`. Bot chạy lại thật chưa kiểm: Cần xác nhận.

## Cài đặt "Suy diễn" của bot = `mode_reply` / `content_reply` (✔ UI 10/2026)
- Mở: bấm tên bot (cạnh tab Đào tạo) → khối "Cấu hình" → **Suy diễn**: "Cho phép" (BOT trả lời cả câu ngoài kho tri thức) / "Không cho phép" (không tìm thấy trong kho tri thức thì từ chối, gửi **Câu trả lời mặc định** — bắt buộc, ≤256 ký tự).
- Lưu UI với "Cho phép" → GET `mode_reply:""`, `content_reply:""`. "Không cho phép" + câu mặc định → `mode_reply:"static"`, `content_reply:"<câu>"`. Gửi `static` qua `save_draft_v2` có lần GET lại thành `mode_reply:"auto"`, `content_reply:""` (UI vẫn tô "Không cho phép", ô câu mặc định trống) — nguyên nhân: Cần xác nhận.
- "Không cho phép" gửi câu mặc định cho khách → mâu thuẫn với yêu cầu "không trả lời được thì im lặng chuyển nhân viên"; khi đó dùng "Cho phép" + prompt cấm suy diễn + trường hợp chuyển nhân viên, rồi test câu ngoài dữ liệu.
- Cùng khối có "Cấu hình bộ nhớ BOT" (= `history_config`): "Không áp dụng" thì BOT vẫn nhớ 6 tin gần nhất trong phiên.

## Bot không im lặng được khi đi tới nút Kết thúc (✔ test LiveTalk thật 10/2026)
- Đường vào: LiveTalk → OMIFlow `OMI_BOT_AI` → bot. Trường hợp (CUSTOM_INTENT hoặc `bot_can_not_answer`) → `END_BOT`: bot **vẫn gửi một câu LLM tự soạn** (vd. "Em không có thông tin… vui lòng liên hệ…") rồi mới kết thúc; prompt cấm trả lời không chặn được câu này. Chèn ACTION (`ADD_CLASSIFY`) trước `END_BOT` cũng không chặn.
- Nhánh "BOT chủ động kết thúc" của flow chạy ngay sau câu đó (gửi tin + `RE_DISTRIBUTE` đều chạy).
- Sau khi flow `RE_DISTRIBUTE` cho nhóm nhân viên, tin kế tiếp của khách **vẫn được bot trả lời** (trigger "Trạng thái chờ phản hồi = Đang rảnh" vẫn khớp) → muốn tắt bot sau bàn giao: thêm "Trạng thái Chatbot" trong "Cập nhật cuộc trò chuyện" (giá trị: Cần xác nhận).
- Hướng còn lại để bot im lặng (chưa kiểm): ACTION `START_OTHER_CAMPAIGN` **không có bước tiếp theo** (đã kiểm là bot không trả lời tin kích hoạt) gọi flow phụ thuộc làm phần chuyển nhân viên; flow phụ thuộc không nhận biến hội thoại — gửi tin/`RE_DISTRIBUTE` trong đó có chạy không: Cần xác nhận.
- Hành động trong bot (✔ UI 10/2026): Tạo thông báo, Biến liên kết tùy chỉnh, API, Gọi đến kịch bản OMIFlow, Phân loại (`ADD_CLASSIFY`, `data.ids=["<tên nhãn>"]`, nhãn khai ở "Cấu hình phân loại" → `campaign.classifies[{name}]`; nhập nhãn xong phải rời ô (Tab) thì ô chọn mới thấy). Ngăn Hành động của bot có sẵn "Nút kế tiếp" ngay khi tạo.
