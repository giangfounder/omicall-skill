# Lịch sử phiên bản

Mỗi skill có phiên bản riêng (file `VERSION` trong thư mục skill) theo quy tắc **MAJOR.MINOR.PATCH**:
- **MAJOR**: đổi quy trình hoặc đầu vào, người dùng phải làm khác đi.
- **MINOR**: thêm quy tắc, bước, script, tài liệu tham chiếu mới.
- **PATCH**: sửa lỗi, sửa chữ, dịch mô tả, đồng bộ file dùng chung.

Mỗi bản có tag git `<tên skill>/v<phiên bản>`, ví dụ `omicall-omiflow/v1.4.0`.
Quay về bản cũ của một skill: `git checkout <tên skill>/v<phiên bản> -- <tên skill>`. Phát hành bản mới: `python tools/release.py` (xem README).
Các bản trước 2026-10-23 được đánh số lại theo lịch sử commit.

## omicall-callbot-flow
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.6.1 | 2026-10-30 | tag `omicall-callbot-flow/v1.6.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.6.0 | 2026-10-30 | tag `omicall-callbot-flow/v1.6.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.5.1 | 2026-10-29 | tag `omicall-callbot-flow/v1.5.1` | tenant_survey (dùng chung): đọc thuộc tính Phiếu ghi qua attribute/get_all (verified), dàn phẳng bộ thuộc tính |
| 1.5.0 | 2026-10-27 | tag `omicall-callbot-flow/v1.5.0` | Đăng nhập một lần: omi_login.py (kho bí mật hệ điều hành, tự đăng nhập lại, MCP không chứa mật khẩu); skill hỏi domain trước rồi yêu cầu đăng nhập trên trang OMI thật; preflight thêm route login |
| 1.4.0 | 2026-10-27 | tag `omicall-callbot-flow/v1.4.0` | Đường nhanh: preflight token, khảo sát tenant trước thiết kế, trích tài liệu, builder và validator offline cho từng skill, omi_save lưu nháp kèm GET kiểm tự động, node-status.json, shared/ + sync_shared + check_skills, xoá dashboard realtime và dữ liệu khách sót |
| 1.3.0 | 2026-10-23 | tag `omicall-callbot-flow/v1.3.0` | Tối ưu token: rút mô tả, tách phần ít dùng sang references, cache self_update 6 giờ; sửa script và xoá dữ liệu khách |
| 1.2.2 | 2026-10-23 | tag `omicall-callbot-flow/v1.2.2` | Hiện phiên bản trong mô tả skill ([vX.Y.Z], thấy khi gõ /) và câu đầu tiên agent trả lời; release.py tự cập nhật |
| 1.2.1 | 2026-10-23 | tag `omicall-callbot-flow/v1.2.1` | omi-mcp.md: thêm nguồn gói npm và yêu cầu Node 18+, đường dẫn cấu hình Claude Desktop, danh mục công cụ theo module cần bật, xử lý lỗi thường gặp |
| 1.2.0 | 2026-10-23 | tag `omicall-callbot-flow/v1.2.0` | Bước bắt buộc tự cập nhật skill khi gọi (`scripts/self_update.py`), file `VERSION`; ghi chú "Gọi thử nghiệm" là cuộc gọi giả lập trên trình duyệt qua micro máy tính, gọi ra số thật cần chiến dịch Callbot |
| 1.1.0 | 2026-10-22 | f29cdb6 | Agent tự cài và cấu hình MCP OMI cho nhiều loại agent |
| 1.0.2 | 2026-10-22 | 43ca6b2 | Dịch mô tả skill sang tiếng Việt |
| 1.0.1 | 2026-10-22 | 624cd6c | Sửa frontmatter YAML |
| 1.0.0 | 2026-10-22 | cb6720a | Bản đầu: quy trình trọn gói, quy tắc dữ liệu STT tổng đài, `gen_training.py`, `stt_noise.py`, `build_callflow.py`, spec mẫu |

