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

