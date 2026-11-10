# OMIFlow — Dựng và kiểm thử flow bằng giao diện (playbook dùng chung)

Dùng khi không gọi được API lưu flow (không có token, MCP chưa cài, hoặc bị chặn đọc cookie): toàn bộ flow được dựng, lưu nháp (**Lưu lại / Cập nhật**) và kiểm thử qua editor trong browser pane. Agent không bấm **Xuất bản**: đó là việc của user, hoặc agent chỉ bấm khi user đã đồng ý rõ cho đúng flow đó (`SKILL.md` Rule 3). Mọi mục dưới đây đã làm thật trên editor (10/2026, 11/2026 ghi theo từng dòng); nhãn UI giữ nguyên tiếng Việt để tìm bằng `find`.

Mục lục: 1. Tạo flow và Thông tin Flow · 2. Trigger (kể cả Biểu mẫu) · 3. Cấu hình từng loại nút · 4. AI điền CRM sau cuộc gọi · 5. Canvas: nối, xoá, sửa cạnh · 6. Lưu, Xuất bản và id · 7. Gỡ lỗi biến liên kết · 8. Kiểm thử · 9. Mẹo browser pane và chạy song song.

---

## 1. Tạo flow và Thông tin Flow

- **Danh sách Flow → Thêm mới** (quota hiển thị dạng `2/20`). Tab *Thông tin Flow*: Hoạt động/Ngưng, tên (≤ 256), **thời gian hiệu lực (giao diện mặc định hôm nay → +7 ngày)**, mô tả, tag; *Tuỳ chọn*: số lần đối tượng đi qua (**Giới hạn — giao diện mặc định 2**, Giới hạn theo nhánh, Không giới hạn — nằm cạnh "Giới hạn"; kèm "Thời gian giới hạn"), cách bắt đầu (Không phụ thuộc / Phụ thuộc Flow khác).
- **Mặc định giao diện ngược quy ước skill**: quy ước là Hoạt động, Không giới hạn lượt, không hạn ngày (X11 trong `validate_flow.py`). Đổi ngay ở form tạo mới; giữ giới hạn hay hạn ngày là lệch quy ước mặc định, chỉ giữ nếu user yêu cầu.
- **Xoá ngày hiệu lực**: rê chuột lên ô ngày thì hiện nút ✕ ở từng ô; bấm lần lượt (✔ UI 11/2026: có lúc một ✕ xoá cả khoảng). Lịch bật ra thì Escape.
- **Giới hạn số lần đi qua** chống lặp, nhưng cũng chặn kiểm thử lặp lại trên cùng một khách: hết lượt thì trigger im lặng, không báo lỗi.
- Trạng thái chọn ở form tạo mới có thể không được giữ sau khi lưu/xuất bản: kiểm cột **Trạng thái** ở danh sách flow ("Đang hoạt động"). Cột **Phiên bản** "-" = chưa xuất bản.
- **Thông tin Flow** của flow đã có (trạng thái, thời gian hiệu lực, số lần đi qua, cách bắt đầu) mở bằng **biểu tượng cạnh tên flow** ở đầu trang editor, không nằm trong menu ⋮ (menu ⋮ chỉ có Căn chỉnh vị trí, Trả về phiên bản trước, Chia sẻ, Training) (✔ UI 11/2026).
- **Bỏ hạn hiệu lực flow đã xuất bản** (✔ UI 11/2026): rê chuột lên ô ngày → bấm ✕ ở ô bắt đầu, rê lại → ✕ ở ô kết thúc → **Cập nhật** (chuyển "Đã lưu"); bản đang chạy chỉ đổi khi user bấm **Xuất bản** rồi xác nhận (agent chỉ bấm khi user đã đồng ý rõ cho flow đó). GET kiểm `start_date`/`end_date` = null.
- **Vỏ flow tối thiểu, lần "Lưu lại" đầu**: `api-reference.md` mục *Vỏ flow tối thiểu và lần "Lưu lại" đầu* (lưu lần đầu đổi URL sang `/flow/edit/<id>`, có `_id` nháp; ✔ UI 11/2026 vỏ gồm trigger + vài nút lưu được ngay, kể cả khi nhánh mặc định của nút Điều kiện chưa nối).
- **Flow phụ thuộc vẫn cần thẻ "Điều kiện bắt đầu"** (✔ UI 11/2026): chọn "Phụ thuộc Flow khác" trước khi có trigger thì canvas trống, không hiện thẻ trigger, lưu báo "Kịch bản không hợp lệ". Đúng thứ tự: để "Không phụ thuộc" → chọn trigger (vd. Điều kiện, Đa kênh "Kênh = LiveTalk") → dựng chuỗi nút từ trigger → lưu → mới đổi sang "Phụ thuộc Flow khác" → lưu. Chuỗi phải kết thúc bằng nút Hành động.

## 2. Trigger

