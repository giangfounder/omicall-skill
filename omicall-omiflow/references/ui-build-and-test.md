# OMIFlow — Dựng và kiểm thử flow bằng giao diện (playbook dùng chung)

Dùng khi không gọi được API lưu flow (không có token, MCP chưa cài, hoặc bị chặn đọc cookie): toàn bộ flow được dựng, xuất bản và kiểm thử qua editor trong browser pane. Mọi mục dưới đây đã làm thật trên editor bản 10/2026; nhãn UI giữ nguyên tiếng Việt để tìm bằng `find`.

---

## 1. Biểu mẫu (nguồn lead, trigger `FORM`)

- **OMIFlow → Biểu mẫu → Thêm biểu mẫu** (quota riêng, ví dụ 0/50). Tab *Thông tin*: tên, hoạt động/ngưng, thời gian hiệu lực, ngôn ngữ, phân quyền; tuỳ chọn: thông báo khi có trả lời, chặn trả lời trùng, cho sửa sau khi gửi, **CAPTCHA (bật sẵn)**, mã bảo vệ, liên kết Google Sheet.
- Tab *Thiết kế* → **Thêm trường dữ liệu** → ngăn "Thêm thuộc tính":
  - *Thuộc tính liên kết* → **Khách hàng** (Tên đầy đủ, Số điện thoại, Email, Chức vụ, Địa chỉ, Mô tả…) hoặc **Phiếu ghi**: trường được ghi thẳng vào đối tượng tương ứng.
  - *Thuộc tính tuỳ chỉnh*: hộp ký tự, đoạn văn bản, danh sách, ô chọn, sắp xếp, thời gian. *Khác*: tiêu đề, đoạn văn, đánh giá, hình ảnh, file, quan tâm OA.
  - Mỗi trường: tên trường, gợi ý, giới hạn, bắt buộc, giá trị mặc định, điều kiện hiển thị. Ngăn này tự gợi ý thuộc tính kế tiếp (Tên → SĐT → Email).
- **Lưu lại** chỉ lưu nháp. **Xuất bản** mới tạo link công khai (`form.omicrm.io/<mã>`, có cả link Zalo MiniApp, xem ở tab *Chia sẻ*). Xuất bản = công khai, hỏi user trước.
- **Trigger Biểu mẫu trong flow chỉ liệt kê biểu mẫu đã xuất bản.** Chưa xuất bản → ô chọn trống "Không có dữ liệu".
- Mỗi trường của form thành một biến mã ngẫu nhiên 10 ký tự (nhóm biến *Biểu mẫu*), ngoài ra có biến hệ thống `{{form_name}}`, `{{form_created_date}}`, `{{form_verification_code}}`, `{{form_ip}}`, `utm_*`…
- Trang form công khai đưa giá trị đang nhập lên query string (`?<mã biến>=<giá trị>`): đọc URL là biết mã biến của từng trường.

## 2. Tạo flow và tab Thông tin

- **Danh sách Flow → Thêm mới** (quota hiển thị dạng `2/20`). Tab *Thông tin Flow*: Hoạt động/Ngưng, tên (≤ 256), **thời gian hiệu lực (mặc định hôm nay → +7 ngày)**, mô tả, tag; *Tuỳ chọn*: số lần đối tượng đi qua (**Giới hạn — mặc định 2**, Giới hạn theo nhánh, Không giới hạn; kèm "Thời gian giới hạn"), cách bắt đầu (Không phụ thuộc / Phụ thuộc Flow khác).
- Trạng thái chọn ở form tạo mới có thể không được giữ sau khi lưu/xuất bản: kiểm tra lại cột **Trạng thái** ở danh sách flow ("Đang hoạt động"). Cột **Phiên bản** "-" = chưa xuất bản.
- **Giới hạn số lần đi qua** chống lặp, nhưng cũng chặn kiểm thử lặp lại trên cùng một khách: hết lượt thì trigger im lặng, không báo lỗi.

## 3. Tab Kịch bản: trigger và thêm nút