## omicall-callbot-gen-ai
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.13.2 | 2026-10-30 | tag `omicall-callbot-gen-ai/v1.13.2` | RAG File đào tạo: scripts/rag_upload.py tải docx/pdf qua filestore (business_type=callbot_recording_file), ghi knowledge.files + org selectedTraining, lưu bằng omi_save --update; api-reference mục 'RAG — File đào tạo' (cả chế độ other_wok_id); SKILL.md trỏ tới script |
| 1.13.1 | 2026-10-30 | tag `omicall-callbot-gen-ai/v1.13.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.13.0 | 2026-10-30 | tag `omicall-callbot-gen-ai/v1.13.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.12.1 | 2026-10-29 | tag `omicall-callbot-gen-ai/v1.12.1` | tenant_survey (dùng chung): đọc thuộc tính Phiếu ghi qua attribute/get_all (verified), dàn phẳng bộ thuộc tính |
| 1.12.0 | 2026-10-27 | tag `omicall-callbot-gen-ai/v1.12.0` | Đăng nhập một lần: omi_login.py (kho bí mật hệ điều hành, tự đăng nhập lại, MCP không chứa mật khẩu); skill hỏi domain trước rồi yêu cầu đăng nhập trên trang OMI thật; preflight thêm route login |
| 1.11.0 | 2026-10-27 | tag `omicall-callbot-gen-ai/v1.11.0` | Thêm agent-config-guide: quy chuẩn cấu hình Agent V1 (kịch bản chung, mô tả biến, thứ tự Thu thập/Hướng dẫn Agent, chuyển nút, END_CALL), thao tác node Hành động, canvas, sao chép sang tenant khác, đăng nhập MCP trên Claude desktop, mẫu luồng sản phẩm và đặt hàng |
| 1.10.0 | 2026-10-27 | tag `omicall-callbot-gen-ai/v1.10.0` | Đường nhanh: preflight token, khảo sát tenant trước thiết kế, trích tài liệu, builder và validator offline cho từng skill, omi_save lưu nháp kèm GET kiểm tự động, node-status.json, shared/ + sync_shared + check_skills, xoá dashboard realtime và dữ liệu khách sót |
| 1.9.0 | 2026-10-23 | tag `omicall-callbot-gen-ai/v1.9.0` | Tối ưu token: rút mô tả, tách phần ít dùng sang references, cache self_update 6 giờ; sửa script và xoá dữ liệu khách |
| 1.8.2 | 2026-10-23 | tag `omicall-callbot-gen-ai/v1.8.2` | Hiện phiên bản trong mô tả skill ([vX.Y.Z], thấy khi gõ /) và câu đầu tiên agent trả lời; release.py tự cập nhật |
| 1.8.1 | 2026-10-23 | tag `omicall-callbot-gen-ai/v1.8.1` | omi-mcp.md: thêm nguồn gói npm và yêu cầu Node 18+, đường dẫn cấu hình Claude Desktop, danh mục công cụ theo module cần bật, xử lý lỗi thường gặp |
| 1.8.0 | 2026-10-23 | tag `omicall-callbot-gen-ai/v1.8.0` | Bước bắt buộc tự cập nhật skill khi gọi, file `VERSION` |
| 1.7.0 | 2026-10-22 | f29cdb6 | Agent tự cài và cấu hình MCP OMI cho nhiều loại agent |
| 1.6.4 | 2026-10-22 | 43ca6b2 | Dịch mô tả skill sang tiếng Việt |
| 1.6.3 | 2026-10-22 | 624cd6c | Sửa frontmatter YAML |
| 1.6.2 | 2026-10-22 | cb6720a | `omi-mcp.md` dùng chung cho 4 skill |
| 1.6.1 | 2026-10-21 | eea2d10 | Gỡ thay đổi của 1.6.0 (nội dung quy tắc như 1.5.0) |
| 1.6.0 | 2026-10-21 | 1cab1d4 | Dùng nguyên văn lời thoại kịch bản, câu mở đầu vào thẳng mục đích, giữ thay đổi tay khi lưu |
| 1.5.0 | 2026-10-20 | 113ffe9 | Xưng hô theo giới tính khách, cảnh báo tab editor cũ ghi đè phiên bản mới |
| 1.4.0 | 2026-10-20 | 2d1d28d | Quy tắc đầu ra cho giọng đọc tiếng Việt, không nối node phụ về BEGIN, bot không xử lý được thì chuyển máy |
| 1.3.0 | 2026-10-20 | b394d8d | Một câu nhận dạng mỗi ý định, không dựng ý định hỏi đáp, chỉ ý định Hoàn tất mới kết thúc |
| 1.2.0 | 2026-10-19 | f035b9c | Tích hợp MCP OMI: đăng nhập, công cụ theo từng bước, script token |
| 1.1.0 | 2026-10-19 | 93106b1 | Đầu vào chỉ gồm domain, tài khoản, mô tả nghiệp vụ |
| 1.0.0 | 2026-10-19 | 8846a90 | Bản đầu |