- Flow trống hiện 7 thẻ trigger: Biểu mẫu (Form), Xảy ra định kỳ, Điều kiện, API, Kích hoạt bằng File Excel, Đối tác, Cuộc gọi đang diễn ra.
- Sau khi cấu hình trigger, editor tự bật bảng chọn nút kế tiếp: Logic (Điều kiện, Trì hoãn, Random, Phân tích thông tin), Tương tác (Hành động, Marketing, Cửa sổ tương tác), Trò chuyện (các kênh, bot AI), Khác (Thu thập thông tin, Ghi chú).

### Trigger Điều kiện
- Danh sách trường hợp bên trái; nhóm so sánh bên phải (Khách hàng, Phiếu ghi, Nhân viên, Cuộc gọi, AI Assistant – Cuộc gọi/Đa kênh, Voice Insights, Chat Insights, Đa kênh, Voucher, AI Chatbot, **Mở rộng**, Tuỳ chỉnh). Thuộc tính kiểu danh sách (ví dụ *Trạng thái khách hàng*) mở hộp chọn **Là / Không là**, VÀ / HOẶC, tick giá trị. Có công tắc "Chạy lại chiến dịch cho đối tượng thoả điều kiện đã tồn tại trước đó" (mặc định tắt).
- **Trigger theo trạng thái (pipeline) chỉ bắt lúc đối tượng chuyển vào trạng thái đó**; sửa thuộc tính khác của đối tượng không làm flow chạy lại (đã thử). Đổi trạng thái là mốc tốt để nối flow trước với flow sau, ví dụ "người duyệt xác nhận".
- **Trạng thái nhiều cấp** (✔ UI 11/2026): Khách hàng → gõ tên bộ trạng thái vào ô tìm → bấm chip → hộp chọn có mũi tên ▸ mở cấp 2; tick bằng click `ref`. "Thêm trường hợp" tạo trường hợp mới nhưng **chip trạng thái đã có sẵn và rỗng**, chỉ việc mở chip chọn giá trị (tìm lại sẽ báo "Không có dữ liệu"). Mỗi trường hợp có "Nút kế tiếp" riêng.

### Trigger API
- **Biến trigger API**: gõ tay `{{tên biến}}` không khớp (mã là 10 ký tự ngẫu nhiên, ví dụ `{{Pd43rT7iqX}}`) → cảnh báo "N biến liên kết có vấn đề"; tên trùng thuộc tính hệ thống (`note`, `phone`…) còn bị gán nhầm loại. Lấy mã ở `multi_variables[].field_code` (GET) rồi gõ mã.
- Khai báo biến: gõ tên biến thì ô "Điều kiện truy vấn" tự điền cùng khoá; gõ thêm vào ô truy vấn sẽ bị lặp ("routeroute"). Mỗi biến một hàng "Value" = tên trường trong body.
- **Method**: mặc định GET; đổi sang POST khi bên gọi gửi body JSON.
- **Cách lấy dữ liệu**: **"Truy vấn từ Body"** (mặc định) tự tách body và gán vào biến theo tên trường; **"Toàn bộ Body"** đưa cả body vào một biến JSON.
- **Kết quả trả về** (`response_config`): mặc định `{"message":"success","status_code":9999}`, là body cố định; trả dữ liệu tra cứu dùng `SEND_RESPONSE_WEBHOOK_API` (`webhook-examples.md`). Ghi chép cũ ở skill chatbot cho rằng chèn được `{{...}}` vào ô này: Cần xác nhận.
- Hộp "Thông tin về URL" khi lưu: tick "Tôi xác nhận đã lưu lại các URL" rồi Cập nhật. URL webhook → `api-reference.md` mục *Ba loại id và URL webhook*.
- Ngăn của trigger API không có mục "Nút kế tiếp" → đổi nút đứng sau trigger phải sửa cạnh trên canvas (mục 5).

### Biểu mẫu (nguồn lead, trigger `FORM`)
- **OMIFlow → Biểu mẫu → Thêm biểu mẫu** (quota riêng, ví dụ 0/50). Tab *Thông tin*: tên, hoạt động/ngưng, thời gian hiệu lực, ngôn ngữ, phân quyền; tuỳ chọn: thông báo khi có trả lời, chặn trả lời trùng, cho sửa sau khi gửi, **CAPTCHA (bật sẵn)**, mã bảo vệ, liên kết Google Sheet.
- Tab *Thiết kế* → **Thêm trường dữ liệu** → ngăn "Thêm thuộc tính":
  - *Thuộc tính liên kết* → **Khách hàng** (Tên đầy đủ, Số điện thoại, Email, Chức vụ, Địa chỉ, Mô tả…) hoặc **Phiếu ghi**: trường được ghi thẳng vào đối tượng tương ứng.
  - *Thuộc tính tuỳ chỉnh*: hộp ký tự, đoạn văn bản, danh sách, ô chọn, sắp xếp, thời gian. *Khác*: tiêu đề, đoạn văn, đánh giá, hình ảnh, file, quan tâm OA.
  - Mỗi trường: tên trường, gợi ý, giới hạn, bắt buộc, giá trị mặc định, điều kiện hiển thị. Ngăn này tự gợi ý thuộc tính kế tiếp (Tên → SĐT → Email).
