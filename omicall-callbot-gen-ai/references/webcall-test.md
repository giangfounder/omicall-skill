# Gọi thử kịch bản bằng web call (OMICallSDK web v3)

Dùng ở `references/playbook.md` Bước 6 ý 3 (gọi thử) sau khi kịch bản đã lưu, **xuất bản** và có số gọi trỏ vào nó. Mỗi lần chạy là một cuộc gọi thật (tính phút tổng đài): chỉ chạy khi user đồng ý.

Hai chế độ của `scripts/webcall_test.py`:
- `open`: mở trang web call có phụ đề trực tiếp, **user tự nói** bằng micro thật.
- `auto`: agent tự kiểm thử, phát câu khách (giọng đọc edge-tts) vào cuộc gọi theo `plan.json`, chờ bot nói xong mới nói câu tiếp, gác máy, lưu phụ đề.

## 1. Tham số cấu hình (thay đổi theo từng tenant, không có giá trị mặc định)

| Tham số SDK | Cờ của script | Là gì | Lấy ở đâu |
|---|---|---|---|
| `sipRealm` | `--domain` | Realm SIP của tenant | Tên tenant, phần trước `.omicrm.io` (ví dụ `abc` khi domain là `<tên>.omicrm.io` với tên = `abc`). Đăng ký báo sai mật khẩu dù mật khẩu đúng → realm có thể khác tên domain: Cần xác nhận với quản trị tổng đài. |
| `sipUser` | `--ext` | Số máy nhánh dùng làm "điện thoại" gọi đi | MCP `list_extensions` / `get_extension`. **Kết quả `list_extensions` có trường `password` (mật khẩu SIP dạng chữ thường): không in, không ghi log, không chép vào báo cáo; chỉ lấy `sip_user`, `enabled`, `full_name`.** Nên dùng một máy nhánh riêng cho kiểm thử, không dùng máy của nhân viên đang trực (trang đăng ký máy nhánh này trên trình duyệt, cuộc gọi đến máy đó có thể đổ về trang). |
| `sipPassword` | (kho bí mật) | Mật khẩu SIP của máy nhánh, **không phải** mật khẩu đăng nhập OMI | Trang quản lý máy nhánh của tenant hoặc quản trị tổng đài. User tự nhập một lần bằng `webcall_test.py setup` (ô ẩn, lưu vào Windows Credential Manager / Keychain / keyring); hoặc biến môi trường `OMI_SIP_PASSWORD`. Agent không nhận mật khẩu qua chat, không ghi vào file trong skill, repo hay báo cáo. |
| `phoneNumber` | `--number` | Số mà trang gọi tới | Hotline có định tuyến cuộc gọi vào đúng kịch bản cần thử (MCP `list_hotlines` / `get_hotline`, `tenant_context.json` mục `hotlines`, `existing_artefacts[].hotline_attached`). Gắn hotline vào kịch bản chỉ làm khi user đồng ý. Số 2–7 chữ số được SDK coi là gọi nội bộ (máy nhánh); gọi thẳng vào kịch bản mà không qua hotline: Cần xác nhận. |
| `sdkVersion` | `--sdk-version` | Phiên bản file `https://cdn.omicrm.com/sdk/web/<ver>/core.min.js` | Mặc định `3.0.35` (đã chạy thử). Danh sách phiên bản: `https://api.omicall.com/sdk/web-sdk/v3-changelog`. |
| `botName` | `--bot-name` | Tên hiện trên trang và trong phụ đề | Tuỳ ý, ví dụ tên kịch bản. |
| (plan) | `--plan` | Các câu khách cho chế độ `auto` | Tự soạn từ ca kiểm thử của kịch bản, mục 3. |
| (giọng) | `--voice` | Giọng đọc câu khách (MCP `text_to_speech` / `generate_tts_audio` của OMI trả 404 khi thử 2026-10-28 → dùng edge-tts) | edge-tts: `vi-VN-NamMinhNeural` (nam, mặc định) hoặc `vi-VN-HoaiMyNeural` (nữ). `plan.json` có trường `voice` thì dùng trường đó. |

Script ghi các trường trên vào `config.json` trong thư mục chạy (ở `OMI_SCRATCH`), trang đọc rồi script **xoá file ngay khi đăng ký xong**. Thiếu trường bắt buộc → trang báo "Thiếu cấu hình" kèm tên trường.

## 2. Điều kiện để gọi được

