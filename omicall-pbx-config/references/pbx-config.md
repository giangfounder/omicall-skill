# OMICall — Cấu hình tổng đài (dùng chung mọi tenant)

Nhãn nguồn: **✔ UI 10/2026** = đã xem trên giao diện một tenant thật (chỉ xem, không lưu); **[API công khai]** = tài liệu `api.omicall.com` (Public API, xác thực bằng apiKey của doanh nghiệp); **[MCP]** = mô tả công cụ `omicall-mcp`, chưa đối chiếu. Giá trị cụ thể (đầu số, máy lẻ, tên nhóm) luôn tra trong tenant.

## 1. Bản đồ màn hình ✔ UI 10/2026
Cấu hình → **Tổng đài**:
| Mục | Đường dẫn | Dùng để |
|---|---|---|
| Danh sách đầu số | `/config/switchboard/sip-number/all` | hotline: loại (Cố định, Di động, 18xx, 19xx, Đầu số ngoài), nhà cung cấp, tag, trạng thái, **ngày hết hạn**; lọc "Đầu số có vấn đề" |
| Kịch bản cuộc gọi | `/config/switchboard/call-script/list` | định tuyến cuộc gọi vào (mục 4); mỗi kịch bản có "Số nội bộ đại diện" |
| Nhóm nội bộ | `/config/switchboard/internal-group/list` | nhóm đổ chuông nhân viên (mục 3); có số nội bộ riêng |
| Nhóm bên ngoài | `/config/switchboard/outer-group/list` | đích chuyển ra số ngoài (chi tiết: Cần khảo sát) |
| Tương tác phím | `/config/switchboard/key-interaction/list` | IVR (mục 5); có số nội bộ riêng |
| Số nội bộ | `/config/switchboard/internal-number/list` | máy lẻ của nhân viên |
| Lời chào | `/config/switchboard/greeting/list` | file âm thanh (mục 2) |

Cấu hình → Doanh nghiệp → **Cuộc gọi** (`/config/company/call/list`) ✔: ưu tiên gọi nội mạng, ưu tiên gọi ra theo quốc gia, **chặn cuộc gọi** đi/đến, **Mục đích cuộc gọi** (nhân viên chọn trước khi gọi; dùng cho tiêu chí AI — `omicall-ai-insight`), random đầu số gọi ra, hạn mức cuộc gọi, **Truy vấn mở rộng** (hệ thống gọi truy vấn khi nhân viên gọi, kết quả hiện ở cửa sổ cuộc gọi — cách đưa dữ liệu hệ thống ngoài lên màn hình gọi mà không cần OMIFlow; cấu hình chi tiết: Cần khảo sát).

## 2. Lời chào ✔ UI 10/2026
- Bốn nguồn (tab): **Tải lên** (file ghi âm), **Robot đọc** (TTS), **AI Callbot**, **Khác**. Danh sách có thời lượng và phân loại.
- Lời chào dùng ở: nhạc chờ của Tương tác phím, thành phần "Lời chào" trong kịch bản cuộc gọi, hành động "Lời chào" của một phím.
- [MCP] `generate_tts_audio(text ≤300 ký tự, speaker_id, speed 0.8–1.2)`; giọng `northern_female_ngocanh`, `southern_male_tienhuy`, `northern_male_anhkiet`, `southern_female_khangan`.
- Nội dung lời chào lấy từ tài liệu khách; không có thì soạn nháp, ghi "Cần xác nhận".

## 3. Nhóm nội bộ (nhóm đổ chuông)
- ✔ UI: danh sách có Tên nhóm, Số nội bộ, số Nhân viên. Tenant mới có sẵn "Nhóm nhân viên mặc định" và kịch bản "Chuyển đến nhóm nhân viên mặc định".
- [API công khai] `POST /api/call_center/internal_group/add`: bắt buộc `group_name`, `strategy` (`enterprise` đổ đồng loạt / `rollover` lần lượt / `random` ngẫu nhiên), `sip_members`, `timeout`; tuỳ chọn **hàng đợi** `call_queue_config {enable, is_in_call, is_offline, waiting_time}`. Nguồn: https://api.omicall.com/omicall-api/call-center
- Chọn chiến lược: ít người, ai rảnh nghe → `enterprise`; có người trực chính → `rollover`; chia đều → `random`. Bật hàng đợi khi cao điểm vượt số nhân viên.

