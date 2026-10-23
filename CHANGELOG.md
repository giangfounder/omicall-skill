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
