# Quy tắc dữ liệu huấn luyện Kho tri thức (Callbot NORMAL)

Áp dụng cho mọi nghiệp vụ. Mục tiêu: mô hình NLU của tenant nhận đúng ý định/thực thể từ **chữ do STT ghi ra trong cuộc gọi thật**.

## 1. Phạm vi và số lượng
- Chỉ gồm **ý định và thực thể kịch bản dùng**. Không thêm ý định cho câu hỏi đáp (dùng ý định "khách đặt câu hỏi" + thực thể chủ đề).
- **≥200 câu mới cho mỗi ý định và mỗi thực thể** (không tính câu mẫu hệ thống). Ý định chỉ đi kèm thực thể (đặt câu hỏi, lời hẹn có thời gian) được tính bằng tổng câu của các thực thể đó; ý định có cả câu không thực thể thì phần không thực thể cũng ≥200.
- Tenant trống → nạp dữ liệu mẫu hệ thống trước (`training/reset`), rồi bổ sung bằng file của dự án.
- **Gom vào một file, đẩy một lần** (mỗi lần nhập = huấn luyện lại toàn bộ 10–20 phút). Lần bổ sung sau: lọc trùng với mọi file đã đẩy (`--existing`).

## 2. Mẫu Excel hệ thống
File mẫu: `POST callbot/training/download_excel_template` → `https://cdn.omicrm.com/callbot/Import_training_data_template.xlsx` (tải công khai). Giữ nguyên file mẫu (sheet đầu, tiêu đề 2 dòng gộp ô), điền từ dòng 3:

| A | B | C | D | E | F | G | H–K, L–O |
|---|---|---|---|---|---|---|---|
| Câu khách nói | Tên ý định | **Mã** ý định | Tên thực thể | **Mã** thực thể | Đoạn thực thể (nằm nguyên vẹn trong cột A) | Kiểu: `STRING`/`NUMBER` | thực thể 2, 3 |

- Ý định/thực thể đã có: ghi đúng tên + mã đang có trong tenant (thực thể hệ thống trùng mã được dùng lại, không tạo trùng). Mã mới → hệ thống tạo mới.
- Hệ thống tự tính `start_char/end_char` từ cột F (lấy lần xuất hiện đầu) → đoạn thực thể không được lặp lại sớm hơn trong câu.

## 3. Câu phải giống chữ STT tổng đài
STT chỉ ra tiếng Việt, âm thanh điện thoại 8kHz, giọng vùng miền, khách nói tự nhiên. Bộ giả lập: `scripts/stt_noise.py`.
- **Phiên âm tiếng Anh/tên riêng** (luôn áp dụng): "ok" → "ô kê", "hotline" → "hót lai", "app" → "áp", "free" → "phri", "zalo" → "da lô", "online" → "on lai", "voucher" → "vau chơ", "ship" → "síp"... Tên sản phẩm/thương hiệu/ứng dụng của dự án: tự lập bảng phiên âm trong spec (`en_vi_extra`), mỗi tên 2–3 cách ghi.
- **Nghe nhầm âm gần** (~45% câu, 1–2 chỗ): gi/d ("giùm" → "dùm", "giấy" → "dấy"), "không" → "hông/hổng", "vậy" → "dậy/dị", "nghen" → "nhen", n/ng và t/c cuối ("chút" → "chúc", "biết" → "biếc"), hỏi/ngã ("bảo dưỡng" → "bảo dưởng"), "bao nhiêu" → "bao nhiu". Từ chuyên ngành của dự án hay bị nghe nhầm → thêm vào `confuse_extra`.
- **Không** đổi từ phổ biến mà mô hình ngôn ngữ của STT luôn sửa đúng ("rồi", "giờ"); **không** đổi làm câu lệch sang ý định khác ("quà" → "qua").
- **Lời nói tự nhiên** (ngoài đoạn thực thể): từ đệm đầu câu ("ờ ờ", "à à", "alo alo", "ừm", "dạ dạ"), lặp từ đầu ("em em ơi"), ngắt lời ("khoan khoan", "từ từ"), câu bị cắt chữ cuối (~10%).
- **Số**: trộn chữ số ("9 giờ", "ngày 28") và chữ ("hai mươi tám").
- **Tỉ lệ**: ~1/3 câu nghe rõ, ~2/3 có nhiễu. Phiên âm và nghe nhầm áp dụng cả trong đoạn thực thể (để khớp chữ STT); từ đệm, lặp, cắt câu chỉ ngoài đoạn.
- Viết thường, không dấu câu, không ký tự đặc biệt, không viết tắt kiểu nhắn tin ("ko", "dc", "k").
- Câu đã đẩy trước đó có từ tiếng Anh viết chuẩn → thêm biến thể phiên âm (`augment_existing_en`).