## omicall-chatbot-gen-ai
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.9.1 | 2026-10-30 | tag `omicall-chatbot-gen-ai/v1.9.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.9.0 | 2026-10-30 | tag `omicall-chatbot-gen-ai/v1.9.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.8.1 | 2026-10-29 | tag `omicall-chatbot-gen-ai/v1.8.1` | tenant_survey (dùng chung): đọc thuộc tính Phiếu ghi qua attribute/get_all (verified), dàn phẳng bộ thuộc tính |
| 1.8.0 | 2026-10-27 | tag `omicall-chatbot-gen-ai/v1.8.0` | Đăng nhập một lần: omi_login.py (kho bí mật hệ điều hành, tự đăng nhập lại, MCP không chứa mật khẩu); skill hỏi domain trước rồi yêu cầu đăng nhập trên trang OMI thật; preflight thêm route login |
| 1.7.0 | 2026-10-27 | tag `omicall-chatbot-gen-ai/v1.7.0` | Đường nhanh: preflight token, khảo sát tenant trước thiết kế, trích tài liệu, builder và validator offline cho từng skill, omi_save lưu nháp kèm GET kiểm tự động, node-status.json, shared/ + sync_shared + check_skills, xoá dashboard realtime và dữ liệu khách sót |
| 1.6.0 | 2026-10-26 | tag `omicall-chatbot-gen-ai/v1.6.0` | Trường hợp bot mô tả tự nhiên (CUSTOM_INTENT); bot thu SĐT gọi webhook OMIFlow; /end khi test; khác biệt Trò chuyện thử và kênh thật; biến LiveTalk social_lt_phone_number; mã kiểu phân bổ; bẫy giao diện editor |
| 1.5.0 | 2026-10-23 | tag `omicall-chatbot-gen-ai/v1.5.0` | Tối ưu token: rút mô tả, tách phần ít dùng sang references, cache self_update 6 giờ; sửa script và xoá dữ liệu khách |
| 1.4.0 | 2026-10-23 | tag `omicall-chatbot-gen-ai/v1.4.0` | Bước 7: gắn bot vào LiveTalk test, bộ câu hỏi thử 14 nhóm, chấm 5 tiêu chí, bảng lỗi → chỗ sửa, vòng tối ưu trước/sau (references/livetalk-test-optimize.md, scripts/eval_report.py) |
| 1.3.2 | 2026-10-23 | tag `omicall-chatbot-gen-ai/v1.3.2` | Hiện phiên bản trong mô tả skill ([vX.Y.Z], thấy khi gõ /) và câu đầu tiên agent trả lời; release.py tự cập nhật |
| 1.3.1 | 2026-10-23 | tag `omicall-chatbot-gen-ai/v1.3.1` | omi-mcp.md: thêm nguồn gói npm và yêu cầu Node 18+, đường dẫn cấu hình Claude Desktop, danh mục công cụ theo module cần bật, xử lý lỗi thường gặp |
| 1.3.0 | 2026-10-23 | tag `omicall-chatbot-gen-ai/v1.3.0` | Bước bắt buộc tự cập nhật skill khi gọi, file `VERSION` |
| 1.2.0 | 2026-10-22 | f29cdb6 | Agent tự cài và cấu hình MCP OMI cho nhiều loại agent |
| 1.1.3 | 2026-10-22 | 43ca6b2 | Dịch mô tả skill sang tiếng Việt |
| 1.1.2 | 2026-10-22 | 624cd6c | Sửa frontmatter YAML |
| 1.1.1 | 2026-10-22 | cb6720a | `omi-mcp.md` dùng chung cho 4 skill |
| 1.1.0 | 2026-10-19 | f035b9c | Tích hợp MCP OMI |
| 1.0.0 | 2026-10-19 | 8846a90 | Bản đầu |