- Flow trống hiện 7 thẻ trigger: Biểu mẫu (Form), Xảy ra định kỳ, Điều kiện, API, Kích hoạt bằng File Excel, Đối tác, Cuộc gọi đang diễn ra.
- Trigger **Biểu mẫu**: chọn *Hoàn thành biểu mẫu* hoặc *Sửa câu trả lời*, rồi chọn form. Nếu chỉ có một form đã xuất bản, editor có thể tự gắn form đó.
- Trigger **Điều kiện**: danh sách trường hợp bên trái; nhóm so sánh bên phải (Khách hàng, Phiếu ghi, Nhân viên, Cuộc gọi, AI Assistant – Cuộc gọi/Đa kênh, Voice Insights, Chat Insights, Đa kênh, Voucher, AI Chatbot, **Mở rộng**, Tuỳ chỉnh). Thuộc tính kiểu danh sách (ví dụ *Trạng thái khách hàng*) mở hộp chọn **Là / Không là**, VÀ / HOẶC, tick giá trị. Có công tắc "Chạy lại chiến dịch cho đối tượng thoả điều kiện đã tồn tại trước đó" (mặc định tắt).
- **Trigger theo trạng thái (pipeline) chỉ bắt lúc đối tượng chuyển vào trạng thái đó**; sửa thuộc tính khác của đối tượng không làm flow chạy lại (đã thử). Vì vậy đổi trạng thái là một mốc tốt để nối flow trước với flow sau, ví dụ "người duyệt xác nhận".
- Sau khi cấu hình trigger, editor tự bật bảng chọn nút kế tiếp: Logic (Điều kiện, Trì hoãn, Random, Phân tích thông tin), Tương tác (Hành động, Marketing, Cửa sổ tương tác), Trò chuyện (các kênh, bot AI), Khác (Thu thập thông tin, Ghi chú).
- **Nút vừa tạo chưa có mục "Nút kế tiếp"** trong ngăn cấu hình. Đóng ngăn → Lưu lại → mở lại nút (hoặc dùng nút ←/→ trên đầu ngăn để đi sang nút kề) rồi bấm **Bước tiếp theo**.
- Ngăn **Điều kiện**: mục "Nút kế tiếp" **bên phải** thuộc trường hợp đang chọn; mục **bên trái** (dưới danh sách trường hợp) là nhánh mặc định "Bước tiếp theo".
- Kéo cổng nối ra vùng trống chỉ làm trôi canvas; bấm cổng cũng không mở bảng chọn. Đường chắc chắn là ngăn cấu hình → "Bước tiếp theo".
- **Lưu lại / Cập nhật** không ảnh hưởng phiên bản đang chạy. **Xuất bản** tạo phiên bản mới, áp dụng ngay và **đổi id** trong URL `flow/edit/<id>`: luôn mở flow từ danh sách thay vì giữ URL cũ.

## 4. Cấu hình từng loại nút qua UI

### Hành động (ngăn "Hành động", 22 mục)
- **Thêm khách hàng**: *Nhân viên cụ thể* hoặc *Cấu hình phân bổ*; tuỳ chọn ưu tiên nhân viên thực hiện cuộc gọi / tiếp nhận hội thoại; ánh xạ Tên, SĐT, Email từ biến (nhóm *Biểu mẫu*…). SĐT đã tồn tại → lỗi `CONTACT_EXIST`, không tạo trùng.
- **Cập nhật khách hàng**: hai nhóm *Gán mới, thay thế, chèn* và *Gỡ giá trị* (+ *Mở rộng*); ô tìm trong 19 thuộc tính. Mỗi thuộc tính mở một ngăn con:
  - *Nhân viên phụ trách*: Nhân viên cụ thể / Cấu hình phân bổ / Tuỳ chỉnh + **Ghi chú** (thành log chuyển phụ trách) + "Gán liên quan cho nhân viên phụ trách trước đó".
  - *Trạng thái: <bộ trạng thái>*: chọn trạng thái + Ghi chú (thành log chuyển trạng thái).
  - Gán phụ trách cho đúng người đang phụ trách → `NO_CHANGE` (chấm đỏ) nhưng luồng vẫn chạy tiếp.
  - Với trigger Biểu mẫu, "Cập nhật khách hàng" áp lên khách đã có theo SĐT ngay cả khi "Thêm khách hàng" báo `CONTACT_EXIST`. Muốn cập nhật tên/email của khách cũ thì phải thêm chính các thuộc tính đó vào bước cập nhật. Cẩn thận ghi đè bằng giá trị rỗng từ trường không bắt buộc.