- **Lưu lại** chỉ lưu nháp. **Xuất bản** mới tạo link công khai (`form.omicrm.io/<mã>`, có cả link Zalo MiniApp, xem ở tab *Chia sẻ*). Xuất bản = công khai, hỏi user trước.
- **Trigger Biểu mẫu trong flow chỉ liệt kê biểu mẫu đã xuất bản.** Chưa xuất bản → ô chọn trống "Không có dữ liệu". Chọn *Hoàn thành biểu mẫu* hoặc *Sửa câu trả lời*, rồi chọn form; chỉ có một form đã xuất bản thì editor có thể tự gắn form đó.
- Mỗi trường của form thành một biến mã ngẫu nhiên 10 ký tự (nhóm biến *Biểu mẫu*), ngoài ra có biến hệ thống `{{form_name}}`, `{{form_created_date}}`, `{{form_verification_code}}`, `{{form_ip}}`, `utm_*`…
- Trang form công khai đưa giá trị đang nhập lên query string (`?<mã biến>=<giá trị>`): đọc URL là biết mã biến của từng trường.

## 3. Cấu hình từng loại nút

### Ngăn cấu hình: mở, duyệt, nút kế tiếp
- **Nút vừa tạo chưa có mục "Nút kế tiếp"** (kể cả Trì hoãn). Đóng ngăn → Lưu lại → mở lại nút từ canvas (hoặc nút ←/→ trên đầu ngăn để đi sang nút kề) rồi bấm **Bước tiếp theo**.
- **"Bước tiếp theo" trong ngăn chỉ tạo nút mới** đã nối sẵn, không chọn được nút có sẵn (nối nút có sẵn: mục 5).
- Ngăn **Điều kiện**: mục "Nút kế tiếp" **bên phải** thuộc trường hợp đang chọn; mục **bên trái** (dưới danh sách trường hợp) là nhánh mặc định "Bước tiếp theo".
- **Duyệt ngăn**: ✕ đóng ngăn hiện tại và quay về ngăn node trước (xếp chồng); ←/→ đầu ngăn đi sang node kề.
- **Ô nhập trong drawer nối thêm thay vì thay thế**: Ctrl+A trước khi gõ; body JSON editor tự bọc `{}`. Không dùng Escape trong drawer.
- **Phải chờ ~1s sau khi bấm ô rồi mới gõ**; gõ ngay thì giá trị rỗng (`=""`) mà không báo lỗi. Đóng ngăn con bằng nút ✕ ngoài cùng; ngăn Hành động có thuộc tính rỗng thì không đóng được ("Vui lòng điền đầy đủ thông tin").

### Hành động (ngăn "Hành động", 22 mục)
- **Thêm khách hàng**: *Nhân viên cụ thể* hoặc *Cấu hình phân bổ*; hai công tắc **Ưu tiên nhân viên thực hiện cuộc gọi** / **Ưu tiên nhân viên tiếp nhận cuộc trò chuyện** (ưu tiên giao cho người đó khi khớp); ánh xạ Tên, SĐT, Email từ biến (nhóm *Biểu mẫu*…). SĐT đã tồn tại → lỗi `CONTACT_EXIST`, không tạo trùng.
- **Cập nhật khách hàng**: hai nhóm *Gán mới, thay thế, chèn* và *Gỡ giá trị* (+ *Mở rộng*); ô tìm trong 19 thuộc tính. Mỗi thuộc tính mở một ngăn con:
  - *Nhân viên phụ trách*: Nhân viên cụ thể / Cấu hình phân bổ / Tuỳ chỉnh + **Ghi chú** (thành log chuyển phụ trách) + "Gán liên quan cho nhân viên phụ trách trước đó".
  - *Trạng thái: <bộ trạng thái>*: chọn trạng thái + Ghi chú (thành log chuyển trạng thái).
  - Gán phụ trách cho đúng người đang phụ trách → `NO_CHANGE` (chấm đỏ) nhưng luồng vẫn chạy tiếp.
  - Với trigger Biểu mẫu, "Cập nhật khách hàng" áp lên khách đã có theo SĐT ngay cả khi "Thêm khách hàng" báo `CONTACT_EXIST`. Muốn cập nhật tên/email của khách cũ thì phải thêm chính các thuộc tính đó vào bước cập nhật. Cẩn thận ghi đè bằng giá trị rỗng từ trường không bắt buộc.