- Gói dịch vụ có tính năng gọi trên web (`direct_call_on_web_app`) và máy nhánh được phép kết nối từ web; thiếu → SDK trả `Feature not available` hoặc `Dont have permission to call`.
- Kịch bản đã **xuất bản** và hotline ở `--number` đang trỏ vào nó (bản nháp không chạy khi gọi vào).
- Google Chrome 135+ (phụ đề lời bot cần `SpeechRecognition.start(track)`; bản cũ chỉ chép được lời khách). Nhận dạng chạy trên máy chủ Google: cần mạng, chữ có thể khác bản STT của OMI. Browser pane của Claude desktop **không dùng được** (chặn micro, không có nhận dạng giọng của Google, lỗi `network`).
- `pip install websocket-client edge-tts`. Đăng ký SIP chạy được từ `localhost` (không vướng CORS).

## 3. plan.json cho chế độ auto

```json
{
  "name": "Ca 1: hỏi dịch vụ rồi chào kết thúc",
  "voice": "vi-VN-NamMinhNeural",
  "turns": [
    { "text": "A lô, chào em." },
    { "text": "Cho anh hỏi bên em đang hỗ trợ những dịch vụ gì vậy em?" },
    { "text": "Ừ, anh hiểu rồi. Cảm ơn em nhé, chào em." }
  ]
}
```
- Mỗi `turn` là một lượt khách, nói sau khi bot nói xong (bot nói ≥ 0,3 giây rồi im 1,6 giây; bot không nói trong 12 giây thì khách nói luôn). Sau lượt cuối chờ bot đáp rồi gác máy; bot tự cúp trước thì dừng sớm (`ended_early`).
- Lượt khó: `{"text": "...", "bargeMs": 1500}` nói chen khi bot mới nói được 1,5 giây (thử bot có dừng và nghe khách không); `{"silence": 10000}` (không có `text`) khách im lặng 10 giây (thử bot nhắc lại hoặc kết thúc lịch sự). Sự kiện tương ứng: `barge_in`, `bot_turn_barge`, `silent`.
- Viết câu khách như người thật nói qua điện thoại: ngắn, một ý, tiếng Việt đầy đủ, số viết bằng chữ. Mỗi ca thử một nhánh của kịch bản (đúng ý định, thu đủ biến, chuyển máy, kết thúc).

### Ca khách AI (Claude soạn câu khách theo từng lượt)

Ca có trường `persona` thì không soạn câu sẵn: sau mỗi lượt bot, script lấy câu bot (phụ đề Chrome), gửi Claude (`--model`, mặc định `claude-opus-5-5`, effort `low`, bật dự phòng `fallbacks: "default"`) cùng vai, mục tiêu, dữ liệu của ca; Claude trả đúng một câu khách, edge-tts đọc thành giọng (có bộ nhớ đệm) rồi phát vào cuộc gọi. Khách tự chào và kết thúc khi xong mục tiêu, bot chào kết thúc, hoặc hết `max_turns`.
```json
{
  "id": "ai01-dat-hang-doi-y",
  "name": "Khách AI: đặt hàng rồi đổi số lượng",
  "persona": "Khách mua lẻ, nói ngắn, hơi vội",
  "goal": "Đặt hai hộp sản phẩm mẫu; sau khi tổng đài xác nhận thì đổi thành năm hộp; trả lời đủ rồi chào",
  "facts": { "ten": "Minh", "noi_o": "quận Một", "so_luong_sau_khi_doi": "năm hộp" },
  "max_turns": 8,
  "expect": ["Bot xác nhận năm hộp sau khi khách đổi ý"]
}
```
- Claude chỉ dùng dữ liệu trong `facts`; bot hỏi thứ không có thì khách nói chưa rõ (không bịa). `facts` chỉ chứa dữ liệu giả hoặc từ tài liệu nghiệp vụ, không dùng thông tin cá nhân của khách thật.
- Cần khóa Claude API: user tự đặt biến môi trường `ANTHROPIC_API_KEY` (hoặc `ant auth login`); agent không nhận khóa qua chat. Thiếu khóa → script dừng trước khi gọi. `pip install anthropic`.
- Mỗi lượt chậm thêm khoảng 2–5 giây (Claude + giọng đọc); bot có thể nhắc "anh còn nghe không" trong lúc chờ, ghi nhận nhưng không tính là lỗi kịch bản.
- Phụ đề lời bot sai chữ thì Claude có thể hiểu sai: khách được dặn hỏi lại như người thật; khi chấm, lỗi do nhận dạng ghi "Cần nghe lại".
- Kết quả khác nhau giữa các lần chạy: dùng ca soạn sẵn (`turns`) để chống hồi quy, ca khách AI để dò lỗi hội thoại tự nhiên. Một thư mục ca có thể trộn cả hai loại.