- **Tạo thông báo**: Tiêu đề, Nội dung (trình soạn thảo giàu định dạng), Đọc nội dung thông báo, *Gửi đến nhân viên* (mặc định là tài khoản đang đăng nhập), Nền tảng Web / Mobile / Custom App.
- Một nút Hành động chứa nhiều hành động chạy tuần tự (Thêm KH → Cập nhật KH → Thông báo…), giúp tiết kiệm quota nút.

### Biến trong ô nhập
- Thanh chip biến dưới ngăn (Khách hàng, Phiếu ghi, Dữ liệu thu thập, Biểu mẫu, Cuộc gọi, AI Assistant, Nhân viên, Khác, Biến liên kết tuỳ chỉnh…) chèn `{{mã}}` vào **ô nhập thường được focus gần nhất**. Với trình soạn thảo nội dung thông báo, chip có thể chèn nhầm sang ô Tiêu đề, nên gõ tay mã biến.
- Biến hệ thống gõ tay được: `{{full_name}}`, `{{phone_number}}`… Biến form là mã ngẫu nhiên dễ lẫn `I`/`l`: lấy mã chính xác bằng JS (`input.value` sau khi chèn chip) hoặc từ query string của trang form. Biến đúng hiển thị thành tên thuộc tính trên thẻ nút (ví dụ "Tên đầy đủ"); biến sai vẫn hiện `{{...}}` thô.

### Trì hoãn
- Mặc định "Sau khoảng thời gian = 1 Ngày". Đơn vị đổi bằng mũi tên ◂ ▸ quay vòng (Ngày → Giờ → Phút…). Sau khi gõ giá trị, nút ✕ xuất hiện làm lệch vị trí mũi tên, nên chụp lại trước khi bấm.
- Tuỳ chọn: Thời gian cụ thể, Đặt khung giờ tiếp tục, Hoặc điều kiện đến trước.

### Điều kiện SLA: "Kiểm tra tương tác khách hàng" (nhóm Mở rộng)
- *Tương tác mới* / *Không có tương tác* · loại: Cuộc gọi, SMS, ZBS, Email Marketing, Ghi chú, Chuyển trạng thái, Log, Phiếu ghi, Đánh giá · **Người tương tác (bắt buộc)**: Nhân viên (chọn người hoặc chọn tất cả), Nhóm, Nhân viên phụ trách KH, Nhân viên liên quan, Hệ thống · "Thời điểm tương tác gần nhất" N phút/giờ.
- Cửa sổ thời gian tính lùi từ lúc nút chạy. Vì vậy với nút Trì hoãn đặt trước, cửa sổ = khoảng chờ cộng dồn kể từ mốc giao việc.
- Chip "Nhân viên phụ trách KH" để trống bị báo "Vui lòng điền đầy đủ thông tin" → dùng chip *Nhân viên* rồi tick người. Không tick *Hệ thống* nếu chính flow tự ghi log/ghi chú, vì log đó có thể bị tính là tương tác.
- Thay cho mọi cách tự đếm (chụp `interactive_call` vào biến rồi so sánh, so `last_call_transaction_time` với thời điểm giao…).

