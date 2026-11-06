# OMICall — AI Assistant, Voice Insights, Chat Insights (dùng chung mọi tenant)

Nhãn nguồn: **✔ UI 10/2026** = đã xem trên giao diện tenant thật (chỉ xem, không lưu); **✔ flow** = đã dựng flow thật dùng kết quả; **[tài liệu]** = hướng dẫn trên omicrm.io; **[API công khai]** = `api.omicall.com` (xác thực bằng apiKey doanh nghiệp). Chưa có dữ liệu thì ghi **Cần khảo sát**, không suy đoán.

## 0. Ba lớp AI và khác nhau ở đâu
| Lớp | Đầu vào | Đầu ra | Dùng khi |
|---|---|---|---|
| **AI Assistant** (Cuộc gọi / Đa kênh) | từng cuộc gọi (hoặc hội thoại) thoả phạm vi | tóm tắt, ghi chú, tag, gợi ý giá trị thuộc tính phiếu/khách, biến `{{ca_summarize}}`, `{{ca_ai_assistant}}` | cần dữ liệu nghiệp vụ từ cuộc gọi đổ vào CRM/OMIFlow |
| **Voice Insights** | cuộc gọi **có ghi âm** | điểm chất lượng theo thông số và bộ tiêu chí có trọng số | QA/chấm điểm nhân viên, phát hiện từ khoá, từ chối dịch vụ |
| **Chat Insights** | hội thoại đa kênh | điểm theo bộ tiêu chí (theo nhân viên) | QA kênh chat |

Gói dịch vụ (`get_service_package`, module `ai`) có cờ `omi_call_assistant`, `omi_call_assistant_multichannel`, `call_analysis`, `conversation_history_analyzed`, `api_speech_to_text`, `api_call_analysis` và giới hạn `total_call_assistant`, `total_social_assistant` → kiểm trước khi hứa với khách.

## 1. AI Assistant ✔ UI 10/2026
Cấu hình → AI → **AI Assistant** (`/config/ai/call-assistant/criteria`): hai tab **Cuộc gọi** và **Đa kênh**; nút Thêm mới hiện quota dạng `N/M` trợ lý.

Mở một trợ lý (`/config/ai/call-assistant/config-criteria/edit/<id>`) gồm 2 bước:
1. **Thông tin chung** — Hoạt động/Ngưng hoạt động, Tên trợ lý*, **Mục đích cuộc gọi** (lấy từ Cấu hình → Doanh nghiệp → Cuộc gọi → Mục đích cuộc gọi), Mô tả, **Cuộc gọi áp dụng*** (Cuộc gọi đi / Cuộc gọi đến), **Nhân viên**, **Nhóm nhân viên**, **Đầu số**. Cuộc gọi không thoả phạm vi → không được phân tích, biến rỗng.
2. **Cấu hình trợ lý cuộc gọi** — danh sách chức năng, "Thêm mới" chọn một trong:
   - **Tổng hợp nội dung cuộc gọi** (mặc định): ô **"Hướng dẫn các bước tổng hợp"*** viết theo cú pháp `- Tên trường: (mô tả)` mỗi dòng; chip **Gợi ý** chèn sẵn trường (Tiêu đề, Nội dung, Tên khách hàng, Email, Số điện thoại, Tên công ty, Bước tiếp theo, Từ khóa, Mức độ ưu tiên); công tắc **"Tự động điền kết quả phân tích vào ghi chú - Tag"** (cập nhật ghi chú và tag trong cửa sổ gọi).
   - **Phân loại Tag**: mỗi tag có mô tả/hướng dẫn; tag bật "gán tự động và không cho nhân viên thay đổi" thì nhân viên không gỡ được [tài liệu].
   - **Tạo phiếu ghi** / **Tạo khách hàng**: mỗi thuộc tính có hướng dẫn trích xuất riêng; khi nhân viên tạo phiếu/khách từ cửa sổ gọi, form được **gợi ý sẵn** giá trị đã bóc [tài liệu]. Cấu hình chi tiết từng thuộc tính: Cần khảo sát.

Nguồn tài liệu: https://omicrm.io/post/detail/gioi-thieu-omicall-assistant-tro-ly-dac-luc-cho-moi-cuoc-goi-post121