- **Thu hồi lead** (✔ UI 11/2026) = Cập nhật khách hàng → Gán mới → Nhân viên phụ trách → Nhân viên cụ thể + Ghi chú (`ASSIGN_USER_OWNER_ID`, `transfer_agent_note`).
- **Tạo thông báo**: Tiêu đề, Nội dung (trình soạn thảo giàu định dạng), Đọc nội dung thông báo, *Gửi đến nhân viên* (mặc định là tài khoản đang đăng nhập), Nền tảng Web / Mobile / Custom App. "Gửi đến nhân viên" → "+" → chọn loại người nhận; có **Nhân viên phụ trách khách hàng** (JSON runtime `send_to_user_owner_of_contact:true`, bản editor `noticeCustomer:true`; ✔ UI 11/2026). Bỏ chọn "Nhân viên" cụ thể nếu muốn gửi động theo người phụ trách.
- Một nút Hành động chứa nhiều hành động chạy tuần tự (Thêm KH → Cập nhật KH → Thông báo…), giúp tiết kiệm quota nút.
- **Trạng thái hành động** (dưới "Danh sách hành động"): thêm nhánh riêng cho thành công / thất bại của hành động (`success_next_nodes` / `fail_next_nodes`, `api-reference.md` bảng DUAL); bỏ trống thì đi tiếp qua "Bước tiếp theo". Có nhánh Thất bại thì dùng nó thay cho `DELAY` + `CONDITION` kiểm trạng thái.
- Thứ tự ghi dữ liệu trước, gửi tin sau: `SKILL.md` Gotchas.

### Biến trong ô nhập
- Thanh chip biến dưới ngăn (Khách hàng, Phiếu ghi, Dữ liệu thu thập, Biểu mẫu, Cuộc gọi, AI Assistant, Nhân viên, Khác, Biến liên kết tuỳ chỉnh…) chèn `{{mã}}` vào **ô nhập thường được focus gần nhất**. Với trình soạn thảo nội dung thông báo, chip có thể chèn nhầm sang ô Tiêu đề, nên gõ tay mã biến. Chọn ô thuộc tính phiếu trước rồi mới mở chip để biến chèn đúng ô.
- Biến hệ thống gõ tay được: `{{full_name}}`, `{{phone_number}}`… Biến form là mã ngẫu nhiên dễ lẫn `I`/`l`: lấy mã chính xác bằng JS (`input.value` sau khi chèn chip) hoặc từ query string của trang form. Biến đúng hiển thị thành tên thuộc tính trên thẻ nút (ví dụ "Tên đầy đủ"); biến sai vẫn hiện `{{...}}` thô.
- **Bộ chọn "Biến liên kết tuỳ chỉnh"** (✔ UI 11/2026): ô tìm kiếm **không** tìm được biến trigger webhook theo tên trường (gõ tên → "Không có dữ liệu") dù tiêu đề ghi "Tìm kiếm | N thuộc tính". Xoá từ khoá rồi **cuộn danh sách** và bấm biến; mỗi dòng hiện tên trường và mã `{{xxxxxxxxxx}}`.
- Ngăn mở từ "Bước tiếp theo" của nút khác có danh sách "Biến liên kết tuỳ chỉnh" rỗng → gõ tay `{{mã}}` hoặc mở nút từ canvas (`node-condition.md` mục 2.5).

### Trì hoãn
- Mặc định "Sau khoảng thời gian = 1 Ngày". Đơn vị đổi bằng mũi tên ◂ ▸ quay vòng. Thứ tự đã ghi khác nhau giữa hai lần dựng (10/2026: Ngày → Giờ → Phút…; 11/2026: Ngày → Giây → Phút → Giờ…) → **luôn đọc lại đơn vị bằng chữ sau mỗi lần bấm**. Sau khi gõ giá trị, nút ✕ xuất hiện làm lệch vị trí mũi tên: `find` lại mũi tên rồi bấm theo ref (không bấm theo toạ độ cũ). Nhanh hơn: đặt khoảng chờ qua API (`flow_outline` + `omi_save`).
- Tuỳ chọn: Thời gian cụ thể, Đặt khung giờ tiếp tục, Hoặc điều kiện đến trước.

### Điều kiện
- **Trường hợp mới** bằng "Thêm trường hợp" (nút dịch xuống ~47px mỗi trường hợp); chọn biến, toán tử, ô giá trị (chờ ~1s rồi mới gõ).
- **Khung giờ**: không dùng được với "Điều kiện HOẶC" (báo "Điều kiện Khung giờ không hoạt động khi áp dụng điều kiện HOẶC", không cho đóng ngăn) và phải đi cùng ≥1 điều kiện khác (`node-condition.md` mục 2.1). **Đóng ngăn con "Khung giờ" bằng cách bấm vùng mờ** có thể bật ra một ngăn "Điều kiện so sánh" rỗng; bấm vùng mờ sát mép trái (x≈30–120) lần nữa để đóng, ngăn này không thêm điều kiện (✔ UI 10/2026).
- **Thuộc tính khách hàng dùng được trong điều kiện** (49 mục, mã hiển thị trong ô chọn): `full_name`, `phone_number`, `mail`, `contact_tags`, `contact_categories`, `user_owner_id`, `user_owner_email`, `transfer_agent_log_note`, `last_log_note`, `change_status_log_note`, `contact_related_employee`, `interactive_call` / `_sms` / `_zns` / `_email` / `_note` / `_ticket` / `_diary` / `_change_status` / `_evaluation`, `total_interactive`, `closest_interaction_time`, `last_call_transaction_time`, `contact_created_date`, `contact_created_by`, `contact_last_updated_date`, `last_transfer_agent_time`, `last_transfer_agent_by`, `win_lose`, `opportunity_expired`, trạng thái pipeline… Kiểu thời gian so với một mốc HH:mm dd/MM/yyyy cố định, không có "trong N phút qua" → dùng điều kiện Mở rộng bên dưới.