## 4. Lệnh

```bash
python "<thư mục skill>/scripts/webcall_test.py" setup --domain <domain> --ext <máy nhánh>      # user tự chạy, một lần
python "<thư mục skill>/scripts/webcall_test.py" auto  --domain <domain> --ext <máy nhánh> --number <hotline> --plan <scratch>/plan.json --bot-name "<tên kịch bản>"
python "<thư mục skill>/scripts/webcall_test.py" open  --domain <domain> --ext <máy nhánh> --number <hotline>
```
`--plan` nhận một file hoặc một thư mục (mỗi file `*.json` một ca, chạy theo thứ tự tên, nghỉ `--gap` giây giữa hai cuộc gọi). Kết quả `auto` ở `<OMI_SCRATCH>/webcall-<thời điểm>/`:
- `suite.json`: mỗi ca `id`, `name`, `status` (`done` | `error`), `error`, `callUuid`, `ended_early`, đường dẫn phụ đề.
- `results/<id>.txt`: phụ đề `[mm:ss] BOT|KHÁCH: …`.
- `results/<id>.json`: `plan` (kèm `goal`, `expect`) + `events` có mốc giây: `accepted`, `bot_turn` kèm `spokeMs`, `say`, `ended_early`, `hangup_by_test`, `error`. Đối chiếu bản ghi chính thức, nhãn phân loại, biến đã thu bằng MCP `get_call_detail(callUuid)` hoặc `search_calls`.

## 5. Đọc kết quả

Với từng ca, so phụ đề `results/<id>.txt` với thiết kế kịch bản: câu mở đầu, nhận đúng ý định, hỏi đủ biến theo thứ tự, không đọc ra chữ nội bộ (mô tả node, tên biến, chỉ dẫn hệ thống), xưng hô đúng, kết thúc đúng trình tự END_CALL. Câu nghi lỗi nhưng có thể do nhận dạng sai chữ → ghi "Cần nghe lại bản ghi", không kết luận là lỗi kịch bản.

## 6. Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `Chưa có mật khẩu SIP` | User chạy `setup` cho đúng `--domain` và `--ext`. |
| `SIP_USER_INACTIVE` | SDK trả CÙNG mã này cho cả máy nhánh bị tắt LẪN **sai mật khẩu SIP** (`password_incorrect`). Máy nhánh vẫn gọi được ở nơi khác → gần như chắc là mật khẩu lưu sai: user chạy `setup` lại. |
| `Dont have permission to call` / `Feature not available` | Gói hoặc máy nhánh chưa được phép gọi trên web (mục 2). |
| `Bot không nhấc máy trong 45 giây` | Hotline chưa trỏ vào kịch bản, kịch bản chưa xuất bản, hoặc số sai. |
| Có tiếng nhưng không có phụ đề lời bot | Chrome cũ hơn 135, hoặc đang chạy trong browser pane. |
| Lời khách bị gộp nhiều lượt vào một dòng | Đã xử lý: câu nháp kẹt quá 3 giây được chốt và mở phiên nhận dạng mới. Còn gặp thì xem `events` để biết thời điểm từng lượt. |

## 7. Bộ ca kiểm thử cho vòng lặp (gọi thử, sửa, gọi lại)

Mỗi ca một file, `id` ngắn không dấu, `expect` là điều kiểm được bằng tai (lời bot), không phải trạng thái nội bộ:
```json
{
  "id": "ca03-chuyen-may",
  "name": "Khách đòi gặp nhân viên",
  "goal": "Ý định yêu cầu gặp nhân viên dẫn tới TRANSFER_CALL",
  "expect": [
    "Bot xác nhận sẽ chuyển máy cho nhân viên",
    "Bot không hỏi thêm thông tin sau khi khách đã đòi gặp nhân viên",
    "Cuộc gọi được chuyển, bot không tự cúp máy"
  ],
  "turns": [
    { "text": "A lô." },
    { "text": "Em cho anh nói chuyện với nhân viên được không?", "expect": "chuyển máy" }
  ]
}
```
Bộ ca tối thiểu (bỏ ca nào kịch bản không có nhánh tương ứng):