Quy tắc viết hướng dẫn ✔ flow:
- Giữ nguyên dòng cũ, chỉ thêm dòng mới cùng cú pháp; **chép bản gốc trước khi sửa** (cấu hình dùng chung cho mọi cuộc gọi thoả phạm vi).
- Trường sẽ ghi vào thuộc tính kiểu danh sách: `Chỉ ghi MỘT trong các giá trị: <A>, <B>, …, không có thì ghi: Không xác định` — tập giá trị khớp nguyên văn thuộc tính đích (`omicall-crm-config`).
- Kết quả **ghi trễ** sau khi cuộc gọi kết thúc → flow đọc kết quả phải Trì hoãn trước.

## 2. Dùng kết quả AI Assistant ✔ flow
- Không cần OMIFlow: bật "Tự động điền… ghi chú - Tag" và chức năng Tạo phiếu/Tạo khách (nhân viên xác nhận trên cửa sổ gọi). Ưu tiên cách này khi nhân viên còn ngồi xem cuộc gọi.
- Cần tự động hoàn toàn (không người xác nhận) → OMIFlow: chèn `{{ca_ai_assistant}}` vào mô tả phiếu (mẫu B5), hoặc bóc từng trường bằng nút LLM rồi gán thuộc tính; trường danh sách rẽ nhánh theo giá trị (`omicall-omiflow` `references/ui-build-and-test.md` mục 7).
- Điều kiện/trigger OMIFlow có nhóm **AI Assistant – Cuộc gọi/Đa kênh**, **Voice Insights**, **Chat Insights**; trigger `GENERAL` có đối tượng "cuộc gọi AI phân tích". Danh sách thuộc tính từng nhóm: Cần khảo sát.