### Điều kiện SLA: "Kiểm tra tương tác khách hàng" (nhóm Mở rộng)
- *Tương tác mới* / *Không có tương tác* · loại: Cuộc gọi, SMS, ZBS, Email Marketing, Ghi chú, Chuyển trạng thái, Log, Phiếu ghi, Đánh giá · **Người tương tác (bắt buộc)**: Nhân viên (chọn người hoặc chọn tất cả), Nhóm, Nhân viên phụ trách KH, Nhân viên liên quan, Hệ thống · "Thời điểm tương tác gần nhất" N phút/giờ.
- Cửa sổ thời gian tính lùi từ lúc nút chạy. Với nút Trì hoãn đặt trước, cửa sổ = khoảng chờ cộng dồn kể từ mốc giao việc. **Cửa sổ phải ngắn hơn khoảng chờ cộng dồn 1 phút** để log lúc vào trạng thái không bị tính là tương tác (ví dụ chờ 5/10/15 phút → cửa sổ 4/9/14; ✔ UI 11/2026).
- Chip "Nhân viên phụ trách KH" để trống bị báo "Vui lòng điền đầy đủ thông tin" → dùng chip *Nhân viên*, mở và tick nhân viên cụ thể; kiểm lại GET: `agent_option.agent_ids` phải khác rỗng, nếu rỗng thì tick đã hụt. Không tick *Hệ thống* nếu chính flow tự ghi log/ghi chú, vì log đó có thể bị tính là tương tác.
- Thay cho mọi cách tự đếm (chụp `interactive_call` vào biến rồi so sánh, so `last_call_transaction_time` với thời điểm giao…).

### Nút AI Chatbot (`OMI_BOT_AI`) (✔ UI 11/2026)
- "AI Chatbot sẽ kết thúc khi" mặc định có "BOT chủ động kết thúc"; "Thêm trường hợp" cho 3 kiểu xét **tin nhắn của khách**: Chủ đề / Ý định mong muốn, Từ khoá, Đạt giới hạn. "Trạng thái hành động" chỉ có "Thất bại".
- Không có nhánh theo hành động (ACTION) bên trong bot → muốn flow làm việc gì khi bot chọn một trường hợp mà bot không nhắn gì: bot dùng ACTION "Gọi đến kịch bản OMIFlow" (flow phụ thuộc), không nối bước tiếp theo.
- Nhánh "BOT chủ động kết thúc" cũng chạy khi khách im lặng hết thời gian chờ; JSON của nhánh: `api-reference.md` bảng DUAL, `node-condition.md` mục 2.1.

## 4. AI điền CRM sau cuộc gọi: bóc trường bằng LLM rồi gán thuộc tính (dựng thật qua UI, 10/2026)

**Mẫu**: trigger Điều kiện → Cuộc gọi → *Trạng thái cuộc gọi* = Trả lời (không dùng "Cuộc gọi được cập nhật", đó là sự kiện cập nhật cửa sổ/lịch sử, không phải kết thúc) → Trì hoãn vài phút (AI Assistant ghi kết quả trễ; `design-patterns.md` mẫu B5) → các nút LLM → Cập nhật khách hàng. Nguồn dữ liệu là `{{ca_ai_assistant}}`: một trường văn bản mô tả mọi thuộc tính theo mẫu cấu hình ở AI Assistant. Cần AI Assistant của cuộc gọi đó đã bật, nếu không biến rỗng.