## 4. Câu tự nhiên, đúng vai
- **Lõi câu**: ≥30 lõi mỗi ý định, ≥15 mẫu mỗi thực thể, viết theo **câu trả lời thật của khách ở từng bước gọi** (khách đáp câu hỏi xác nhận, câu mời, câu hỏi ngày...). Dùng ô trống `{s}` (khách tự xưng), `{b}` (khách gọi bot), `{x}` (chủ ngữ hỏi), `{v}` (giá trị thực thể), `{tên_slot}` (danh sách riêng của dự án) để nhân biến thể.
- **Vai xưng hô**: bot xưng "em" → khách gọi bot "em" (anh, chị, tui, tôi) hoặc "con" (chú, cô); mỗi câu một vai thống nhất.
- **Đầu/đuôi câu tách theo loại**: câu hỏi ("cho anh hỏi", "ủa", "… vậy em", "… hả em") khác câu nói thường ("dạ", "ừ", "… nha em", "… nghen em"); đầu câu riêng theo ý định (không "thôi" trước câu xác nhận, không "cho hỏi" trước câu nói thường).
- **Chống câu gượng**: không gọi bot hai lần ("em ơi … em"), không chồng tiểu từ ("nha nghen", "hả hả"), không đặt từ đệm khi lõi đã mở đầu bằng "ừ/dạ/ờ", không thêm đuôi khi lõi kết bằng tiểu từ, không ghép "{s} em" thành cụm sai nghĩa ("cho chị em").

## 5. Tách rõ ý định dễ lẫn
| Dễ lẫn | Cách tách |
|---|---|
| Đồng ý ↔ lời hẹn ↔ xác nhận đúng | Đồng ý: chấp nhận, không có mốc thời gian ("được em", "ok để anh qua"). Lời hẹn: luôn có mốc thời gian (đánh dấu thực thể thời gian). Xác nhận đúng: trả lời câu hỏi "có phải … không" ("đúng rồi", "anh đây") |
| Từ chối ↔ từ chối dịch vụ ↔ xác nhận sai | Từ chối: "không" ngắn, trả lời câu có/không. Từ chối dịch vụ: kèm lý do không dùng dịch vụ. Xác nhận sai: sai người/nhầm số |
| Gọi lại sau ↔ lời hẹn | Gọi lại sau: đang bận, hẹn nói chuyện sau. Lời hẹn: hẹn làm việc nghiệp vụ (ghé, thanh toán...) có thời gian |
| Câu hỏi về thời hạn ↔ lời hẹn | Câu hỏi luôn có từ hỏi ("ngày nào", "bao giờ", "được không"); không đưa câu kiểu "để tuần sau được không" vào câu hỏi |
| Lặp lại ↔ câu hỏi | Lặp lại: không nghe rõ, nói lại; không hỏi nội dung mới |

## 6. Kiểm tra trước khi gửi duyệt
Không trùng (kể cả với file đã đẩy) · không dấu câu · đoạn thực thể nằm nguyên trong câu · đủ số lượng · không còn từ tiếng Anh chưa phiên âm · đọc 30 câu ngẫu nhiên mỗi ý định/thực thể, sửa lõi gượng rồi sinh lại. `gen_training.py` in báo cáo các mục này.

## 7. Sau khi đẩy
`upload_excel/status`: `successTotalRecord == total`, `errorTotalRecord == 0`; số thực thể tăng đúng số thực thể mới; lịch sử huấn luyện chạy tới `SUCCESS` (theo dõi bằng `training/history/search`). Ghi lại file đã đẩy để lần sau lọc trùng.