## omicall-omiflow
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.18.1 | 2026-10-30 | tag `omicall-omiflow/v1.18.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.18.0 | 2026-10-30 | tag `omicall-omiflow/v1.18.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.17.0 | 2026-10-30 | tag `omicall-omiflow/v1.17.0` | Khảo sát giao diện 10/2026 + tài liệu công khai: bản đồ 7 màn hình tổng đài, quy tắc kịch bản cuộc gọi, form Tương tác phím và 6 loại hành động, API công khai nhóm nội bộ/hotline/IVR/Autocall, MCP tổng đài 404 trên tenant .omicrm.com; AI Assistant (phạm vi, 4 chức năng), Voice Insights 13 thông số, Chat Insights, API Voice Insights/STT; Cấu hình doanh nghiệp Khác, Phân loại, 3 loại trạng thái phiếu; omiflow thêm solution-map.md (bản đồ kết hợp module theo bài toán) |
| 1.16.0 | 2026-10-30 | tag `omicall-omiflow/v1.16.0` | Tách cấu hình nền sang skill con omicall-crm-config, omicall-pbx-config, omicall-ai-insight: mục Skill con (bảng khi nào gọi, thứ tự phối hợp), crm-config.md chuyển sang omicall-crm-config, Gotchas TTP/phân bổ/kiểu chọn trỏ sang skill con |
| 1.15.0 | 2026-10-29 | tag `omicall-omiflow/v1.15.0` | crm-config mục 3: 6 kiểu trường khi Thêm thuộc tính (Khách hàng/Phiếu ghi), dropdown và ô chọn chỉ nguồn Tùy chỉnh, khuôn API attribute/get_all (chỉ trả bộ Phiếu ghi, field_name.custom, data_type REST bên thứ ba chưa bật trên UI); tenant_survey đọc thuộc tính (verified), dàn phẳng bộ thuộc tính, ticket_switch |
| 1.14.0 | 2026-10-28 | tag `omicall-omiflow/v1.14.0` | Gotchas và mục 8 ui-build-and-test: bảng biến có vấn đề báo nhầm biến cửa sổ tương tác, điều kiện trỏ biến không tồn tại, Cập nhật chỉ lưu nháp, giới hạn dropdown động từ API, quy trình tìm và gỡ mã biến mất định nghĩa, sửa mô tả TinyMCE, ref stale |
| 1.13.0 | 2026-10-27 | tag `omicall-omiflow/v1.13.0` | Đăng nhập một lần: omi_login.py (kho bí mật hệ điều hành, tự đăng nhập lại, MCP không chứa mật khẩu); skill hỏi domain trước rồi yêu cầu đăng nhập trên trang OMI thật; preflight thêm route login |
| 1.12.0 | 2026-10-27 | tag `omicall-omiflow/v1.12.0` | Đường nhanh: preflight token, khảo sát tenant trước thiết kế, trích tài liệu, builder và validator offline cho từng skill, omi_save lưu nháp kèm GET kiểm tự động, node-status.json, shared/ + sync_shared + check_skills, xoá dashboard realtime và dữ liệu khách sót |
| 1.11.1 | 2026-10-26 | tag `omicall-omiflow/v1.11.1` | Mục 7 ui-build-and-test: AI điền CRM sau cuộc gọi (bóc trường bằng LLM từ ca_ai_assistant, thuộc tính danh sách không nhận biến nên rẽ nhánh theo giá trị), thao tác canvas xoá/nối cạnh, subagent song song dùng tab riêng |
| 1.11.0 | 2026-10-26 | tag `omicall-omiflow/v1.11.0` | Mẫu B4b hiện phím khách bấm theo chi nhánh; gắn webhook flow vào Tương tác phím (xuất bản trước); xuất bản đổi id flow; lưu flow ngay sau chọn trigger; cách học payload từ flow có sẵn; lưu ý Browser pane dùng chung |
| 1.10.0 | 2026-10-26 | tag `omicall-omiflow/v1.10.0` | Trường hợp bot mô tả tự nhiên (CUSTOM_INTENT); bot thu SĐT gọi webhook OMIFlow; /end khi test; khác biệt Trò chuyện thử và kênh thật; biến LiveTalk social_lt_phone_number; mã kiểu phân bổ; bẫy giao diện editor |
| 1.9.0 | 2026-10-23 | tag `omicall-omiflow/v1.9.0` | Tối ưu token: rút mô tả, tách phần ít dùng sang references, cache self_update 6 giờ; sửa script và xoá dữ liệu khách |
| 1.8.0 | 2026-10-23 | tag `omicall-omiflow/v1.8.0` | Mẫu đón tin nhắn LiveTalk giao cho AI Chatbot (lọc đúng widget test) |
| 1.7.2 | 2026-10-23 | tag `omicall-omiflow/v1.7.2` | Hiện phiên bản trong mô tả skill ([vX.Y.Z], thấy khi gõ /) và câu đầu tiên agent trả lời; release.py tự cập nhật |
| 1.7.1 | 2026-10-23 | tag `omicall-omiflow/v1.7.1` | omi-mcp.md: thêm nguồn gói npm và yêu cầu Node 18+, đường dẫn cấu hình Claude Desktop, danh mục công cụ theo module cần bật, xử lý lỗi thường gặp |
| 1.7.0 | 2026-10-23 | tag `omicall-omiflow/v1.7.0` | Bước bắt buộc tự cập nhật skill khi gọi, file `VERSION` |
| 1.6.0 | 2026-10-22 | f29cdb6 | Agent tự cài và cấu hình MCP OMI cho nhiều loại agent |
| 1.5.2 | 2026-10-22 | 43ca6b2 | Dịch mô tả skill sang tiếng Việt |
| 1.5.1 | 2026-10-22 | 624cd6c | Sửa frontmatter YAML |
| 1.5.0 | 2026-10-22 | 3b98915 | Tài liệu cấu hình CRM: thuộc tính động, bộ trạng thái khách hàng, chủ đề phiếu ghi |
| 1.4.1 | 2026-10-22 | cb6720a | `omi-mcp.md` dùng chung cho 4 skill |
| 1.4.0 | 2026-10-21 | 7db0d8e | Quy trình dựng và kiểm thử trên giao diện, mẫu SLA lead, module UI đã kiểm chứng |
| 1.3.0 | 2026-10-19 | f035b9c | Tích hợp MCP OMI |
| 1.2.0 | 2026-10-19 | 7eae230 | Khái niệm nền tảng từ tài liệu chính thức, mẫu đa ngành |
| 1.1.0 | 2026-10-19 | a32a66f | Danh mục module đầy đủ, API và schema flow, khung suy luận, thư viện mẫu |
| 1.0.0 | 2026-10-19 | 8846a90 | Bản đầu |

