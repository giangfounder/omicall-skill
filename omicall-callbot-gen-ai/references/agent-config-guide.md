# Hướng dẫn cấu hình Agent (SmartAgent) — quy chuẩn viết nội dung

Nguồn: tài liệu "Hướng dẫn cấu hình Agent – V1" của OMI, cùng thao tác giao diện đã kiểm chứng khi dựng kịch bản. Áp dụng cho mọi tenant. Bổ sung cho `api-reference.md` (schema) và `voice-rules.md` (giọng đọc).

## 1. Kịch bản chung (`instruction` của BEGIN)
Kịch bản chung là hướng dẫn cốt lõi, áp dụng suốt cuộc gọi. Gồm:

| Thành phần | Nội dung |
|---|---|
| Ý chính | Vai trò của Agent, mục tiêu cuộc gọi |
| Hướng dẫn phát âm | Cách đọc từ tiếng Anh, tên riêng doanh nghiệp và sản phẩm |
| Luồng xử lý | Các bước tổng quát từ lúc bắt đầu đến khi kết thúc |
| Câu thoại tiêu chuẩn | Lời chào, lời cảm ơn, mẫu câu ứng xử chuẩn |
| Quy tắc câu thoại | Muốn Agent nói đúng một câu thì đặt câu đó trong dấu ngoặc kép `" "`, **ưu tiên đặt ở Kịch bản chung** (không đặt trong Hướng dẫn hành động) |
| Hướng dẫn thu thập biến | Viết quy tắc thu thập (thứ tự hỏi, hỏi lại, không hỏi lại ý đã có) **tại đây**, không viết vào mô tả từng biến |

Câu đọc lại thông tin để khách xác nhận (đơn hàng, lịch hẹn, hồ sơ) đặt ở Kịch bản chung, có ngoặc kép.

Cá nhân hoá: dùng biến ngay trong kịch bản, ví dụ `"Xin chào, anh/chị có phải là {{full_name}}?"`.

## 2. Biến thu thập (`collect_variables`)
- Mô tả **gọn**: mục tiêu và **định dạng kết quả** mong muốn. Không đưa luồng điều khiển hay câu thoại dẫn dắt.
  - ĐÚNG: "Số điện thoại liên hệ của khách hàng, gồm 10 chữ số."
  - SAI: "Hỏi khách số điện thoại, nếu không đọc thì hỏi lại rồi lưu vào biến."
- Mẹo: thêm 1–2 ví dụ **phản trực giác** để nhận dạng giọng nói xử lý đúng (nói ngọng, chèn từ, đồng âm, tự sửa lời). Không liệt kê trường hợp cơ bản.
  - số đọc bằng chữ ("không chín tám một …") → ghi 10 chữ số liền nhau dạng `09xxxxxxxx`
  - "số của chị là 0912… à không 0988…" → `0988…`
- Biến có thể kèm prompt suy luận giá trị (ví dụ gán mức độ, YES/NO) ngay trong mô tả biến.
- Trên giao diện: mã biến được **tự sinh từ tên biến** (`var_` + tên bỏ dấu, nối gạch dưới, ví dụ "Họ tên khách" → `{{var_ho_ten_khach}}`). Đặt tên xong mới tham chiếu mã trong prompt; tham chiếu mã không tồn tại thì editor không nhận. Biến mới chỉ hiện trong danh sách "Dữ liệu thu thập" (chip chèn biến) sau khi đóng mở lại panel hoặc sau lần lưu.

## 3. Ý định và Hành động
### 3.1 Viết Ý định
- Ngắn gọn, tập trung mục tiêu chính của người dùng; prompt quá dài làm model lẫn ý định.
- Gộp các nhánh nhỏ cùng bản chất vào một Ý định. Không tách nhiều nhánh gần giống nhau.
- Cần phân biệt nhiều trường hợp nhỏ: tách nhãn lưu thành biến YES/NO theo nhóm, hoặc dùng node đánh nhãn (`ADD_CLASSIFY`), thay vì thêm Ý định.

### 3.2 Hành động trong Ý định (editor: "Danh sách hành động")
Editor có 2 loại hành động trong một trường hợp Ý định:
- **Thu thập thông tin** = `collect_variables` (chọn biến từ danh sách biến của BEGIN; biến đã dùng ở bước khác trong cùng Ý định bị ẩn khỏi danh sách chọn).
- **Hướng dẫn Agent** = `search_knowledge` (yêu cầu tra cứu kho tri thức hoặc gọi công cụ API).