## 3. Voice Insights ✔ UI 10/2026
Cấu hình → AI → **Voice Insights** (`/config/ai/call-analysis/analysis-parameters`), 4 tab: **Thông số phân tích**, **Bộ tiêu chí**, **SmartCall**, **Trọng số**.
- 14 thông số [tài liệu chấm điểm 11/2026], 2 nhóm: **Âm thanh** (Độ trễ tín hiệu, Thời gian phản hồi, Tốc độ thoại, Cảm xúc âm thanh, Tạp âm, Cường độ âm thanh, Độc thoại) và **Ngôn ngữ tự nhiên** (Cảm xúc, Lịch sự, Từ khóa, Câu hỏi, Lời hẹn, Đánh giá dịch vụ, Từ chối dịch vụ). Mỗi thông số có "Đối tượng áp dụng" (biểu tượng góc thẻ: hai người = cả hai bên, người xanh dương = nhân viên, xanh lá = khách) và ngưỡng. Cách chấm từng thông số, Đánh giá chất lượng, Bộ tiêu chí, SmartCall: mục 3b.
- Điểm tiêu chí = trọng số các thông số; điểm bộ tiêu chí = trọng số các tiêu chí; trọng số nâng cao theo điều kiện VÀ/HOẶC. Bộ tiêu chí gắn **mục đích cuộc gọi**, giới hạn được theo nhân viên/nhóm. **Chỉ cuộc gọi có ghi âm** được phân tích [tài liệu: https://omicrm.io/post/detail/phan-tich-cuoc-goi-voi-ai-post110 — bài 2023–2024, tên menu cũ "Phân tích cuộc gọi"].
- → Muốn chấm theo loại cuộc gọi: tạo giá trị **Mục đích cuộc gọi** trước (Cấu hình → Doanh nghiệp → Cuộc gọi), rồi mới tạo bộ tiêu chí.
- Tab SmartCall: cách chấm ở mục 3b; form trên giao diện: Cần khảo sát.
- Trạng thái xử lý mỗi cuộc gọi: cột **Trạng thái phân tích** trên danh sách cuộc gọi. Cấu hình mới chỉ áp dụng cho cuộc gọi phân tích sau thời điểm đổi; chấm lại cuộc gọi cũ: chuột phải cuộc gọi → **Phân tích lại**. Phân tích cả cuộc gọi vào, ra và cuộc gọi Callbot (khi đó phía "nhân viên" là bot → điểm phản ánh giọng và kịch bản của bot).

### 3a. Dựng Voice Insights trên giao diện ✔ UI 10/2026
Tenant mới có thể **chưa có thông số nào** (danh sách trống) — phải tự thêm. Thứ tự: thông số → mục đích cuộc gọi → bộ tiêu chí.

**Thông số phân tích** — nút Thêm mới mở bảng chọn thẻ thông số (lọc Tất cả / Ngôn ngữ tự nhiên / Âm thanh). 12 thẻ gắn **PRO**, chỉ **Lịch sự** không PRO; gói chưa mở PRO → bấm thẻ báo "Bạn không có quyền sử dụng tính năng này" (kiểm trước khi hứa với khách). (Giao diện 10/2026 đếm được 13 thẻ, tài liệu 11/2026 liệt kê 14 — thẻ thiếu: Cần khảo sát.) Bấm thẻ → ngăn "Thêm thông số" bên phải → nút **Thêm mới** lưu, bảng chọn vẫn mở để thêm tiếp (thẻ đã thêm bị mờ).
| Thông số | Ô bắt buộc trong form |
|---|---|
| Từ khóa | Áp dụng tất cả / Theo đối tượng; danh sách dòng **Từ khóa** + **Phiên âm** (tuỳ chọn, ≤48 ký tự), nút + thêm dòng |
| Cảm xúc âm thanh | **Khoảng chênh lệch*** (delta; gợi ý trên form: tốt nhất từ 30 delta) |
| Độ trễ tín hiệu | **Độ trễ tín hiệu*** (ms) |
| Thời gian phản hồi | **Thời gian phản hồi*** (giây) |
| Tốc độ thoại | **Tốc độ thoại*** (từ/phút) + tuỳ chọn trừ điểm khi lớn hơn / nhỏ hơn giá trị chênh lệch |
| Lịch sự, Cảm xúc, Tạp âm, Câu hỏi, Lời hẹn, Độc thoại, Cường độ âm thanh | chỉ ô chọn đối tượng (Nhân viên / Khách hàng) |
| Đánh giá dịch vụ, Từ chối dịch vụ | chỉ đối tượng Khách hàng |

**Mục đích cuộc gọi** — `/config/company/call/list`, khối "Mục đích cuộc gọi" → Chỉnh sửa → danh sách ô **Tên mục đích** (≤48 ký tự, nút + thêm dòng) → Cập nhật. Có giá trị thì **nhân viên phải chọn mục đích trước khi gọi** → báo khách trước.

**Bộ tiêu chí** — `/config/ai/call-analysis/evaluation-criteria/add/new`, 2 bước:
1. Thông tin chung: **Tên bộ tiêu chí*** (≤48), Mục đích cuộc gọi (mặc định "Không áp dụng"), Mô tả (≤256), **Khung điểm** (Thêm khung điểm → Tiêu đề*, Từ*, Đến*; ví dụ trên form "0–30 = Không đạt"), Nhân viên / Nhóm nhân viên (trống = áp dụng tất cả) → Tiếp tục.
2. Cấu hình tiêu chí (`…/evaluation-criteria/config/list`): cột trái danh sách tiêu chí, trọng số tự chia đều (link "Cấu hình" để chỉnh, tổng 100%); chọn tiêu chí → ô **Tiêu chí** (tên) + "Thêm thông số" mở ngăn điều kiện. Danh mục điều kiện bên phải: Tuỳ chỉnh (Chủ đề Ý định/Mong muốn, Tự định nghĩa), Cơ bản (Thời lượng cuộc gọi, Tỉ lệ thoại, Bao gồm từ khoá, Không bao gồm từ khoá), Ngôn ngữ tự nhiên (Lịch sự, Cảm xúc, Đánh giá dịch vụ, Từ chối dịch vụ, Câu hỏi, Lời hẹn), Âm thanh (Độc thoại, Thời gian phản hồi, Cảm xúc âm thanh, Cường độ âm thanh…). Mỗi điều kiện: Đối tượng (Tất cả / Nhân viên / Khách hàng — **giữ lựa chọn của lần trước**, kiểm lại), giá trị cần đếm (Lịch sự: Lịch sự/Không lịch sự; Cảm xúc: Vui vẻ/Bình thường/Khó chịu; Đánh giá dịch vụ: Hài lòng-Khen/Trung lập/Chê), **Số lần** hoặc **Phần trăm xuất hiện** với Trong khoảng Từ–Đến (bỏ trống Đến = "Trên X"), tuỳ chọn khung thời gian, "Thêm trường hợp khác". Trọng số các thông số trong tiêu chí tự chia đều. Nút **Thêm mới** cuối trang lưu cả bộ.
- **Tự định nghĩa** ✔ UI 11/2026 — tiêu chí chấm bằng prompt LLM (form ghi "Model sử dụng: gpt-4o-mini"). Form: Đối tượng áp dụng chỉ **Nhân viên / Khách hàng** (không có Tất cả), **Tên thông số*** (≤256), **Mô tả** = prompt (nhiều dòng được, lưu nguyên văn), dải chip "Gợi ý" tên mẫu (Tương tác và giao tiếp, Khả năng giải quyết vấn đề, Thái độ và ngôn từ…). Không có ô ngưỡng/số lần; trong tiêu chí thẻ hiện "Tự định nghĩa" + tên thông số, ô trọng số mặc định 100%.
- **Sửa bộ đã có** ✔ UI 11/2026: bấm thẻ bộ trong danh sách → `…/evaluation-criteria/edit/{id}` mở thẳng bước 2; "Thêm mới" cột trái tạo tiêu chí trống ("Chưa có dữ liệu"), trọng số các tiêu chí **tự chia lại đều** (3 → 4 tiêu chí = 25% mỗi cái, ghi đè tỉ lệ cũ — báo user); nút cuối trang là **Cập nhật** (lưu cả bộ, quay về danh sách, toast "Cập nhật thành công"). Thêm cùng tiêu chí vào nhiều bộ: làm lần lượt từng bộ.
- **Chấm thử file ghi âm ngoài tổng đài** ✔ UI 11/2026: AI (thanh trên) → API → tab **Voice Insights** (`/ai/api/call-analysis/list`), nút **Tải lên File ghi âm** mở ngăn kéo-thả (≤50MB/file) → nút **Tải lên (n)**. Dòng mới hiện "Đang xử lý" (file 3–4 phút chờ hơn 1 phút), xong thành "Thành công" kèm cước (~229 VND cho 3:48); bộ lọc theo từng bộ tiêu chí phía trên bảng. Trong browser pane không có công cụ đính file: bấm vùng chọn file mở hộp Open của Windows → gõ đường dẫn đầy đủ vào ô File name qua Windows-MCP, Enter. "Kho dữ liệu mẫu" chỉ là thư viện mẫu tiêu chí, không tải file được.
- Gotcha: bấm vào thẻ điều kiện đã thêm mở "Chỉnh sửa" (nút Cập nhật/Đóng), không phải Thêm thông số — nút "Thêm thông số" nằm dưới thẻ cuối.
- Danh sách bộ tiêu chí hiện tên, số tiêu chí, khung điểm, mục đích, phạm vi nhân viên. Trên một số tenant tab thứ 4 là "Kho dữ liệu mẫu" thay cho "Trọng số" (Cần khảo sát).

### 3b. Cách hoạt động và chấm điểm [tài liệu chấm điểm 11/2026]
Nguồn: tài liệu nội bộ OMICRM "Voice Insights – Cách hoạt động và chấm điểm" (11/2026). Chưa đối chiếu bằng dữ liệu tenant trừ chỗ ghi rõ.

**Quy trình 4 bước** sau khi cuộc gọi kết thúc và có ghi âm: (1) tách kênh — ghi âm 2 kênh riêng nhân viên/khách, nên biết câu nào ai nói kể cả khi nói chồng; (2) âm thanh — cắt mỗi kênh thành đoạn thoại (một lần nói liền mạch), STT kèm mốc thời gian từng tiếng, đo SNR, dB, Hz, cảm xúc, lịch sự; (3) ngôn ngữ — gắn nhãn câu hỏi/lời hẹn/đánh giá/từ chối/từ khoá, LLM viết tiêu đề, tóm tắt, nhận xét, chấm tiêu chí tự định nghĩa; (4) tính điểm — so ngưỡng, ra điểm thông số, cộng theo trọng số.

**Ba lớp kết quả**: (1) Thông số + **Đánh giá chất lượng** (chuẩn, mọi cuộc gọi); (2) **Bộ tiêu chí** (doanh nghiệp tự định nghĩa); (3) **SmartCall** (tuân thủ kịch bản).

**7 thông số tính vào Đánh giá chất lượng** (thang 0–100 mỗi thông số):
| Thông số | Cấu hình | Cách tính điểm |
|---|---|---|
| Độ trễ tín hiệu (chỉ nhân viên) | ngưỡng ms, mặc định 90 | trừ điểm khi ping cao hơn ngưỡng; là chỉ số hạ tầng mạng/thiết bị, không phải kỹ năng; phía khách đi qua nhà mạng, không đo được |
| Thời gian phản hồi | ngưỡng giây (khuyến nghị 2–4) | lượt = khoảng lặng từ lúc bên này dừng tới lúc bên kia nói; **điểm = lượt trong ngưỡng ÷ tổng lượt × 100** |
| Tốc độ thoại | tốc độ mong muốn (từ/phút) + mức chênh cho phép và số điểm trừ, riêng cho nhanh hơn / chậm hơn | bắt đầu 100, mỗi lần lệch quá mức chênh bị trừ số điểm cấu hình, thấp nhất 0; tốc độ = số tiếng ÷ thời gian nói thực (bỏ khoảng lặng); nhãn Thấp/Tốt/Cao |
| Cảm xúc âm thanh | delta (khuyến nghị ≥ 30) | so cao độ trung bình hai đoạn liền kề, chênh < delta = giọng đều → trừ điểm; đo **ngữ điệu**, không phải vui/buồn; Trầm < 90 Hz, Trung bình 90–150, Cao > 150 |
| Tạp âm | không | trừ theo tỷ lệ thời lượng có tạp âm trên thời lượng nói; SNR > 25 Không ồn, 15–25 Ồn nhỏ, < 15 Ồn |
| Cảm xúc | không | **điểm = đoạn không tiêu cực ÷ tổng đoạn được nhận diện × 100**; nhãn tích cực/bình thường hoặc tiêu cực; xếp ở bước âm thanh, dựa trên giọng và nội dung |
| Lịch sự | không | **điểm = đoạn lịch sự ÷ tổng đoạn được đánh giá × 100** |

- **Tốc độ thoại tiếng Việt**: mỗi tiếng (âm tiết) đếm là một "từ" ("chăm sóc khách hàng" = 4). Nói bình thường > 200 tiếng/phút, thực tế nhân viên ~230–380 → mức "125–200 từ/phút" kiểu tiếng Anh sẽ trừ điểm gần như mọi cuộc gọi; đặt theo cuộc gọi mẫu của khách. Mức khuyến nghị chính thức cho tiếng Việt: Cần xác nhận.
- **Cảm xúc âm thanh** — ghi chú trong tài liệu: dữ liệu 30 cuộc gọi thật cho thấy thông số này luôn 100 khi người đó có nói và 0 khi không nói, không phụ thuộc delta → chưa dùng để phân biệt cuộc gọi tốt/xấu cho tới khi xác nhận lại.
- Mức trừ cụ thể của Độ trễ tín hiệu và Tạp âm: Cần xác nhận.

**7 thông số tham khảo** (hiện ở chi tiết cuộc gọi, dùng được làm thông số con trong Bộ tiêu chí, không tính vào Đánh giá chất lượng): Cường độ âm thanh (dB theo thời gian; 60 dB ≈ trò chuyện bình thường), Độc thoại (độ dài đoạn nói liên tục không bị chen), Từ khóa (dò cả từ gốc lẫn **phiên âm** — tên riêng, từ tiếng Anh mà STT nghe thành chữ khác; AI còn tự rút Chủ đề và Từ khóa chính), Câu hỏi, Lời hẹn (cam kết/bước tiếp theo kèm vị trí), Đánh giá dịch vụ (chỉ khách: cao/trung bình/thấp + câu dẫn chứng), Từ chối dịch vụ (chỉ khách; lý do: giá, đã dùng bên khác, chưa đủ thẩm quyền, không phù hợp nhu cầu, đã được liên hệ trước).

**Đánh giá chất lượng** — hai điểm riêng: nhân viên và khách hàng.
- `Điểm = Σ(điểm thông số × trọng số) ÷ 100`, tổng trọng số mỗi bên = 100%. Cấu hình ở nút **Trọng số** trên màn Thông số phân tích, 2 tab Nhân viên / Khách hàng, bật/tắt và chia % từng thông số. Tắt hết → không có điểm.
- Ví dụ cấu hình trong tài liệu (gần chia đều): nhân viên 7 thông số 14–15% mỗi cái; khách 6 thông số (không có Độ trễ) 16–17%. Gợi ý: CSKH tăng Cảm xúc, Lịch sự; telesale tăng Thời gian phản hồi, Tốc độ thoại.
- **Thông số không đủ dữ liệu = 0 điểm** (hiện "Chưa có đánh giá") nhưng vẫn giữ trọng số → cuộc gọi rất ngắn/một chiều điểm thấp; báo cáo QA nên lọc riêng.
- Điểm là công cụ sàng lọc (tìm cuộc gọi điểm thấp, nhiều tiêu cực, có từ chối) rồi người nghe lại, không thay đánh giá của con người.

**Bộ tiêu chí** — `Điểm tiêu chí = Σ(điểm thông số con × trọng số con) ÷ 100`; `Điểm bộ = Σ(điểm tiêu chí × trọng số tiêu chí) ÷ 100`; xếp vào khung điểm để ra nhãn/màu. Thông số số → so điều kiện đạt; từ khoá → dò (kể cả phiên âm) trong đúng khung thời gian; tự định nghĩa → LLM đọc toàn bộ lời thoại, cho 0–100 kèm giải thích và câu dẫn chứng (tab **Tiêu chí** ở chi tiết cuộc gọi). Danh sách cuộc gọi lọc được theo điểm từng bộ và từng tiêu chí (ví dụ "Xử lý khiếu nại" < 50). **Kho dữ liệu mẫu** có bộ mẫu (Cuộc gọi tốt, Xử lý khiếu nại, Phát hiện từ ngữ nhạy cảm, Cảm xúc tiêu cực…).

**SmartCall** — kịch bản chuẩn gồm các bước theo thứ tự; mỗi bước: yêu cầu + câu mẫu, **từ khoá** (kèm phiên âm, điều kiện **Bất kỳ** hoặc **Tất cả**), **khung thời gian** ("trong 20 giây đầu", "30 giây cuối"), **trọng số** (tổng 100%); cấu hình chung: tên, mục đích cuộc gọi, nhân viên áp dụng. Chỉ dò trong lời **nhân viên**, trong khung thời gian.
- `Điểm bước = từ khoá xuất hiện ÷ tổng từ khoá của bước × 100` (điều kiện Tất cả; ví dụ 2 từ khoá, nói 1 → 50). Cách chấm với điều kiện Bất kỳ: Cần xác nhận.
- `Điểm kịch bản = Σ(điểm bước × trọng số bước) ÷ 100`. Tab **Kịch bản SmartCall** hiện điểm từng bước, dạng "Lời chào 1/2", và vị trí từ khoá.

**Màn chi tiết cuộc gọi**: trình phát (SPACE phát/dừng, tua ±10 giây), dải thời gian nói và % mỗi bên, Chủ đề/Từ khóa; Tiêu đề + Tóm tắt (AI); Lời thoại theo đoạn (tìm, sao chép được); tab Ngôn ngữ tự nhiên, Âm thanh, Tiêu chí, Kịch bản SmartCall; khung Nhân viên / Khách hàng: giới tính, giọng vùng miền, tỷ lệ nói, nhận xét và gợi ý cải thiện (AI), điểm Đánh giá chất lượng kèm điểm từng thông số.

**Khuyến nghị cấu hình ban đầu** (dùng khi tư vấn khách): hiệu chỉnh ngưỡng từ 10–20 cuộc gọi quản lý cho là tốt (xem số đo ở tab Âm thanh); khai báo phiên âm cho thương hiệu, sản phẩm, từ tiếng Anh; trọng số chia đều rồi xem lại sau 1–2 tuần, tăng cho thông số phân biệt rõ cuộc gọi tốt/chưa tốt; Bộ tiêu chí bắt đầu từ Kho dữ liệu mẫu, chạy thử một nhóm nhân viên, so với chấm của QA rồi mới mở rộng. STT không đúng 100% (phụ thuộc ghi âm, tạp âm, giọng vùng miền, từ chuyên ngành) → luôn đối chiếu lời thoại và dẫn chứng.

## 4. Chat Insights ✔ UI 10/2026
Cấu hình → AI → **Chat Insights** (`/config/ai/natural-language-analysis/evaluation-criteria`): một tab **Bộ tiêu chí** (cột Nhân viên, Ngày tạo). Nội dung form bộ tiêu chí, chỉ số đầu ra: Cần khảo sát (tenant khảo sát chưa có bộ nào).

## 5. Đánh giá thủ công và API
- Cấu hình → Doanh nghiệp → **Đánh giá** (`/config/company/evaluation/list`): Cần khảo sát.
- [MCP] `list_eval_criteria`, `evaluate_call(transaction_id, agent_id, values[{criteria_id, point 0–10}], comment)`, `get_ticket_eval_criteria`, `create_ticket_evaluation` — **`list_eval_criteria` trả 404 trên tenant miền `.omicrm.com` (10/2026)**. Ghi điểm là dữ liệu thật → chỉ khi user đồng ý.
- [API công khai] Voice Insights và Speech-to-Text chạy bất đồng bộ: đăng ký webhook `POST /api/ai/register_webhook_ai` (header apiKey, body `url`) → gửi file multipart (`file` .wav/.mp3/.m4a + `tracking_id`) tới `/api/ai/call_analyze` hoặc `/api/ai/speech_to_text` → kết quả đẩy về webhook, khớp bằng `tracking_id`; Voice Insights trả `criteria_classification_result` và `quality_evaluation_result` (STAFF/CUSTOMER). Dùng khi khách muốn phân tích file ghi âm từ hệ thống khác. Nguồn: https://api.omicall.com/omicall-api/ai-api/voice-insights-api , https://api.omicall.com/omicall-api/ai-api/speech-to-text-api
- [MCP] `register_stt_webhook(url)` (chỉ HTTPS). apiKey và URL đích do user cung cấp; agent không tự lấy key.

## 5a. Đọc hiện trạng bằng API (✔ GET 10/2026, không mở giao diện)
`python <thư mục skill>/scripts/config_survey.py --out <scratch>/tenant_context.json --domain <domain>` → khoá `ai_config`:

| Đối tượng | Endpoint (token phiên) |
|---|---|
| AI Assistant | `POST cdr-v1-stg.omicrm.com/call_transaction/assistant/list` body `{}` → `{name, desc, type ("call"), enable, call_types, call_purpose_id, contact_ids, agent_cate_ids, numbers, keywords, channels, min_agent_messages_to_start, min_customer_messages_to_start, features[{type, items[{id, prompt, auto_assign, field_type}]}]}`; `features[].type` đã thấy `SUMMARY` (Tổng hợp nội dung); mã của Phân loại Tag / Tạo phiếu / Tạo khách: Cần xác nhận |
| Mục đích cuộc gọi | `POST cdr-v1-stg.omicrm.com/call_transaction/purpose/get_list` |
| Tiêu chí Chat Insights | `POST ai-v1-stg.omicrm.com/natural_language/criteria/get_list` |
| Tiêu chí đánh giá (thủ công) | `GET contact-v1-stg.omicrm.com/evaluation_criteria/get_all` → `{name, scopes[], contact_ids, contact_category_ids}` |

Ghi (thấy trong mã giao diện, chưa chạy): `call_transaction/assistant/add`, `…/update`. Sửa hướng dẫn tổng hợp vẫn làm trên giao diện cho tới khi đã thử ghi bằng API trên một trợ lý mới, có sự đồng ý của user.

## 6. Kiểm thử
- AI Assistant: một cuộc gọi thật thoả phạm vi (đúng chiều, nhân viên, đầu số, mục đích) — gọi thử chỉ khi user đồng ý → xem cửa sổ/lịch sử cuộc gọi; flow dùng kết quả → tab Lịch sử của flow.
- So kết quả với hướng dẫn: mỗi trường đúng một dòng, giá trị danh sách đúng nguyên văn.
- Voice Insights: cuộc gọi phải có ghi âm và đúng mục đích của bộ tiêu chí.