### Thuộc tính khách hàng dùng được trong điều kiện (49 mục, mã hiển thị trong ô chọn)
`full_name`, `phone_number`, `mail`, `contact_tags`, `contact_categories`, `user_owner_id`, `user_owner_email`, `transfer_agent_log_note`, `last_log_note`, `change_status_log_note`, `contact_related_employee`, `interactive_call` / `_sms` / `_zns` / `_email` / `_note` / `_ticket` / `_diary` / `_change_status` / `_evaluation`, `total_interactive`, `closest_interaction_time`, `last_call_transaction_time`, `contact_created_date`, `contact_created_by`, `contact_last_updated_date`, `last_transfer_agent_time`, `last_transfer_agent_by`, `win_lose`, `opportunity_expired`, trạng thái pipeline… Kiểu thời gian so với một mốc HH:mm dd/MM/yyyy cố định, không có "trong N phút qua" → dùng điều kiện Mở rộng ở trên.

## 5. Kiểm thử

### Đọc kết quả
- Tab **Lịch sử** của flow: mỗi lượt một dòng (Credit, ngày tạo, phiên bản, đối tượng liên quan, trạng thái *Hoàn thành* / *Đang trì hoãn* + giờ chạy tiếp, thời lượng). Bấm vào ô ngày tạo để mở **hành trình**: từng nút có giờ chạy, số lần, mỗi hành động một chấm xanh/đỏ. Rê chuột lên chấm đỏ để xem mã lỗi, hoặc đọc phần tử tooltip bằng JS.
- Mã lỗi đã gặp: `NO_CHANGE` (gán giá trị trùng hiện tại, vô hại), `CONTACT_EXIST` (thêm khách đã có, vô hại).
- Kiểm chứng chéo: **log trong hồ sơ khách** ("OMIFlow | <tên flow> đã gán trạng thái…", "…đã thêm khách hàng và gán cho …") và **số trên chuông thông báo** (tăng 1 mỗi thông báo flow gửi tới tài khoản đang xem).
- Khi tab Lịch sử bị tooltip che, bấm bằng JS vào phần tử có text "Lịch sử".

### Thời gian chờ
- Nút "Tiếp tục kịch bản" (trên dòng hoặc menu hàng loạt ⋯: Tiếp tục / Huỷ kịch bản / Xuất Excel / Chạy lại nút thất bại / Xoá) có hộp xác nhận ghi "các hành động sau đó sẽ được không thực thi", nghĩa chưa rõ → không dùng để test.
- Hai cách tin cậy: (a) chờ thời gian thật bằng Bash `sleep <giây>` chạy nền, tới mốc thì đọc Lịch sử; (b) tạm đặt Trì hoãn = 1 phút, test, rồi **đặt lại giá trị thật và xuất bản**. Ghi việc phải trả lại vào báo cáo giao.

### Kịch bản nên test (ngoài luồng chính)
1. Đối tượng mới đi hết luồng chính.
2. Đối tượng đã tồn tại kích hoạt lại trigger (gửi lại form, cập nhật lại): có tạo trùng không, có cập nhật đủ thuộc tính không.
3. Sửa một thuộc tính không liên quan của đối tượng đang ở trạng thái trigger: flow có chạy lại không.
4. Từng nhánh của mỗi điều kiện. Nhánh cần sự kiện thật (cuộc gọi) chỉ test khi user đồng ý gọi.
5. Đếm lượt còn lại theo giới hạn số lần đi qua. Hết lượt → dùng SĐT khác, nhờ user xoá đối tượng test, hoặc nới giới hạn.

### Trước mỗi lần test
- Mở flow từ danh sách, đọc **Phiên bản** và cấu hình hiện tại: flow có thể đã bị người hoặc phiên khác sửa (đổi trì hoãn, giới hạn…).
- Dữ liệu test dùng tên dễ nhận ("Test …") và SĐT user cung cấp. Xoá dữ liệu test là việc của user (agent không xoá vĩnh viễn).

