# Tối ưu kịch bản Callbot Gen AI đã có (nhiều kịch bản cùng tenant)

Dùng khi user muốn "đánh giá và tối ưu" các kịch bản AI_AGENT đang có, không dựng mới từ tài liệu. Ghi từ một lần làm thật trên 8 kịch bản theo ngành (✔ API 11/2026, môi trường stg). Chỉ ghi năng lực nền tảng, không ghi dữ liệu khách.

## 1. Đánh giá nhanh (đọc, không ghi)
`script_outline.py --list` rồi `--id <id> --save` cho từng kịch bản (bản gốc làm baseline hoàn tác, không sửa). Soi 5 điểm:
- RAG: `knowledge.files` và `knowledge.apis` rỗng mà prompt dài 6–7 nghìn ký tự có mục KHO/CÂU HỎI THƯỜNG GẶP → FAQ đang nhúng trong prompt, nên tách ra RAG.
- Mã biến lệch giữa các kịch bản cùng tenant (số điện thoại, đồng ý, thời gian mỗi nơi một mã) → khó đọc CRM và flow chung.
- `validate_smartagent.py --mode post` FAIL C2/C8/C9/C10/X2 trên bản do giao diện lưu: thường là hình dạng dữ liệu (thiếu `classifies`, mô tả END_CALL, biến cho node ACTION, điều kiện hệ thống), không phải lỗi nghiệp vụ.
- `tts_lint.py`.
- Chuyển máy: node TRANSFER_CALL trỏ nhóm/máy lẻ nào, có tồn tại không (xem mục 4).

## 2. Quy trình tối ưu an toàn
1. `scripts/optimize_script.py <GET.json> <thư mục ra>`: (a) đổi mã biến theo bảng chuẩn `var_ho_ten, var_sdt, var_nhu_cau, var_thoi_gian, var_khu_vuc, var_dong_y`, chỉ đổi khi mã đích chưa có (tránh va chạm); (b) tách mục FAQ ra file docx, thay bằng mục `# TRA CỨU KIẾN THỨC` (bot chỉ nêu số liệu có trong kho, không tự thêm); (c) vá C2/C8/C9/C10/X2; (d) đặt tên `<tên> - Tối ưu`, `is_publish:false`. In JSON gồm `out`, `faq`, `log`.
2. `omi_save.py callbot <out> --new` (kịch bản mới, bản gốc nguyên vẹn). Không `--update` lên kịch bản gốc khi user chưa chỉ định.
3. RAG theo mục 3 (tải file FAQ vào bản vừa lưu bằng `rag_upload.py`; dự phòng `rag_other.py`), rồi `omi_save.py --update --confirm-update` (ngoại lệ Rules 4: kịch bản chính agent vừa tạo).
4. Tự GET lại và chạy `validate_smartagent.py --mode post` độc lập; mỗi lần lưu server cấp `id` MỚI, luôn dùng id mới nhất.
Nhiều kịch bản: mỗi kịch bản một tiến trình nền riêng, `--out-dir` riêng (tránh ghi chung file), mỗi tiến trình ghi một file kết quả JSON; đây là script Python, không phải subagent LLM. Tự kiểm lại từng kết quả bằng GET, không tin file kết quả.

## 3. RAG cho callbot
Theo `references/api-reference.md` mục "RAG — File đào tạo": `rag_upload.py` tải lên qua `put_v2` (◐ tải được; bot truy xuất nội dung: Cần xác nhận bằng gọi thử); đường "Dữ liệu khác" (`rag_other.py`) là dự phòng.

## 4. Bẫy đã gặp
- `is_publish`: server có thể trả `true` cho bản nháp dù gửi `false`. Tin việc "chưa gắn hotline" hơn là cờ này; báo user kiểm trên giao diện.
- Đổi mã biến làm flow/CRM đang đọc mã cũ không khớp. Báo trước khi user chuyển sang bản mới.
- Chuyển máy: `list_groups`/`list_hotlines` có thể trả 404 trên tenant nhỏ; không xác minh được nhóm đổ chuông (Ring_group) thì ghi "Cần xác nhận", để user tự kiểm trong Cài đặt tổng đài.
- Biến lõi không ép đủ ở mọi ngành; thiếu biến lõi do nghiệp vụ thì giữ nguyên.

## 5. Môi trường không có giao diện (máy chủ chỉ có terminal)
- `omi_login.py` chặn nhập mật khẩu qua pipe/agent và form `--ui` cần trình duyệt. User chỉ có terminal: nhờ họ tự chạy `! python <skill>/scripts/omi_login.py setup --domain <domain> --email <email>` để gõ mật khẩu vào ô ẩn. Không nhận mật khẩu qua chat; lỡ nhận thì không lưu vào cấu hình, khuyên đổi mật khẩu.
- Máy không có Secret Service thì cần `pip install --user keyring keyrings.alt` (kho dạng file chữ thường, nhắc user).
- Công cụ MCP chỉ nạp ở phiên mới. Trong phiên đang chạy, cần gọi MCP thì dùng script gọi stdio của chính MCP đó, không in đầu ra có bí mật (ví dụ mật khẩu SIP trong `list_extensions`).
- Tài khoản cùng domain có thể đăng nhập UI nhưng lỗi `agent_not_exists`/`Unknown API error` qua API: thử tài khoản khác của tenant thay vì thử lại.
- Python: skill cần Python ≥ 3.10; Amazon Linux 2023 có `python3.11` riêng, tạo symlink `python` → `python3.11`.
- Không dùng `pkill -f <chuỗi>` trong lệnh shell của agent (khớp chính shell, exit 144); dừng theo PID.