## omicall-crm-config
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.2.1 | 2026-10-30 | tag `omicall-crm-config/v1.2.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.2.0 | 2026-10-30 | tag `omicall-crm-config/v1.2.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.1.0 | 2026-10-30 | tag `omicall-crm-config/v1.1.0` | Khảo sát giao diện 10/2026 + tài liệu công khai: bản đồ 7 màn hình tổng đài, quy tắc kịch bản cuộc gọi, form Tương tác phím và 6 loại hành động, API công khai nhóm nội bộ/hotline/IVR/Autocall, MCP tổng đài 404 trên tenant .omicrm.com; AI Assistant (phạm vi, 4 chức năng), Voice Insights 13 thông số, Chat Insights, API Voice Insights/STT; Cấu hình doanh nghiệp Khác, Phân loại, 3 loại trạng thái phiếu; omiflow thêm solution-map.md (bản đồ kết hợp module theo bài toán) |
| 1.0.0 | 2026-10-30 | tag `omicall-crm-config/v1.0.0` | Bản đầu: skill con của omicall-omiflow tách cấu hình nền — crm-config (thuộc tính, trạng thái, chủ đề phiếu, phân bổ; chuyển crm-config.md từ omiflow), pbx-config (nhóm nội bộ, lời chào TTS, Tương tác phím, kịch bản gọi vào, gắn hotline), ai-insight (AI Assistant, Voice/Chat Insights cần khảo sát, đánh giá cuộc gọi, STT); sync_shared chia BUILDERS/SUBSKILLS |