## 6. Mẹo browser pane khi dựng bằng UI
- Ảnh chụp trễ 1–2 thao tác và khung pane đổi kích thước liên tục: xác nhận bằng `get_page_text` hoặc JS (`input.value`, `innerText`), bấm theo `ref` lấy từ `find` thay vì toạ độ.
- Pane đổi kích thước thì toạ độ cũ bị từ chối ("page, zoom or size has changed") → chụp lại hoặc dùng `ref`.
- Phiên đăng nhập hết hạn sau một đêm: mở trang đăng nhập để user tự đăng nhập lại.
- Đọc cookie lấy token (JS hay CDP) bị bộ lọc an toàn chặn: **không lách**, kể cả bằng hàm `fetch` trong trang tự đọc cookie (mục 7, *Giới hạn công cụ*). Token chỉ lấy qua MCP OMI hoặc `OMI_TOKEN_FILE` do user đặt (`scripts/omi_preflight.py`); không có thì dựng bằng UI. Trang editor tải lại toàn bộ khi đổi URL → hàm JS đọc DOM đã khai báo phải khai báo lại.
- **Biến trigger API**: gõ tay `{{tên biến}}` không khớp (mã là 10 ký tự ngẫu nhiên, ví dụ `{{Pd43rT7iqX}}`) → cảnh báo "N biến liên kết có vấn đề"; tên trùng thuộc tính hệ thống (`note`, `phone`…) còn bị gán nhầm loại. Lấy mã ở `multi_variables[].field_code` (GET) rồi gõ mã.
- Khai báo biến trigger API: gõ tên biến thì ô "Điều kiện truy vấn" tự điền cùng khoá; gõ thêm vào ô truy vấn sẽ bị lặp ("routeroute").
- **URL webhook có thể đổi** ở mỗi lần lưu còn hiện hộp "Thông tin về URL" (phải tick "Tôi xác nhận đã lưu lại các URL" rồi Cập nhật): luôn lấy URL cuối cùng từ GET `kick_off.id`, không lấy từ ảnh chụp đầu tiên.
- **"Bước tiếp theo" trong ngăn chỉ tạo nút mới**, không chọn được nút có sẵn. Nối hai nút có sẵn: `left_click_drag` từ chấm nguồn tới chấm đích khi cả hai cùng hiện trên màn hình (mục 7, *Thao tác canvas đã kiểm chứng*); kéo cổng ra vùng trống chỉ làm trôi canvas, giả lập PointerEvent bằng JS thường không ăn. Không nối được bằng chuột (hoặc cần chèn nút vào giữa): dựng các nút trên UI (để có schema), rồi sửa `next_nodes` + `edges.connections` trong JSON và lưu bằng `save_draft_v2` (`api-reference.md`), tải lại editor để đối chiếu.
- Bấm ra ngoài hộp xác nhận có thể mở nhầm ngăn khác (ví dụ ngăn Ghi chú) và trình duyệt có thể tự điền ô; đọc lại nội dung trước khi lưu.
- **Ô nhập trong drawer nối thêm thay vì thay thế**: Ctrl+A trước khi gõ; body JSON editor tự bọc `{}`. Không dùng Escape trong drawer.
- **Browser pane không bắt XHR khác domain** trong `read_network_requests`; dùng `performance.getEntriesByType('resource')` để tìm endpoint. Pane hẹp làm canvas tràn ngang → ưu tiên API thay vì bấm UI.


---

## 7. AI điền CRM sau cuộc gọi: bóc trường bằng LLM rồi gán thuộc tính (dựng thật qua UI, 10/2026)

**Mẫu**: trigger Điều kiện → Cuộc gọi → *Trạng thái cuộc gọi* = Trả lời (không dùng "Cuộc gọi được cập nhật", đó là sự kiện cập nhật cửa sổ/lịch sử, không phải kết thúc) → Trì hoãn vài phút (AI Assistant ghi kết quả trễ) → các nút LLM → Cập nhật khách hàng. Nguồn dữ liệu là `{{ca_ai_assistant}}`: một trường văn bản mô tả mọi thuộc tính theo mẫu cấu hình ở AI Assistant. Cần AI Assistant của cuộc gọi đó đã bật, nếu không biến rỗng.