| Nhóm | Ca |
|---|---|
| Mở đầu | Khách chỉ "A lô": bot chào đúng `start_call_instruction` và dẫn vào câu hỏi đầu |
| Ý định | Mỗi ý định một ca, câu khách diễn đạt khác câu mẫu trong mô tả ý định |
| Thu thông tin | Đưa đủ biến theo thứ tự; đưa thiếu (bot phải hỏi lại); sửa thông tin đã nói |
| Kho tri thức | Câu hỏi có trong tài liệu (bot trả lời đúng nội dung); câu hỏi không có (bot không bịa) |
| Chuyển máy | Khách đòi gặp nhân viên; nhánh nghiệp vụ dẫn tới chuyển máy |
| Ngoài phạm vi | Câu không liên quan nghiệp vụ → `bot_can_not_answer` → chuyển máy |
| Từ chối, bận | Khách từ chối hoặc hẹn gọi lại: bot tôn trọng, không cúp ngay, hỏi khách còn cần hỗ trợ gì không; chỉ kết thúc sau khi khách xác nhận không còn (playbook mục *Kết thúc và chuyển cuộc gọi*) |
| Kết thúc | Khách nói hết nhu cầu: bot hỏi còn cần hỗ trợ gì không, khách xác nhận hết rồi mới đúng trình tự cảm ơn → chúc → xin phép kết thúc → tạm biệt |
| Khó: đổi ý | Khách sửa số lượng, sản phẩm hoặc thông tin đã nói: bot xác nhận theo giá trị mới |
| Khó: dồn thông tin | Khách nói nhiều biến trong một câu: bot không hỏi lại thứ đã có |
| Khó: mơ hồ | Khách nói không rõ ("cái loại hôm trước"): bot hỏi làm rõ, không đoán |
| Khó: hỏi giá, khuyến mãi | Bot chỉ nói thông tin có trong Kho tri thức, không bịa |
| Khó: đổi chủ đề | Đang tư vấn chuyển sang đặt hàng (hoặc ngược lại): bot theo kịp, không lặp lại từ đầu |
| Khó: im lặng | Lượt `silence`: bot hỏi lại một lần, vẫn im mới kết thúc lịch sự |
| Khó: chen ngang | Lượt `bargeMs`: bot dừng, trả lời đúng câu khách vừa chen |
| Khó: ngoài ngành | Hỏi chuyện không liên quan: bot từ chối khéo hoặc chuyển máy theo thiết kế |

Ca có chuyển máy: cuộc gọi đổ sang máy nhánh nhân viên. Nhắc user trước khi chạy để nhân viên biết đó là cuộc gọi thử, hoặc chọn máy nhánh đích dành cho thử nghiệm.

## 8. Khuôn báo cáo kiểm thử

Ghi vào `<SCRIPT_NAME>_Knowledge/test-report.md`, gửi user bản tóm tắt cùng khuôn giao của Bước 6:

1. **Tổng quan**: kịch bản (tên, id, version cuối), hotline và máy nhánh đã dùng, số vòng, số cuộc gọi, kết quả cuối (`x/y` ca Đạt).
2. **Bảng kết quả**: hàng là ca, cột là vòng (Đạt / Không đạt / Cần nghe lại / Chưa chạy).
3. **Thay đổi đã sửa** theo từng vòng: chỗ sửa (prompt, ý định, biến, node, Kho tri thức), lý do, ca liên quan, version sau khi lưu.
4. **Lỗi còn lại**: ca, `expect` chưa đạt, câu trích phụ đề, nguyên nhân dự đoán, đề xuất cho người quyết định.
5. **Cần nghe lại**: ca, mốc thời gian, `callUuid` để mở bản ghi âm.
6. **Cần xác nhận**: dữ liệu nghiệp vụ còn thiếu, giả định agent đã tự chọn.
7. **Phụ lục**: đường dẫn thư mục chạy (`suite.json`, `results/`) của từng vòng.

Báo cáo không chứa mật khẩu SIP, token hay số điện thoại cá nhân của khách thật.

## 9. Ghi chú kỹ thuật SDK v3 (dùng khi sửa trang)

- `core.min.js` không có giao diện. Sự kiện `OMICallSDK.on(...)`: `register` (`status`: `connecting` / `connected` / `disconnect`), `connecting`, `ringing`, `accepted`, `on_calling` (mỗi giây, `call.callingDuration.text`), `ended`.
- Đối tượng cuộc gọi: `end()`, `mute(cb)` (tự đảo trạng thái, `cb(micBật)`), `hold()`, `dtmf(phím)`, `streams.remote` / `streams.local` (MediaStream), `uid`, `uuid`, `isAccepted`.
- Tiếng bot chỉ phát khi trang có `<audio id="${call.uid}-remote" autoplay>`: tạo ở sự kiện `connecting`.
- SDK dò micro bằng `enumerateDevices` ngay khi tải và gọi `getUserMedia` khi bắt đầu gọi; chế độ `auto` (`webcall/autotest.js`) thay hai hàm này **trước khi** nạp SDK để micro là luồng phát giọng đọc.
