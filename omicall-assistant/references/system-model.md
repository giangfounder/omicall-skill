# OMICall — Mô hình hệ thống: có gì, làm được gì, đi đường nào nhanh nhất

Đọc ở bước phân tích bài toán, TRƯỚC khi chọn module. Cách suy luận từ bài toán: `solution-method.md`. Mỗi dòng dưới đây tổng hợp từ tài liệu các skill (10/2026), không thêm điều chưa có nguồn.

## 1. Mô hình: mọi giải pháp là chuỗi Sự kiện → Điều kiện → Hành động trên Thực thể
- **Thực thể**: Khách hàng, Cuộc gọi, Phiếu ghi, Hội thoại (Zalo OA, Fanpage, LiveTalk…), Nhân viên/Nhóm, Đầu số + Kịch bản.
- **Sự kiện**: cuộc gọi vào/kết thúc/nhỡ, phím IVR, phiếu mới, tin nhắn, webhook từ hệ thống ngoài, lịch/Excel, đối tác.
- **Hành động**: tạo/sửa bản ghi, gọi ra/gọi tự động, gửi tin (SMS, ZNS, Zalo), thông báo/popup cho nhân viên, gọi API ngoài, chuyển tiếp (nhóm, callbot, người), AI bóc/chấm/tóm tắt.
- **Bốn lớp**: Dữ liệu CRM → Tổng đài → AI → Điều phối (OMIFlow). Lớp dưới là nền: dựng từ dưới lên, mỗi sự thật chỉ giữ ở một nơi.

Nhãn trạng thái: **✔API** đã chạy thật qua API · **✔UI** đã thao tác thật trên giao diện · **◐** có công cụ/endpoint nhưng chưa chạy ghi (thấy trong mã giao diện hoặc mô tả MCP), thử trên bản mới và có user đồng ý · **?** Cần xác nhận (không dò bằng ảnh chụp, xem `solution-method.md` mục 4).

## 2. Bản đồ năng lực
Cột "Ghi" là đường nhanh nhất đã có; thứ tự ưu tiên chung: cấu hình sẵn của hệ thống → MCP → script API của skill → giao diện.