Quy tắc:
- Hướng dẫn Agent viết **ngắn, dạng chỉ dẫn cách lấy thông tin**. Hạn chế hội thoại mẫu trong phần này (câu thoại để ở Kịch bản chung).
- Tra cứu **kho tri thức** để giải đáp thắc mắc: đặt khối Hướng dẫn Agent TRƯỚC khối Thu thập thông tin, để Agent giải đáp trước khi quay lại luồng hỏi–đáp thu biến.
- Gọi **API (Truy vấn) cần tham số là biến thu thập**: đặt khối **Thu thập thông tin TRƯỚC**, khối **Hướng dẫn Agent SAU**, và trong hướng dẫn gọi hành động bằng biến của nhóm chip "Hành động": `{{request_api_<tên truy vấn>}}` (tên truy vấn bỏ dấu, nối gạch dưới, ví dụ truy vấn "API tra cứu sản phẩm phù hợp" → `{{request_api_tra_cuu_san_pham_phu_hop}}`). Cùng nhóm chip có `{{collect_<biến>}}` để nhắc tới bước thu biến. Đã kiểm chứng theo chỉ dẫn của user.
- Ví dụ: Ý định "Đăng ký khám mới" — mô tả "Khách chưa từng khám và muốn đăng ký thông tin mới"; biến Họ tên, Ngày sinh, Số điện thoại; hướng dẫn "Truy cập knowledge base để hỗ trợ lần lượt xác nhận Họ tên, Ngày sinh và Số điện thoại để tạo hồ sơ."

## 4. Cơ chế chuyển nút
| Trường hợp | Agent xử lý |
|---|---|
| Ý định có biến thu thập | Giữ tương tác tại Ý định đến khi đủ biến bắt buộc, rồi mới chuyển sang nút tiếp theo |
| Ý định không có biến | Chuyển nút ngay khi nhận đúng Ý định, không chờ thêm lượt |

Hệ quả: bước "đọc lại cho khách xác nhận" đặt sau khi thu đủ biến **có thể bị bỏ qua** vì hệ thống chuyển nút ngay khi đủ biến.

**Cách làm đúng cho luồng cần xác nhận (đơn hàng, lịch hẹn…):**
1. Ý định thu thập (tra cứu → thu biến) để **trống "nút kế tiếp"**.
2. Câu đọc lại thông tin đặt ở Kịch bản chung (ngoặc kép).
3. Tạo Ý định riêng "Khách xác nhận đúng thông tin đã đọc lại" → nút phân loại / chuyển máy / kết thúc.

Thu một cụm thông tin liên quan chặt chẽ: để trống "nút tiếp theo" để giữ ngữ cảnh, tránh chuyển nút liên tục; có thể dùng một Ý định xác định nhu cầu rồi rẽ nhánh sang các Ý định thu từng nhóm biến riêng.

## 5. Nút Ngắt cuộc gọi (END_CALL)
- Lệnh endcall thực thi ngay sau khi model làm xong hướng dẫn trong nút endcall.
- Ý định có biến thu thập mà nút kế tiếp là endcall: hệ thống ngắt ngay khi đủ biến, bỏ qua xác nhận lại. Không nối thẳng Ý định thu biến → END_CALL.
- Đặt endcall ngay sau Ý định cuối cùng của cuộc gọi (thường là "Hoàn tất", không có biến) để luồng chạy trọn vẹn.

## 6. Điều kiện biến thu thập
- Có thể cấu hình điều kiện kiểm tra giá trị biến; hệ thống rẽ nhánh ngay khi vừa nhận giá trị, điều kiện được quét ở mỗi lượt hội thoại.
- Chỉ kiểm tra một biến thì dùng trực tiếp điều kiện biến thu thập, không tạo Ý định. Ví dụ biến chuyên khoa = "ngoài chuyên khoa" → rẽ sang end_call.

## 7. API (Truy vấn) trên giao diện
- Truy vấn nằm ở BEGIN → "Truy vấn": tên, cấu hình (GET/POST, URL, header, body raw JSON), thời gian chờ, "Hướng dẫn Agent lấy kết quả trả về từ API" (bắt buộc).
- Tham số trong body có 2 kiểu:
  - **Biến thu thập** `{{var_…}}`: Agent thu biến trước rồi điền vào body khi gọi. Dùng khi tham số chính là dữ liệu khách nói (nhu cầu, tên sản phẩm, mã đơn). Ưu tiên cách này.
  - **Biến truy vấn tùy chỉnh** `{{value1}}`, `{{value2}}`: Agent tự sinh giá trị theo phần "Định nghĩa value cho BOT". Khi body không còn dùng `value…` thì mục định nghĩa tự ẩn.