## 4. Kịch bản cuộc gọi (định tuyến gọi vào) ✔ UI 10/2026
- Mỗi kịch bản = danh sách **Thành phần** kéo thả được. Quy tắc trên giao diện: **tối đa 3 tiêu chí, luôn đứng đầu**; sau đó là **lời chào** và **hành động chuyển tiếp**; không thêm được thành phần sau một hành động chuyển tiếp hoặc **hộp thư thoại** (thành phần cuối).
- Hành động chuyển tiếp thấy được trên tenant khảo sát: chuyển tới Nhóm nội bộ (kịch bản mặc định) và **Chuyển tiếp đến kịch bản AI Callbot** (callbot nghe máy). Danh sách đầy đủ loại thành phần: Cần khảo sát (có thể giống bộ hành động của phím ở mục 5, chưa kiểm).
- **Giờ làm việc không nằm trong kịch bản** mà ở đầu số (mục 7: `working_days` chọn kịch bản theo ngày/khung giờ). Loại tiêu chí của kịch bản (khách VIP, người phụ trách…): Cần khảo sát. [MCP] `create_script` gợi ý `criteria_type` 2 = nhân viên phụ trách, 3 = khách gọi lại, 4 = khách gọi nhỡ — chưa đối chiếu.
- Gắn vào đầu số: [API công khai] `POST /api/call_center/hotline/update` — **`call_script` là kịch bản gọi vào mặc định**; `extensions`/`group_ids` chỉ là **quyền dùng đầu số để gọi ra**, không định tuyến gọi vào; `allow_call_in`, `allow_call_out`, `access_type`. `/hotline/extension/update` gán đầu số cho từng máy lẻ theo chiều in/out.

## 5. Tương tác phím (IVR) ✔ UI 10/2026
Form chỉnh sửa:
- **Tên**, **Nhạc chờ bắt đầu** (lời chào)*, **Số lần cho phép nhấn sai phím***, **Nhạc chờ khi nhấn sai phím**, **Thời gian chờ*** (giây), **Nhạc chờ khi trở lại tương tác này** (khi IVR lồng nhau quay về).
- Công tắc **"Chuyển tiếp cuộc gọi đến nhân viên khi nhấn đúng số nội bộ"** (khách bấm thẳng máy lẻ; đừng bật nhầm).
- **Kịch bản kết thúc**: khi không bấm hoặc sai quá số lần → chọn hành động (mặc định "Không hành động").
- **Kích hoạt Webhook** + **URL nhận kết quả từ hook** (URL trigger API của OMIFlow). Webhook gửi `digits`, `customer_phone`, `ct_transaction_id`; phím có thể ghi `"2"` hoặc `"02"`.
- **Thao tác phím**: mỗi dòng Phím → Kịch bản. Sáu loại hành động: **Không hành động**, **Chuyển cuộc gọi** (→ Nhóm nội bộ / Nhóm bên ngoài / Nhân viên), **Kịch bản AI Callbot**, **Tương tác phím** (IVR con), **Lời chào** (phát một file), **Hộp thư thoại**.

[API công khai] `POST /api/call_center/key-interaction/add`: bắt buộc `script_name` (không trùng), `max_failure`, `time_out`, `scripts` (danh sách phím), `greeting_id` (phải upload audio trước); tuỳ chọn `invalid_sound_id`, `action`/`action_type` (`Ring_group`, `Ivr_menu`, `Recording`) cho trường hợp không bấm/sai quá lần.

Gotchas ✔:
- Ô URL webhook **không lưu được khi flow đích còn nháp** (Cập nhật không báo lỗi, ngày sửa đổi không đổi) → user Xuất bản flow trước, gắn sau, tải lại để kiểm. Xuất bản đổi id flow → dùng URL sau xuất bản.
- Gõ xong ô nhập phải click ra ngoài rồi mới bấm Cập nhật.
- Chọn thử trong danh sách hành động **đã đổi giá trị trên form** dù chưa lưu → khảo sát xong bấm **Đóng**, mở lại danh sách kiểm cột "Ngày sửa đổi" không đổi.

## 6. Gọi tự động (Autocall) dùng lại khối tổng đài [API công khai]
- `POST /api/v2/auto-call/direct-call` (gọi ngay, không tạo phiên; `phoneNumbers`, `scripts`, `sipNumbers`, tuỳ chọn `httpCallback`) và `POST /api/v2/autoCall/executeByPhone` (tạo phiên: `sendTime`, `numberCallPerTime` ≤ CCU gói, `durationOfEachCall`, `maxRetryOfDetail`, `retryAfterSeconds`, `autoPause` khi hết nhân viên rảnh — chỉ với kịch bản chuyển vào nhóm nội bộ).
- Bước kịch bản: `recording` (lời chào), `textVariable`/`callBotTextVariable` (TTS có biến), `ivrMenu` (số nội bộ của một Tương tác phím), `ringGroup` (số nội bộ của nhóm nội bộ) → một chiến dịch gọi ra có thể đọc thông báo, cho bấm phím, rồi chuyển vào nhóm. Nguồn: https://api.omicall.com/omicall-api/autocall/goi-tu-dong-thong-thuong-api-v2
- Trong OMIFlow cùng năng lực này là nút Marketing `AUTOCALL` (`omicall-omiflow` node-catalog 2.6).