## omicall-pbx-config
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.2.1 | 2026-10-30 | tag `omicall-pbx-config/v1.2.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.2.0 | 2026-10-30 | tag `omicall-pbx-config/v1.2.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.1.0 | 2026-10-30 | tag `omicall-pbx-config/v1.1.0` | Khảo sát giao diện 10/2026 + tài liệu công khai: bản đồ 7 màn hình tổng đài, quy tắc kịch bản cuộc gọi, form Tương tác phím và 6 loại hành động, API công khai nhóm nội bộ/hotline/IVR/Autocall, MCP tổng đài 404 trên tenant .omicrm.com; AI Assistant (phạm vi, 4 chức năng), Voice Insights 13 thông số, Chat Insights, API Voice Insights/STT; Cấu hình doanh nghiệp Khác, Phân loại, 3 loại trạng thái phiếu; omiflow thêm solution-map.md (bản đồ kết hợp module theo bài toán) |
| 1.0.0 | 2026-10-30 | tag `omicall-pbx-config/v1.0.0` | Bản đầu: skill con của omicall-omiflow tách cấu hình nền — crm-config (thuộc tính, trạng thái, chủ đề phiếu, phân bổ; chuyển crm-config.md từ omiflow), pbx-config (nhóm nội bộ, lời chào TTS, Tương tác phím, kịch bản gọi vào, gắn hotline), ai-insight (AI Assistant, Voice/Chat Insights cần khảo sát, đánh giá cuộc gọi, STT); sync_shared chia BUILDERS/SUBSKILLS |

## omicall-ai-insight
| Phiên bản | Ngày | Commit | Thay đổi |
|---|---|---|---|
| 1.3.0 | 2026-10-30 | tag `omicall-ai-insight/v1.3.0` | ai-insight.md mục 3a: dựng Voice Insights trên giao diện (13 thông số, gói PRO, ô bắt buộc từng thông số; mục đích cuộc gọi; form bộ tiêu chí 2 bước, loại điều kiện, gotcha) |
| 1.2.1 | 2026-10-30 | tag `omicall-ai-insight/v1.2.1` | SKILL.md mọi skill: mục 'Ít chụp ảnh, chụp thì ghi lại' ngay sau Đường nhanh (thứ tự nguồn omi-mcp.md 4a, ghi tri thức học từ giao diện vào reference 4b) |
| 1.2.0 | 2026-10-30 | tag `omicall-ai-insight/v1.2.0` | Ít chụp ảnh: omi-mcp.md mục 4a (thứ tự nguồn: tri thức skill → tenant_context → API → MCP → chữ giao diện → ảnh) và 4b (ghi tri thức học từ giao diện vào reference); script dùng chung config_survey.py đọc tổng đài và AI bằng API nội bộ (pbx/cdr/ai/contact, ✔ GET 10/2026); omi_api thêm host; pbx-config: bảng API, giờ làm việc nằm ở đầu số (working_days chọn kịch bản), khuôn kịch bản/Tương tác phím (phím ở trường ivr)/nhóm/lời chào; ai-insight: API AI Assistant, mục đích cuộc gọi, tiêu chí |
| 1.1.0 | 2026-10-30 | tag `omicall-ai-insight/v1.1.0` | Khảo sát giao diện 10/2026 + tài liệu công khai: bản đồ 7 màn hình tổng đài, quy tắc kịch bản cuộc gọi, form Tương tác phím và 6 loại hành động, API công khai nhóm nội bộ/hotline/IVR/Autocall, MCP tổng đài 404 trên tenant .omicrm.com; AI Assistant (phạm vi, 4 chức năng), Voice Insights 13 thông số, Chat Insights, API Voice Insights/STT; Cấu hình doanh nghiệp Khác, Phân loại, 3 loại trạng thái phiếu; omiflow thêm solution-map.md (bản đồ kết hợp module theo bài toán) |
| 1.0.0 | 2026-10-30 | tag `omicall-ai-insight/v1.0.0` | Bản đầu: skill con của omicall-omiflow tách cấu hình nền — crm-config (thuộc tính, trạng thái, chủ đề phiếu, phân bổ; chuyển crm-config.md từ omiflow), pbx-config (nhóm nội bộ, lời chào TTS, Tương tác phím, kịch bản gọi vào, gắn hotline), ai-insight (AI Assistant, Voice/Chat Insights cần khảo sát, đánh giá cuộc gọi, STT); sync_shared chia BUILDERS/SUBSKILLS |