- Có thể ghép nhiều biến thành một chuỗi tìm kiếm trong một trường body; kiểm thử chuỗi ghép (kể cả khi có biến trống) trên API thật trước khi lưu.
- Giá trị khoá API/token trong header do user tự dán; agent chỉ điền tên header.

## 8. Thao tác giao diện (đã kiểm chứng)
- Nhãn phân loại: tạo toàn bộ ở "Cấu hình phân loại" trong node Phân loại đầu tiên, các node sau chọn lại nhãn (danh sách chọn cần bấm 2 lần mới mở).
- Một node Hành động chứa được nhiều hành động theo thứ tự (ví dụ Phân loại rồi Chuyển tiếp cuộc gọi).
- Kịch bản mới: "Thêm mới" → chọn SmartAgent → đặt tên → "Lưu lại" (chưa có id) → sau lần lưu đầu URL đổi sang `/update/{id}`, nút đổi thành "Cập nhật". Hộp chọn loại kịch bản nằm đè lên danh sách: bấm theo phần tử, tránh bấm xuyên xuống dòng kịch bản bên dưới.
- Khung trình duyệt hẹp (dưới khoảng 800px) làm editor chuyển giao diện điện thoại, nút Cập nhật bị đẩy ra ngoài, menu "Bước tiếp theo" không nhận bấm. Nhờ user mở rộng khung; không giả lập viewport lớn hơn (toạ độ bấm bị lệch).
- Ảnh chụp có thể trễ một thao tác so với trang: chờ 1–2 giây và chụp lại trước khi bấm tiếp, nhất là gần nút xoá (dấu x đỏ ở điều kiện, trường hợp). Sau mỗi khối thay đổi bấm "Cập nhật" và chờ thông báo "Cập nhật thành công".
- Ô văn bản dài: dùng nhập giá trị theo phần tử (form input) thay vì dán clipboard; clipboard máy không vào được trình duyệt tích hợp.
- Tải file lên "File đào tạo" cần hộp chọn file của hệ điều hành: để user tự tải.

### 8.1 Node Hành động
- Menu "Thêm hành động" của một node Hành động gồm: Tạo thông báo, API, Chuyển tiếp cuộc gọi, Gọi đến kịch bản OMIFlow. **Sau Phân loại, mục Chuyển tiếp cuộc gọi bị mờ**: không đặt Phân loại và Chuyển máy chung một node. Làm chuỗi: node Phân loại → "Bước tiếp theo" → node Hành động mới → Chuyển tiếp cuộc gọi. Tạo thông báo thì đặt chung node với Phân loại được.
- Chuyển tiếp cuộc gọi: chọn Nhân viên / Nhóm nội bộ / Nhóm bên ngoài; mặc định chọn sẵn nhân viên đầu danh sách. Bật "Đính kèm thông tin: Dữ liệu thu thập" để nhân viên nhận đủ biến.
- Tạo thông báo: Tiêu đề, Nội dung (ô soạn thảo định dạng), Gửi đến nhân viên (mặc định nhân viên đầu danh sách), Nền tảng Web / Mobile / Custom App. Biến gõ dạng `{{var_…}}` trong ô này **không được tô màu** như ở prompt nhưng đúng cú pháp danh sách biến; cần gọi thử để xác nhận giá trị được thay. Mẫu cho đơn hàng: tiêu đề kèm họ tên và số điện thoại; nội dung liệt kê sản phẩm, số lượng, người nhận, số điện thoại, địa chỉ, nhu cầu và việc nhân viên cần làm.
- Node Kết thúc cuộc gọi có một ô "Nhập mô tả hướng dẫn Agent kết thúc cuộc gọi": ghi trình tự cảm ơn, chúc, xin phép, tạm biệt.
- Mỗi trường hợp Ý định có "Giới hạn số lần kích hoạt" (0–9, để trống là không giới hạn).

