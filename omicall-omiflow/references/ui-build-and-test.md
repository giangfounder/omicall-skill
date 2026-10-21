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
- Đọc cookie lấy token có thể bị bộ lọc an toàn chặn: không tìm cách lách, chuyển sang dựng bằng UI.