- **Hướng dẫn cho AI Assistant** (thêm trường, cú pháp, trường kiểu danh sách, chép bản gốc trước khi sửa): skill con `omicall-ai-insight` (`omicall-ai-insight/references/ai-insight.md` mục 1). Đây là cấu hình dùng chung cả tổng đài.
- **Biến LLM**: nút Hành động → *Biến liên kết tuỳ chỉnh* có 5 tab (API, Random, Phép toán, Thư mời, **LLM**). Tab LLM: tên biến + ô Giá trị (prompt) + model. Mỗi nút Hành động chỉ thêm được **một** hành động Biến liên kết tuỳ chỉnh (mục đã dùng biến mất khỏi danh sách "Thêm hành động") → mỗi trường một nút, nối chuỗi.
- **Biến chỉ hiện sau khi Lưu**: chip "Biến liên kết tuỳ chỉnh" ở nút sau chỉ liệt kê biến đã lưu; trong nút Điều kiện còn phải **tải lại trang** mới thấy. Chọn biến từ chip (chèn đúng mã 10 ký tự), không gõ tên.
- **Kiểu thuộc tính khách quyết định cách gán**: thuộc tính kiểu *danh sách* (biểu tượng danh sách) **không nhận biến**, chỉ chọn một giá trị cố định; thuộc tính kiểu văn bản nhận biến; *Số điện thoại* là "Thêm giá trị mới" (có thể trùng số đã có). Kiểm từng thuộc tính trước khi thiết kế. Các kiểu trường: `omicall-crm-config/references/crm-config.md` mục 3.
- **Trường danh sách → rẽ nhánh theo giá trị**: LLM bị ép trả đúng nguyên văn một giá trị của danh sách; nút Điều kiện mỗi giá trị một trường hợp (biến, CONTAIN, giá trị); mỗi trường hợp có "Nút kế tiếp" → Hành động → Cập nhật khách hàng gán đúng giá trị. Cẩn thận chuỗi con ("Gói A" nằm trong "Gói A Plus": dùng `=` cho chuỗi ngắn hơn). **Các nhánh không gộp lại được** nên mỗi trường danh sách một flow riêng (cùng trigger, LLM chạy lại), mỗi flow = 4 + số giá trị nút. Biến không truyền giữa các flow.

## 5. Canvas: nối, xoá, sửa cạnh

Mục duy nhất về kéo/nối cạnh; nơi khác trỏ về đây.
- **Nút mới**: tạo từ "Bước tiếp theo" / "Nút kế tiếp" trong ngăn của nút nguồn (mục 3) — cách chắc chắn, nút tạo ra đã được nối.
- **Nối hai nút có sẵn** (✔ UI 11/2026): `left_click_drag` từ chấm ra của nút nguồn (bên phải nút / chấm "Bước tiếp theo") tới **đúng tâm chấm vào bên trái** nút đích (`.react-flow__handle-left`, rộng ~5px), khi cả hai cùng hiện trên màn hình. Lấy toạ độ chấm bằng JS đọc `getBoundingClientRect()` của `.react-flow__handle` rồi quy đổi theo tỉ lệ ảnh chụp (`react-flow-selectors.md`).
- **Thả lệch vài px = thả ra vùng trống**: bật bảng chọn nút mới (Escape để huỷ); nút tạo kiểu này **không được nối** (đầu ngăn ghi "Chưa liên kết"). Có lần kéo ra vùng trống chỉ làm trôi canvas; bấm cổng không mở bảng chọn.
- Ghi chép cũ (10/2026): thả vào cổng vào của nút có sẵn "không bắt". Nhiều khả năng do thả lệch tâm; nguyên nhân: Cần xác nhận.
- Giả lập PointerEvent bằng JS thường không ăn, không dùng làm cách chính.
- **Xoá cạnh**: rê chuột lên giữa đường nối → hiện **nút thùng rác đỏ** → bấm.
- **Node**: bấm vào thân node mở ngăn, không chỉ chọn. Phím tắt: Ctrl+C sao chép node, Delete xoá node. Xoá node bằng JS: `document.querySelectorAll('.react-flow__node')` → tìm theo text → `button[aria-label="Xóa node"]` `.click()`. Xoá node **giữa chuỗi làm đứt cạnh**.
- **Lưu sau khi sửa cạnh**: sửa cạnh không làm hiện nút "Cập nhật" (bấm Xuất bản thì lưu được) → agent không tự xuất bản: sửa cạnh qua `omi_save.py` (lưu nháp) hoặc để user bấm Xuất bản. Sau khi nối: lưu, mở lại hoặc GET kiểm `edges.connections` và `next_nodes`.
- **Không nối được bằng chuột, hoặc cần chèn nút vào giữa**: dựng các nút trên UI (để có schema), sửa `next_nodes` + `edges.connections` trong JSON (`api-reference.md` bảng DUAL), lưu nháp bằng `omi_save.py flow`, tải lại editor để đối chiếu.
- **Sinh phần còn lại bằng script** (✔ UI 11/2026): sau khi UI lưu, GET (`flow_outline.py --save <id>`), nhân bản nút theo mẫu (đổi id, vị trí, giá trị) ở cả `nodes` và `name_mappings`, nối cạnh theo `reactflow__edge-<src><handle>-<tgt>1` (nút Điều kiện dùng id trường hợp làm handle), rồi `omi_save.py flow`. Ví dụ 17 nút dựng từ 5 nút mẫu, editor mở lại hiển thị đủ. Đếm quota nút: tiêu đề "Số lượng nút N / 20".

## 6. Lưu, Xuất bản và id

- **Lưu lại / Cập nhật** chỉ lưu nháp, không ảnh hưởng phiên bản đang chạy. **Xuất bản** (user bấm) tạo phiên bản mới và áp dụng ngay. Hộp "Xác nhận" của Xuất bản hiện ngay ở lần bấm đầu khi không có ngăn nút nào đang mở.
- Vỏ tối thiểu và lần "Lưu lại" đầu: `api-reference.md` mục *Vỏ flow tối thiểu và lần "Lưu lại" đầu*.
- **Id flow, id phiên bản, URL webhook** sau mỗi lần lưu hoặc Xuất bản → `api-reference.md` mục *Ba loại id và URL webhook*. Trước khi báo cáo hoặc gắn: `flow_outline.py --list` rồi GET lại `kick_off.id`.
- Agent bấm "Xuất bản" hoặc "Cập nhật" trong hộp URL có thể bị hệ thống phân quyền chặn → để user tự bấm.