- **Yêu cầu cho AI Assistant**: Cấu hình > AI > AI Assistant (`/config/ai/call-assistant/config-criteria/edit/<id>`), ô "Hướng dẫn các bước tổng hợp". Mẫu mặc định theo cú pháp `- Tên trường: (mô tả)`, mỗi trường một dòng; giữ nguyên các dòng cũ, thêm dòng mới cùng cú pháp. Trường kiểu danh sách: ghi rõ "Chỉ ghi MỘT trong các giá trị: …, không có thì ghi: Không xác định". Đây là cấu hình dùng chung cho cả tổng đài: ghi lại nội dung gốc trước khi sửa để hoàn tác.
- **Biến LLM**: nút Hành động → *Biến liên kết tuỳ chỉnh* có 5 tab (API, Random, Phép toán, Thư mời, **LLM**). Tab LLM: tên biến + ô Giá trị (prompt) + model. Mỗi nút Hành động chỉ thêm được **một** hành động Biến liên kết tuỳ chỉnh (mục đã dùng biến mất khỏi danh sách "Thêm hành động") → mỗi trường một nút, nối chuỗi.
- **Biến chỉ hiện sau khi Lưu**: chip "Biến liên kết tuỳ chỉnh" ở nút sau chỉ liệt kê biến đã lưu; trong nút Điều kiện còn phải **tải lại trang** mới thấy. Chọn biến từ chip (chèn đúng mã 10 ký tự), không gõ tên.
- **Kiểu thuộc tính khách quyết định cách gán**: thuộc tính kiểu *danh sách* (biểu tượng danh sách) **không nhận biến**, chỉ chọn một giá trị cố định; thuộc tính kiểu văn bản/văn bản giàu định dạng nhận biến; *Số điện thoại* là "Thêm giá trị mới" (có thể trùng số đã có). Kiểm từng thuộc tính trước khi thiết kế.
- **Trường danh sách → rẽ nhánh theo giá trị**: LLM bị ép trả đúng nguyên văn một giá trị của danh sách; nút Điều kiện mỗi giá trị một trường hợp (biến, CONTAIN, giá trị); mỗi trường hợp có "Nút kế tiếp" → Hành động → Cập nhật khách hàng gán đúng giá trị. Cẩn thận chuỗi con ("Gói A" nằm trong "Gói A Plus": dùng `=` cho chuỗi ngắn hơn). **Các nhánh không gộp lại được** nên mỗi trường danh sách một flow riêng (cùng trigger, LLM chạy lại), mỗi flow = 4 + số giá trị nút. Biến không truyền giữa các flow.
- **Cú pháp thao tác trong ngăn**: nút Điều kiện: trường hợp mới bằng "Thêm trường hợp" (nút dịch xuống ~47px mỗi trường hợp), chọn biến, toán tử, ô giá trị; **phải chờ ~1s sau khi bấm ô rồi mới gõ**, gõ ngay thì giá trị rỗng (`=""`) mà không báo lỗi. Đóng ngăn con bằng nút ✕ ngoài cùng; ngăn Hành động có thuộc tính rỗng thì không đóng được ("Vui lòng điền đầy đủ thông tin").
- **Duyệt ngăn**: ✕ đóng ngăn hiện tại và quay về ngăn node trước (xếp chồng); nút ←/→ đầu ngăn đi sang node kề; node vừa tạo chỉ có "Bước tiếp theo" sau khi đóng rồi mở lại qua →.

### Thao tác canvas đã kiểm chứng
- Bấm vào thân node mở ngăn, không chỉ chọn. Phím tắt: Ctrl+C sao chép node, Delete xoá node.
- Xoá node bằng JS: `document.querySelectorAll('.react-flow__node')` → tìm theo text → `button[aria-label="Xóa node"]` `.click()`. Xoá node **giữa chuỗi làm đứt cạnh**.
- **Nối lại cạnh bằng chuột hoạt động**: `left_click_drag` từ chấm nguồn (vòng tròn cuối node trước) tới chấm đích (chấm đầu node sau) khi hai node cùng thấy trên màn hình. Lưu lại rồi mở lại để kiểm.
- Xoá ngày hiệu lực khi tạo flow: rê chuột lên ô ngày thì hiện nút ✕ ở từng ô; bấm lần lượt.

