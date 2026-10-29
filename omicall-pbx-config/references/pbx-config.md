# OMICall — Cấu hình tổng đài (dùng chung mọi tenant)

Nguồn: mô tả công cụ MCP OMI (`omicall-mcp`, nhóm Tổng đài, module `switchboard`) và các lần cấu hình Tương tác phím thật khi dựng OMIFlow (10/2026). Mục nào ghi **[MCP]** là theo mô tả công cụ, chưa đối chiếu với giao diện; mục ghi **✔** đã làm thật. Giá trị cụ thể (đầu số, máy lẻ, tên nhóm) luôn tra trong tenant.

## 1. Thành phần và thứ tự phụ thuộc
```
Máy lẻ (nhân viên) → Nhóm nội bộ (nhóm đổ chuông) → Tương tác phím / IVR, Lời chào (file âm thanh)
  → Kịch bản tổng đài (định tuyến cuộc gọi vào) → gắn vào Đầu số (hotline)
```
Dựng từ dưới lên: thiếu máy lẻ thì không có nhóm, thiếu nhóm thì phím không có đích, kịch bản chưa xong thì chưa gắn hotline.

## 2. Đọc hiện trạng (một lần mỗi phiên, ghi vào `tenant_context.json`)
| Cần | Công cụ MCP | Ghi vào |
|---|---|---|
| Module đã bật | `get_service_package` (cần `switchboard`) | `modules_enabled` |
| Đầu số, kịch bản đang gắn | `list_hotlines`, `get_hotline` | `hotlines` |
| Máy lẻ | `list_extensions`, `get_extension`, `list_agents` | `extensions`, `agents` |
| Nhóm đổ chuông | `list_groups` | `pbx.ring_groups` |
| IVR / tương tác phím | `list_ivr` | `pbx.ivr` |
| Kịch bản định tuyến | `list_scripts` | `pbx.call_scripts` |
| File lời chào, ghi âm | `list_audio` | `pbx.audio` |

Khoá `pbx.*` chưa có trong khuôn `tenant_context.template.json`; thêm vào file thật ở scratch, không sửa khuôn.

## 3. Nhóm nội bộ (nhóm đổ chuông) [MCP]
`create_group(name, strategy_type, members[])` — `members` là số máy lẻ; `strategy_type`: `enterprise` (đổ đồng thời), `rollover` (lần lượt), `random` (ngẫu nhiên). Sửa: `update_group`, `add_group_members`, `remove_group_members`. Mỗi phím của TTP cần một nhóm có sẵn.

## 4. Lời chào và file âm thanh [MCP]
- `generate_tts_audio(text, speaker_id, speed)`: tối đa **300 ký tự** mỗi lần; giọng `northern_female_ngocanh` (mặc định), `southern_male_tienhuy`, `northern_male_anhkiet`, `southern_female_khangan`; `speed` 0.8–1.2. Lời chào dài hơn → tách nhiều đoạn hoặc dùng file ghi âm do khách cung cấp.
- `text_to_speech` để nghe thử trước khi tạo file. `list_audio` lấy id file (`greeting_file_id`).
- Nội dung lời chào lấy từ tài liệu khách; không có thì soạn nháp và ghi "Cần xác nhận", không tự dùng.

## 5. Tương tác phím (TTP) ✔ giao diện
Đường dẫn: Cấu hình > Tổng đài > Tương tác phím (`/config/switchboard/key-interaction/list`).
- Trường: tên, nhạc chờ bắt đầu, số lần cho nhấn sai, thời gian chờ, kịch bản kết thúc, công tắc "Chuyển tiếp… khi nhấn đúng số nội bộ" (đừng bật nhầm), **Kích hoạt Webhook** + URL, bảng **Thao tác phím** (phím → kịch bản / nhóm nội bộ).
- Webhook TTP gửi `digits`, `customer_phone`, `ct_transaction_id`. Phím có thể ghi `"2"` hoặc `"02"` → flow nhận phải so `IN`/`CONTAIN`.
- Ô "URL nhận kết quả từ hook" **không lưu được khi flow đích còn nháp** (nút Cập nhật không báo lỗi, ngày sửa đổi không đổi) → flow phải được user Xuất bản trước, gắn sau, tải lại trang để kiểm chứng. Xuất bản đổi id flow → dùng URL của bản đã xuất bản.
- Gõ xong ô nhập phải click ra ngoài rồi mới bấm Cập nhật (click đầu chỉ làm mất focus).

API tương ứng [MCP]: `create_ivr(name, greeting_file_id, keypad_actions[], max_retries=3, timeout=5)`; mỗi `keypad_actions` = `{key: 0-9|*|#, action: extension|ivr_menu|ring_group|recording, action_value}`. **Cần xác nhận**: đối tượng "IVR" của MCP có phải chính là "Tương tác phím" trên giao diện không, và MCP có hỗ trợ trường webhook không → dựng thử một bản (khi user đồng ý) rồi đối chiếu trên giao diện trước khi dựa vào.

## 6. Kịch bản tổng đài (định tuyến cuộc gọi vào) [MCP]
- `create_script(name, description, routing_rules[])`; mỗi luật `{criteria_type, action, action_value}` với `criteria_type`: `2` = nhân viên phụ trách khách, `3` = khách gọi lại, `4` = khách có cuộc gọi nhỡ; `action` ví dụ `extension`.
- Gắn vào đầu số: `update_hotline(hotline_id, inbound_script_id)`; bật gọi ra: `outbound_enabled`. Đây là thay đổi đổi ngay đường đi của cuộc gọi thật.
- **Cần xác nhận / cần khảo sát giao diện**: giờ làm việc và nhánh ngoài giờ của kịch bản, vị trí lời chào, TTP và callbot trong kịch bản, hàng đợi.

## 7. Máy lẻ [MCP]
`update_extension(user_uuid, call_timeout, password)`: chỉ đổi thời gian đổ chuông khi user yêu cầu; **không đổi mật khẩu SIP** (là bí mật, agent không đặt hộ). `update_extension_status` đổi trạng thái sẵn sàng.

## 8. Kiểm thử
- Sau khi tạo: `list_*` / `get_*` đọc lại, đối chiếu từng phím, thành viên nhóm, file lời chào.
- Gọi thử: chỉ khi user đồng ý và đưa số; `click_to_call` rồi `search_calls`, `get_call_detail(transaction_id)` xem đường đi và phím đã bấm. Flow nhận webhook TTP: xem tab Lịch sử của flow.

## 9. Việc còn phải khảo sát
Giờ làm việc của tổng đài (đặt ở đâu, áp cho đầu số hay kịch bản), nhạc chờ, hàng đợi, thứ tự các bước trong kịch bản gọi vào trên giao diện, quan hệ IVR (MCP) ↔ Tương tác phím (giao diện). Khảo sát được mục nào thì ghi vào đây kèm ✔ và tháng.
