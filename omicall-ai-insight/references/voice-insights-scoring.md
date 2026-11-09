# Voice Insights — Cách hoạt động và chấm điểm

Tách từ `ai-insight.md` mục 3 (cấu hình Voice Insights trên giao diện ở đó). Nhãn nguồn như `ai-insight.md`.
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