## 7. Gỡ lỗi biến liên kết và sửa nút qua UI (10/2026)

- **Bảng "N biến liên kết có vấn đề" có thể báo nhầm** (mã biến của Cửa sổ tương tác vẫn bị liệt kê) và **không điều hướng** tới nút chứa mã. Tìm mã: mở từng nút nghi ngờ rồi quét bằng JS: `input`/`textarea` (`.value`) và nội dung iframe TinyMCE của ô Mô tả, regex `/\{\{[A-Za-z0-9_]+\}\}/g`. Mô tả phiếu thường chứa nhiều mã nhất; ô tên phiếu và các ô thuộc tính bắt buộc của phiếu cũng có thể chứa mã.
- **Đối chiếu trước khi xoá**: đọc bộ chọn biến (nhóm Cửa sổ tương tác, Biến liên kết tuỳ chỉnh) để biết mã nào hợp lệ; chỉ gỡ mã không có ở đâu (mã mất định nghĩa thường do copy nút từ flow khác). Thay mã mất bằng biến tương đương nếu có (ví dụ tên khách hàng), nếu không thì bỏ cả dòng nhãn, đừng để dòng rỗng. Sửa thử mà chưa chắc: tải lại trang (`navigate` với `force`) là bỏ thay đổi chưa lưu.
- **Sửa mô tả (TinyMCE)**: lấy `ed = tinymce.get(iframe.id.replace('_ifr',''))`, `getContent()` → parse bằng `DOMParser`, xoá nguyên dòng nhãn+giá trị (div cha có đúng 2 con), `ed.setContent(html); ed.fire('change'); ed.undoManager.add()`. Ô tên phiếu thì chọn ô, Ctrl+A, gõ lại. Sau Cập nhật phải tải lại trang và quét lại để chắc đã lưu.
- **Kiểm API ngoài từ ngoài giao diện**: gọi thử bằng curl với đúng header (tên header phân biệt theo từng API; thông báo "thiếu mã truy cập" hay "API Key trống" cho biết sai tên hay thiếu header). Thông báo `Fetch API failed` khi bấm thử trong nút API chỉ nói OMI không nhận được response dùng được (Cần xác nhận nguyên nhân: 4xx/5xx, thiếu header, bị chặn IP).
- **Danh sách bên ngoài chưa dùng được dạng dropdown** (Gotchas "Giới hạn nền tảng" trong `playbook.md`): chỉ đề xuất đường vòng, ghi "Cần xác nhận" cho cú pháp mảng.

## 8. Kiểm thử

### Trước mỗi lần test
- Mở flow từ danh sách, đọc **Phiên bản** và cấu hình hiện tại: flow có thể đã bị người hoặc phiên khác sửa (đổi trì hoãn, giới hạn…).
- Dữ liệu test dùng tên dễ nhận ("Test …") và SĐT user cung cấp. Xoá dữ liệu test là việc của user (agent không xoá vĩnh viễn).

### Đọc kết quả
- Tab **Lịch sử** của flow: mỗi lượt một dòng (Credit, ngày tạo, phiên bản, điều kiện bắt đầu, đối tượng liên quan, trạng thái *Hoàn thành* / *Đang trì hoãn* + giờ chạy tiếp, thời lượng) — xem nhanh bằng đọc chữ trang, không cần chụp. Bấm vào ô ngày tạo để mở **hành trình**: từng nút có giờ chạy, số lần, mỗi hành động một chấm xanh/đỏ. Rê chuột lên chấm đỏ để xem mã lỗi, hoặc đọc phần tử tooltip bằng JS. Khi tab Lịch sử bị tooltip che, bấm bằng JS vào phần tử có text "Lịch sử".
- Mã lỗi đã gặp: `NO_CHANGE` (gán giá trị trùng hiện tại, vô hại), `CONTACT_EXIST` (thêm khách đã có, vô hại).
- **Kiểm "đã chạy tới nút nào"** (✔ UI 11/2026): tab Lịch sử chỉ cho biết trạng thái cả lượt chạy ("Hoàn thành") và phiên bản; muốn biết nút sau có chạy hay không thì kiểm kết quả của nút đó (phiếu đã tạo, tin đã gửi). Lượt chạy trên phiên bản cũ không chứng minh được hành vi của phiên bản mới.
- Kiểm chứng chéo: **log trong hồ sơ khách** ("OMIFlow | <tên flow> đã gán trạng thái…", "…đã thêm khách hàng và gán cho …") và **số trên chuông thông báo** (tăng 1 mỗi thông báo flow gửi tới tài khoản đang xem).
- **Thông báo lỗi đỏ biến mất rất nhanh**: muốn đọc, cài MutationObserver ghi `innerText` các nút mới vào `window.__toasts` trước thao tác rồi đọc lại (chỉ để đọc, không sửa trang).