### 8.2 Canvas và liên kết node
- "Bước tiếp theo" chỉ tạo node MỚI (Trì hoãn, Điều kiện, Hành động, Kết thúc cuộc gọi). Muốn nối tới node đã có: kéo từ chấm cổng ra của nhánh tới chấm cổng vào (góc trên bên trái) của node đích, ở mức thu phóng bình thường. Thả trượt khỏi cổng thì editor bật menu tạo node mới; chọn một mục trong menu sẽ tạo node nối sẵn, bấm Escape để huỷ. Thả trượt nhiều lần có thể để lại node lẻ không nối: kiểm canvas trước khi giao.
- Bấm dấu x đỏ ở "Nút kế tiếp" thì bỏ liên kết, và node đích không còn nhánh nào dẫn tới sẽ bị xoá theo.
- Canvas chỉ render node đang trong khung nhìn: tìm node bằng chữ (find, DOM) có thể không thấy node ngoài khung. Lăn chuột trên canvas là thu phóng; kéo vùng trống là di chuyển. Lối đi chắc hơn: mở panel Ngữ cảnh bắt đầu → chọn Trường hợp → bấm thẻ node ở "Nút kế tiếp" hoặc mũi tên điều hướng trên đầu panel.
- Bấm một chip biến (Dữ liệu thu thập, Hành động…) chỉ **chép biến vào clipboard** của máy, không chèn vào ô. Gõ thẳng mã biến.
- Nhóm chip "Hành động" có `{{collect_<biến>}}` và `{{request_api_<tên truy vấn>}}`.
- Sau "Cập nhật", kiểm thông báo "Cập nhật thành công" (đọc chữ trên trang). Vị trí nút Cập nhật đổi theo bề rộng khung; bấm trượt có thể mở panel Ngữ cảnh bắt đầu thay vì lưu. Nút Xuất bản nằm ngay cạnh: tìm đúng nút theo tên trước khi bấm.
- Kéo thả trong "Danh sách hành động" để đổi thứ tự khối; sau khi sửa nội dung, kiểm lại thứ tự vì editor có thể đổi chỗ.
- Ô "Hướng dẫn Agent" của hành động có nút "Xem đầy đủ" mở ngăn soạn lớn; nếu điền theo phần tử không ăn, mở ngăn này, Ctrl+A rồi gõ lại.

### 8.3 Sao chép kịch bản sang tenant khác
- Editor không có nút nhân bản hay xuất/nhập kịch bản. Menu ⋮: Căn chỉnh lại vị trí, Trả về phiên bản trước đó, Chia sẻ (một công tắc "Áp dụng", phạm vi chia sẻ chưa rõ: không bật khi user chưa đồng ý), Training.
- Cách chắc chắn: GET kịch bản nguồn bằng API (token tenant nguồn), bỏ `id`/`uuid`/`public_key`, thay nhân viên/máy lẻ, bỏ giá trị header bí mật, rồi `omi_save.py --new` bằng token tenant đích. Không có token thì dựng lại bằng giao diện theo đúng thứ tự: tên → prompt → biến → API → ý định → node.
- Phần phải làm lại ở tenant đích: chọn nhân viên nhận chuyển máy và thông báo, dán khoá API, tải file RAG.

## 9. Đăng nhập MCP trong Claude desktop (tab Code)
- Không có lệnh `claude mcp add`. Thêm server vào `mcpServers` của `~/.claude.json` (đọc và trộn, không ghi đè server khác), email điền sẵn, ô mật khẩu để `<mật khẩu>` cho user tự điền; MCP chỉ nạp khi mở phiên mới hoặc khi app kết nối lại. Agent không ghi mật khẩu kể cả khi user gửi mật khẩu trong chat.
- Khi chưa có MCP: user đăng nhập web trong browser pane, agent dựng bằng giao diện; không đọc cookie hay token.

## 10. Luồng sản phẩm và đặt hàng (mẫu dùng lại)
- Hai trường hợp trong Kịch bản chung: khách chưa rõ sản phẩm → hỏi nhu cầu (cây trồng/đối tượng, giai đoạn, vấn đề) → gọi API → gợi ý 1–2 sản phẩm; khách đã nói rõ tên → tra đúng tên, xác nhận lại tên và quy cách, có biến thể thì hỏi chọn, không hỏi lại thông tin tư vấn.
- Ý định Đặt hàng: Thu thập thông tin đơn → Hướng dẫn Agent gọi `{{request_api_…}}`; để trống nút kế tiếp. Ý định riêng "Khách xác nhận đơn đã đọc lại" → node Phân loại + Tạo thông báo cho nhân viên.
- Body API tìm kiếm ngữ nghĩa ghép nhiều biến thành một câu (`"Tìm … {{var_san_pham}} cho {{var_doi_tuong}} giai đoạn {{var_giai_doan}}, nhu cầu {{var_nhu_cau}}"`) vẫn tìm đúng khi chỉ có tên sản phẩm và các biến khác trống; thử trên API thật trước khi lưu.