### Chạy song song bằng subagent (fork)
Mỗi subagent tự tạo **tab riêng** (`tabs_create`, rồi truyền `tabId` ở mọi lệnh), không dùng tab của agent chính; mỗi flow một subagent, không hai bên cùng chạm một flow. Dặn trước: chờ trước khi gõ, kiểm từng trường hợp sau khi lưu, không xuất bản. Subagent báo thiếu kiểm sau tải lại thì agent chính tự mở lại kiểm. Mẫu giao việc đầy đủ (điều CẤM, ghi manifest): `omi-mcp.md` mục *Mẫu giao việc cho subagent*; mỗi subagent tự chạy `scripts/validate_flow.py` trên bản GET sau khi lưu.

### Giới hạn công cụ
- `browser_batch` tối đa 25 thao tác; ảnh chụp trễ 1–2 thao tác (dùng `wait` rồi chụp lại, hoặc `zoom` vùng nhỏ để đọc tóm tắt điều kiện).
- Đọc cookie token qua JS bị bộ lọc an toàn chặn: không vòng qua, dựng bằng UI.

---

## 8. Gỡ lỗi biến liên kết và sửa nút qua UI (10/2026)

- **Tìm mã biến nằm ở nút nào**: bảng "biến liên kết có vấn đề" không điều hướng. Mở từng nút nghi ngờ rồi quét bằng JS: `input`/`textarea` (`.value`) và nội dung iframe TinyMCE của ô Mô tả, regex `/\{\{[A-Za-z0-9_]+\}\}/g`. Mô tả phiếu thường chứa nhiều mã nhất; ô tên phiếu và các ô thuộc tính bắt buộc của phiếu cũng có thể chứa mã.
- **Sửa mô tả (TinyMCE)**: lấy `ed = tinymce.get(iframe.id.replace('_ifr',''))`, `getContent()` → parse bằng `DOMParser`, xoá nguyên dòng nhãn+giá trị (div cha có đúng 2 con), `ed.setContent(html); ed.fire('change'); ed.undoManager.add()`. Ô tên phiếu thì chọn ô, Ctrl+A, gõ lại. Sau Cập nhật phải tải lại trang và quét lại để chắc đã lưu.
- **Đối chiếu trước khi xoá**: đọc bộ chọn biến (nhóm Cửa sổ tương tác, Biến liên kết tuỳ chỉnh) để biết mã nào hợp lệ; chỉ gỡ mã không có ở đâu. Thay mã mất bằng biến tương đương nếu có (ví dụ tên bệnh nhân), nếu không thì bỏ cả dòng nhãn, đừng để dòng rỗng. Sửa thử mà chưa chắc: tải lại trang (`navigate` với `force`) là bỏ thay đổi chưa lưu.
- **Ref cũ bị stale** sau khi canvas vẽ lại hoặc tải lại: bấm ref cũ có thể trúng nhầm nút khác. Luôn `find` lại ngay trước mỗi lần bấm, và kiểm tiêu đề ngăn vừa mở đúng nút chưa.
- **Nút ✕ đóng ngăn ở góc trên trái**: nếu ngăn đã đóng thì cú bấm đó trúng logo và rời khỏi editor. Chụp màn hình xác nhận ngăn đang mở trước khi bấm.
- **Kiểm API ngoài từ ngoài giao diện**: gọi thử bằng curl với đúng header (tên header phân biệt theo từng API; thông báo "thiếu mã truy cập" hay "API Key trống" cho biết sai tên hay thiếu header). Thông báo `Fetch API failed` khi bấm thử trong nút API chỉ nói OMI không nhận được response dùng được (Cần xác nhận nguyên nhân: 4xx/5xx, thiếu header, bị chặn IP).
- **Danh sách bên ngoài chưa dùng được dạng dropdown** (xem Gotchas trong `SKILL.md`): chỉ đề xuất đường vòng, ghi "Cần xác nhận" cho cú pháp mảng.