## 7. Đọc hiện trạng — bằng API, không mở giao diện
`python <thư mục skill>/scripts/config_survey.py --out <scratch>/tenant_context.json --domain <domain>` → khoá `pbx` (đầu số + giờ làm việc, kịch bản cuộc gọi, Tương tác phím, nhóm nội bộ/bên ngoài, lời chào). Công cụ tổng đài của MCP (`list_groups`, `list_ivr`, `list_scripts`, `list_audio`, `list_hotlines`, `list_eval_criteria`) **trả 404 trên tenant miền `.omicrm.com` (10/2026)** — không dùng. Public API (mục 3–6) cần **apiKey của doanh nghiệp**: bí mật, agent không tự lấy hay nhập.

### API nội bộ của giao diện (token phiên, host `pbx-v1-stg.omicrm.com`, ✔ GET 10/2026)
| Đối tượng | Đọc | Ghi (thấy trong mã giao diện, **chưa chạy** — chỉ dùng khi user đồng ý, thử trên bản mới trước) |
|---|---|---|
| Đầu số | `GET public_number_of_tenant/list_active` → `payload.items[]` | `public_number_of_tenant/update/with_set_job_v2/<id>` |
| Kịch bản cuộc gọi | `GET call_script/get?page=0&size=0` → `payload.items[]` (hoặc `POST call_script/getV2?page=&size=`) | `call_script/add`, `call_script/update/<id>` |
| Tương tác phím | `POST key_interactive_script/get/list` body `{}`; `GET key_interactive_script/get/id/<id>` | `key_interactive_script/add`, `…/update/<id>` |
| Nhóm nội bộ | `POST internal_group/get/list`; `…/get/id/<id>` | `internal_group/add`, `…/update/<id>` |
| Nhóm bên ngoài | `POST outer_group/get/list` | `outer_group/add` |
| Lời chào | `POST greeting/get/list` | `greeting/text_to_speech_v2` (tạo TTS) |

Xoá (`…/delete/<id>`, `…/delete_many`) không bao giờ gọi.

Khuôn dữ liệu đáng nhớ:
- **Giờ làm việc nằm ở đầu số**: `configs = {allow_call_in, allow_call_out, default_script, working_days[], special_days[]}`; mỗi `working_days[i] = {weekday (2 = Thứ 2…; mã Chủ nhật: Cần xác nhận), type ("full_day" hoặc theo khung giờ), script, time_frames[{from, to, script}]}`. Định tuyến theo giờ = **mỗi ngày/khung giờ chọn một kịch bản cuộc gọi**; ngày lễ ở `special_days`. Đây là chỗ cấu hình "ngoài giờ → hộp thư thoại / callbot".
- Kịch bản cuộc gọi: `{script_name, extension (số nội bộ đại diện), enable_criteria, criterias[], scripts[{order, action_type, action_id, callbot_script_uuid}]}`; `action_type` đã thấy `Ivr_menu`, `Callbot`; mã giao diện còn có `Ring_group`, `Recording`, `Voice_mail`.
- Tương tác phím: `{script_name, script_number, greeting_id, greeting_short_id, time_out, max_failure, invalid_sound_id, action_type/action (kịch bản kết thúc), ivr_direct_menu_dial (chuyển khi bấm đúng số nội bộ), webhook{url, enable}, scripts[{ivr: "<phím>", action_type, action}]}` — **phím nằm ở `ivr`**, trường `key` để trống. `action_type` của phím: `Recording` (lời chào), `Callbot`, `Ring_group`, `Ivr_menu`, `Voice_mail`.
- Nhóm nội bộ: `{group_name, group_number, strategy, members[{agent_id, contact_id, order, timeout}], timeout, call_queue_config, max_wait_time, ring_back_id, is_forward_to_user_owner, is_forward_to_outer_group, outer_group_id, target_timeout_type, target_timeout, enable_criteria, criterias, repeat_config, agent_tags, agent_groups}` — có chuyển cho người phụ trách khách, chuyển sang nhóm bên ngoài, đích khi hết giờ chờ.
- Lời chào: `formality_code` `upload_file` | `call_bot` | (TTS), `content`, `voice`, `speed`, `duration`.

## 8. Kiểm thử
- Sau khi tạo: mở lại từng màn hình, đối chiếu từng phím, thành viên nhóm, lời chào, kịch bản gắn đầu số.
- Gọi thử chỉ khi user đồng ý và đưa số; xem Lịch sử cuộc gọi (đường đi, phím đã bấm); flow nhận webhook TTP → tab Lịch sử của flow.

## 9. Còn phải khảo sát
Danh sách loại **tiêu chí** (`criterias`) của kịch bản cuộc gọi và nhóm nội bộ (theo khách, theo người phụ trách), mã `weekday` của Chủ nhật, Nhóm bên ngoài, Hộp thư thoại (nghe ở đâu), cấu hình Truy vấn mở rộng, ghi âm. Khảo sát được mục nào thì ghi vào đây kèm ✔ và tháng.