| Năng lực | Lớp | Đọc | Ghi | Trạng thái | Skill |
|---|---|---|---|---|---|
| Đầu số, giờ làm việc (`working_days` chọn kịch bản) | Tổng đài | `config_survey.py`; MCP `list_hotlines` | gắn kịch bản vào hotline: MCP `update_hotline` (user đồng ý) | đọc ✔API; ghi ◐ | pbx-config |
| Kịch bản cuộc gọi vào (tiêu chí, chuyển tiếp nhóm/phím/callbot) | Tổng đài | `config_survey.py` | giao diện; API `call_script/add\|update`, MCP `create_script` | đọc ✔API; ghi ✔UI, API/MCP ◐ | pbx-config |
| Tương tác phím IVR (phím → nhóm, webhook sang OMIFlow) | Tổng đài | `config_survey.py` | giao diện; API `key_interactive_script/*`, MCP `create_ivr` | đọc ✔API; ghi ✔UI, còn lại ◐ | pbx-config |
| Nhóm nội bộ (chiến lược đổ chuông, hàng đợi) | Tổng đài | `config_survey.py` | giao diện; API `internal_group/add`, MCP `create_group` | đọc ✔API; ghi ✔UI, còn lại ◐ | pbx-config |
| Lời chào (TTS hoặc ghi âm) | Tổng đài | `config_survey.py` | giao diện; MCP `text_to_speech` chỉ để nghe thử | đọc ✔API; ghi ✔UI | pbx-config |
| Nhân viên, máy lẻ, kênh, danh mục phiếu, gói và quota | Nền | MCP `list_agents`, `list_extensions`, `get_all_channels`, `get_ticket_categories`, `get_service_package` | — | ◐ theo quy trình Bước 0 của skill; chưa ghi nhận số lần chạy | mọi skill |
| Gọi thử/gọi ra, tra kết quả cuộc gọi | Cuộc gọi | MCP `search_calls`, `get_call_detail` | MCP `click_to_call`, `update_call` (tag, ghi chú) | ◐ là cách kiểm thử theo skill (không có ghi nhận chạy riêng) | callbot, omiflow |
| Gọi tự động hàng loạt (TTS, ghi âm, IVR) | Cuộc gọi | — | OMIFlow Marketing `AUTOCALL`; MCP `autocall_by_phone` | TTS ✔ (mẫu đã chạy); IVR/ringGroup ◐ | omiflow |
| Callbot Gen AI (SmartAgent): ý định, thu thập, API, RAG, chuyển máy | AI | `script_outline.py` | `build_smartagent.py` → `omi_save.py callbot` | ✔API với node `verified`; node khác ✔UI hoặc ? (`node-status.json`) | callbot-gen-ai |
| Callbot cổ điển (NORMAL): ý định, thực thể, cây hội thoại | AI | `omi_save` GET | `gen_training.py` + `build_callflow.py` → `omi_save.py callflow`; đẩy Excel huấn luyện qua giao diện | ✔API; `upload_excel` API ? | callbot-flow |
| Chatbot OmiBot (Zalo OA, Fanpage, LiveTalk) | AI | `bot_outline.py` | `build_bot.py` → `omi_save.py bot` (lưu nháp, không xuất bản) | ✔API với node `verified`; gửi tin/kết thúc/chuyển nhân viên ✔UI | chatbot-gen-ai |
| RAG, tài liệu đào tạo | AI | outline | `rag_upload.py` rồi lưu lại bằng `omi_save.py` | ✔API | callbot-gen-ai, chatbot-gen-ai |
| AI Assistant, Voice Insights, Chat Insights | AI | `config_survey.py` (khoá `ai_config`) | giao diện; API `assistant/add\|update` | đọc ✔API; ghi ✔UI, API ◐ | ai-insight |
| Khách hàng (tìm, tạo, sửa, ghi chú, chuyển người phụ trách) | CRM | MCP `get_contact_by_phone`, `search_contacts`; Public API v2 | MCP `create_contact`; Public API `contact/add\|update` | ✔ (chatbot gọi thẳng Public API: hướng A) | chatbot-gen-ai, crm-config |
| Thuộc tính động, bộ trạng thái, chủ đề phiếu, phân bổ | CRM | `tenant_survey.py` (đọc bộ thuộc tính Phiếu ghi ✔; của Khách ?) | giao diện | đọc ✔API (phiếu); ghi: Cần xác nhận API | crm-config |
| Phiếu ghi (tạo, cập nhật, ghi chú, chuyển, thống kê) | CRM | MCP `search_tickets`, `get_ticket` | MCP `create_ticket`, `update_ticket`, `update_ticket_status` | ◐ có trong MCP 1.3.1 (module `ticket`); chưa ghi nhận chạy ghi; ghi/xoá chỉ khi user đồng ý | omiflow |
| Hội thoại đa kênh, gửi tin | Đa kênh | MCP `search_conversations`, `get_conversation` | MCP `send_*_message`, `transfer_conversation` | gửi cho người thật: chỉ khi user đồng ý | chatbot-gen-ai |
| OMIFlow: trigger, điều kiện, trì hoãn, hành động, gọi API ngoài, popup, SMS/ZNS, chạy Callbot/Chatbot | Điều phối | `flow_outline.py` | `omi_save.py flow` (`save_draft_v2` trên flow nháp có `_id`) | lưu nháp ✔API; **tạo vỏ flow và Xuất bản = giao diện, user duyệt** | omiflow |
| Webhook ra/vào, gọi hệ thống ngoài khi nhân viên gọi | Điều phối | MCP `list_webhooks` | MCP `register_webhook` (HTTPS); OMIFlow `SEND_WEBHOOK`; Truy vấn mở rộng (cấu hình sẵn) | webhook ✔; Truy vấn mở rộng: chi tiết ? | omiflow, pbx-config |

## 3. Ranh giới cố định của hệ thống
- Xuất bản, bật/tắt, xoá flow/kịch bản và gắn hotline thật: chỉ khi user duyệt; flow luôn giao ở dạng nháp.
- Gửi tin hay gọi cho người thật, công cụ ghi vào tổng đài/khách/phiếu: từng việc một, user đồng ý trước.
- Mỗi tenant có gói khác nhau: kiểm `get_service_package` và quota flow/nút/bot trước khi hứa.
- Một số hành động không có JSON đã kiểm chứng (`node-status.json` ghi `unverified`, `enum`, `ui_only`): không bịa schema, đi giao diện hoặc ghi "Cần xác nhận".
- Token, cookie, mật khẩu: không đọc, không in, không chuyển; đăng nhập bằng form cục bộ (`omi-mcp.md` mục 2a).