### Thời gian chờ
- Nút "Tiếp tục kịch bản" (trên dòng hoặc menu hàng loạt ⋯: Tiếp tục / Huỷ kịch bản / Xuất Excel / Chạy lại nút thất bại / Xoá) có hộp xác nhận ghi "các hành động sau đó sẽ được không thực thi", nghĩa chưa rõ → không dùng để test.
- Hai cách tin cậy: (a) chờ thời gian thật bằng Bash `sleep <giây>` chạy nền, tới mốc thì đọc Lịch sử; (b) tạm đặt Trì hoãn = 1 phút, test, rồi **đặt lại giá trị thật và lưu nháp (Cập nhật)**; xuất bản lại để user làm hoặc chỉ khi user đã đồng ý cho flow đó. Ghi việc phải trả lại vào báo cáo giao.

### Kịch bản nên test (ngoài luồng chính)
1. Đối tượng mới đi hết luồng chính.
2. Đối tượng đã tồn tại kích hoạt lại trigger (gửi lại form, cập nhật lại): có tạo trùng không, có cập nhật đủ thuộc tính không.
3. Sửa một thuộc tính không liên quan của đối tượng đang ở trạng thái trigger: flow có chạy lại không.
4. Từng nhánh của mỗi điều kiện. Nhánh cần sự kiện thật (cuộc gọi) chỉ test khi user đồng ý gọi.
5. Đếm lượt còn lại theo giới hạn số lần đi qua. Hết lượt → dùng SĐT khác, nhờ user xoá đối tượng test, hoặc nới giới hạn.

## 9. Mẹo browser pane và chạy song song

- Ảnh chụp trễ 1–2 thao tác và khung pane đổi kích thước liên tục: xác nhận bằng JS đọc trạng thái (`ui-recipes.md` mục 2) hoặc `get_page_text`, bấm theo `ref` lấy từ `find` thay vì toạ độ. Không `wait` rồi chụp lại; chỉ khi chữ không đủ mới `zoom` vùng nhỏ để đọc tóm tắt điều kiện.
- Pane đổi kích thước thì toạ độ cũ bị từ chối ("page, zoom or size has changed") → `find` lại rồi bấm theo `ref` (không chụp lại để lấy toạ độ).
- **Ref cũ bị stale** sau khi canvas vẽ lại hoặc tải lại: bấm ref cũ có thể trúng nhầm nút khác. Luôn `find` lại ngay trước mỗi lần bấm, và kiểm tiêu đề ngăn vừa mở đúng nút chưa.
- **Nút ✕ đóng ngăn ở góc trên trái nằm đè logo trang chủ**: nếu ngăn đã đóng thì cú bấm đó trúng logo và rời khỏi editor (mất flow chưa lưu). Xác nhận ngăn đang mở trước khi bấm.
- Bấm ra ngoài hộp xác nhận có thể mở nhầm ngăn khác (ví dụ ngăn Ghi chú) và trình duyệt có thể tự điền ô; đọc lại nội dung trước khi lưu.
- `browser_batch` tối đa 25 thao tác.
- **Browser pane không bắt XHR khác domain** trong `read_network_requests`; dùng `performance.getEntriesByType('resource')` để tìm endpoint. Pane hẹp làm canvas tràn ngang → ưu tiên API thay vì bấm UI.
- Phiên đăng nhập hết hạn sau một đêm: mở trang đăng nhập để user tự đăng nhập lại.
- Đọc cookie lấy token (JS hay CDP) bị bộ lọc an toàn chặn: **không lách**, kể cả bằng hàm `fetch` trong trang tự đọc cookie. Token chỉ lấy qua MCP OMI hoặc `OMI_TOKEN_FILE` do user đặt (`scripts/omi_preflight.py`); không có thì dựng bằng UI. Trang editor tải lại toàn bộ khi đổi URL → hàm JS đọc DOM đã khai báo phải khai báo lại.
- **Quy tắc ít ảnh, công thức theo thao tác, JS đọc trạng thái**: `ui-recipes.md`.
- **Chạy song song bằng subagent (fork)**: mỗi subagent tự tạo **tab riêng** (`tabs_create`, rồi truyền `tabId` ở mọi lệnh), không dùng tab của agent chính; mỗi flow một subagent, không hai bên cùng chạm một flow. Dặn trước: chờ trước khi gõ, kiểm từng trường hợp sau khi lưu, không xuất bản. Subagent báo thiếu kiểm sau tải lại thì agent chính tự mở lại kiểm. Mẫu giao việc đầy đủ (điều CẤM, ghi manifest): `omi-mcp.md` mục *Mẫu giao việc cho subagent*; mỗi subagent tự chạy `scripts/validate_flow.py` trên bản GET sau khi lưu.
