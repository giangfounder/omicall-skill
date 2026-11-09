# Phương pháp: từ bài toán khách hàng đến chuỗi module (phân rã, không khớp mẫu)

Dùng ở bước phân tích, sau khi đọc `system-model.md`. Mục tiêu: ghép đúng module ngay từ đầu, không dò giao diện, không học thuộc từng ca. Các bảng "công thức theo bài toán" (`omicall-omiflow/references/solution-map.md`, mẫu B trong `design-patterns.md`) chỉ là **ví dụ minh hoạ** cách ghép; gặp bài toán mới thì phân rã theo các bước dưới.

## 1. Chuẩn hoá bài toán thành 5 thành phần
| Thành phần | Câu hỏi | Ví dụ trả lời |
|---|---|---|
| Vào | Cái gì khởi động (kênh, sự kiện)? | hotline, Zalo OA, form, Excel, hệ thống ngoài gọi webhook |
| Đối tượng | Việc xoay quanh thực thể nào? | khách hàng, cuộc gọi, phiếu ghi, hội thoại |
| Luật | Dựa vào đâu để quyết định, ai/đâu xử lý? | giờ làm việc, phím bấm, nội dung AI hiểu, ca/bộ phận, hạn xử lý |
| Ra | Kết quả nghiệp vụ là bản ghi hay hành động nào? | phiếu đúng chủ đề, thuộc tính khách đổi, cuộc gọi/tin đi, popup |
| Ràng buộc | Gói, quota, hệ thống ngoài, dữ liệu nhạy cảm, hạn chót? | module nào đã bật, API ngoài đã có chưa |
Hỏi user MỘT lần những thành phần chưa rõ (kèm đề xuất mặc định), không hỏi dần từng câu.

## 2. Chọn năng lực cho từng thành phần theo thang "ít bộ phận động nhất"
1. **Cấu hình sẵn của hệ thống** làm được thì dừng ở đây (hạn phiếu theo chủ đề, tự tạo khách từ cuộc gọi, phân bổ, AI Assistant, Truy vấn mở rộng): ít nút, ít quota, ít chỗ hỏng.
2. Cấu hình lớp nền: CRM → Tổng đài (định tuyến, nhóm, phím).
3. AI (bot, callbot, phân tích) khi cần hiểu ngôn ngữ.
4. **OMIFlow chỉ để phản ứng và nối**: rẽ nhánh, trì hoãn/SLA, gọi hệ thống ngoài, thông báo, kết nối bot với dữ liệu.
Mỗi sự thật chỉ giữ ở một nơi: định tuyến ở tổng đài, SLA ở chủ đề phiếu, phân lead ở cấu hình phân bổ; flow không lặp lại.

## 3. Ghép thành chuỗi Sự kiện → Điều kiện → Hành động
Viết chuỗi ra, rồi kiểm ba điểm nối hay hỏng:
- **Dữ liệu đi qua được không**: biến/trường ở mắt xích sau có tồn tại, đúng kiểu, đúng tập giá trị không (kiểu *danh sách* không nhận biến; trường đích phải dựng trước).
- **Thứ tự dựng**: từ dưới lên: trường đích → AI → tổng đài → flow (nháp) → user Xuất bản → gắn webhook/hotline.
- **Ai kích hoạt khi chạy thật**: cuộc gọi thật, webhook, lịch. Cách kiểm thử cho mắt xích đó là gì.

## 4. Gán đường thực thi cho từng mắt xích (tra `system-model.md` mục 2)
Mỗi mắt xích ghi: năng lực · skill · đường (MCP → script API → giao diện) · trạng thái.
- ✔ → đi thẳng, không khảo sát lại.
- Mắt xích thuộc **skill khác** → gọi skill đó theo mục "Gọi skill liên quan" trong SKILL.md (dùng chung domain, đăng nhập, `tenant_context.json`, manifest; không làm theo trí nhớ).
- ◐ hoặc ? → nói rõ với user đây là phương án có rủi ro. Nếu bắt buộc phải biết: khảo sát **một lần** bằng log mạng của giao diện (`read_network_requests`, văn bản) hoặc thử trên bản mới có user đồng ý, rồi **ghi kết quả vào reference/registry** kèm nhãn `✔ <tháng/năm>`. Không dò bằng ảnh chụp, không lặp lại lần sau.

## 5. Kiểm khả thi trước khi hứa
`get_service_package` (module, cờ tính năng), quota flow/nút/bot/trợ lý AI, `tenant_context.json` (kênh, nhóm, thuộc tính đã có). Thiếu gói hoặc quota thì đổi phương án ở mục 2, không dựng rồi mới biết.

## 6. Kế hoạch dựng
Danh sách việc ghi theo thứ tự mục 3, mỗi việc: công cụ (script/MCP) · chạy thử (`--mode pre`, dry-run) · ghi · GET lại kiểm (`--mode post`) · cổng duyệt của user. Việc nhiều artefact phụ thuộc nhau: `parallel.md` mục 2 và 5; ghi vào từ 2 skill trở lên thì giao `omicall-assistant` điều phối (thứ tự đợt và cổng: `orchestration.md` mục 2 của skill đó).

## 7. Học theo năng lực, không theo ca
Khi hoàn thành một bài toán, chỉ cập nhật cái tái dùng được: dòng năng lực trong `system-model.md` (đường mới, trạng thái mới), gotcha nền tảng trong reference của skill. Không ghi chi tiết nghiệp vụ hay dữ liệu của khách.

## Ví dụ phân rã (minh hoạ cách đi, không phải khuôn)
Bài toán: "Nhắc khách lịch hẹn ngày mai bằng cuộc gọi tự động; khách bấm 1 xác nhận, 2 xin đổi lịch; ghi kết quả vào hồ sơ."
- **Vào** danh sách khách + lịch (Excel hoặc hệ thống ngoài); **Đối tượng** khách + cuộc gọi; **Luật** phím 1/2; **Ra** thuộc tính khách "trạng thái lịch" + (phím 2) việc cho nhân viên; **Ràng buộc** gói có Autocall, thuộc tính đích phải có.
- Chuỗi: Autocall có menu phím (`autocall_by_phone` với `ivr_menu`, hoặc OMIFlow Marketing `AUTOCALL`) → khách bấm phím → webhook sang OMIFlow (mẫu B4b) → điều kiện theo phím → cập nhật khách / tạo phiếu.
- Gán đường: thuộc tính đích (crm-config, ghi bằng giao diện) → flow nháp (`omi_save.py flow`) → Autocall. Mắt xích **phím trong Autocall → webhook OMIFlow** chưa có bằng chứng chạy (◐): báo user là phương án, hỏi trước khi cam kết, thử một lần ở bản mới rồi ghi kết quả vào `system-model.md`.
- Không dựng flow cho phần "đếm giờ nhắc lại" nếu hạn xử lý theo chủ đề phiếu đã đủ (mục 2.1).
