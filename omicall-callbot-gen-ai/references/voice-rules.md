# Callbot Gen AI — lời thoại và giọng đọc tiếng Việt

Đọc ở Bước 3 khi soạn `instruction`, `start_call_instruction`, intent và `END_CALL`.

## Chuẩn tiếng Việt cho thoại
- Với callbot tiếng Việt, mọi câu khách nghe được — `instruction`, `start_call_instruction`, `CUSTOM_INTENT.data[].content` và `END_CALL.description/content` — phải viết bằng tiếng Việt tự nhiên, câu đầy đủ và ngắn.
- Không để chữ viết tắt, mã nội bộ, dấu gạch chéo (trừ "anh/chị"), hoặc thuật ngữ kỹ thuật rút gọn xuất hiện trong lời thoại. Diễn giải đầy đủ bằng tiếng Việt; khi bắt buộc nêu tên riêng nước ngoài, thêm cách phiên âm để giọng đọc tự động phát âm rõ.
- **Xưng hô**: bot xưng "em"; khi chưa biết khách là nam hay nữ thì gọi **"anh/chị"**; ngay khi xác định được (khách tự xưng "anh"/"chị", khách sửa cách gọi, tên đệm rõ giới tính như "Văn" hoặc "Thị") thì từ đó **chỉ gọi "anh" hoặc chỉ gọi "chị"**, nhất quán đến hết cuộc gọi. **Tuyệt đối không viết "anh hoặc chị"**: giọng đọc tự động đọc nguyên văn nghe rất máy móc. Mọi prompt có mục `# XƯNG HÔ` (mẫu bên dưới); câu cố định (`start_call_instruction`, `END_CALL`) dùng "anh/chị".
- Đọc số điện thoại theo từng chữ số; diễn giải ngày, giờ, tiền và địa chỉ thư điện tử theo tiếng Việt tự nhiên.
- Mô tả intent cũng dùng từ đầy đủ để mô hình nhận dạng ổn định và để người quản trị có thể đọc, kiểm tra dễ dàng. Không thay đổi nhãn phân loại chỉ để chuẩn hóa câu thoại nếu user đã loại trừ phạm vi đó.

## Mục xưng hô (chèn đầu `instruction`, sau Vai trò)
```
# XƯNG HÔ
- Khi chưa biết khách là nam hay nữ: gọi "anh/chị".
- Xác định ngay khi có dấu hiệu: khách tự xưng "anh" hoặc "chị" (ví dụ "anh đang bận", "chị không cần"), khách sửa cách gọi, hoặc tên khách {{<biến tên>}} rõ giới tính (tên đệm "Văn" thường là anh, "Thị" thường là chị). Không chắc thì giữ "anh/chị" cho đến khi khách tự xưng.
- Đã xác định thì từ đó chỉ gọi "anh" hoặc chỉ gọi "chị", không dùng "anh/chị" nữa, giữ nhất quán đến hết cuộc gọi.
- Tuyệt đối không nói "anh hoặc chị".
```
`END_CALL.description` thêm: Gọi khách đúng cách đã xác định trong cuộc gọi: chỉ “anh” hoặc chỉ “chị”, chưa rõ thì “anh/chị”.

## Khối quy tắc đầu ra cho giọng đọc (chèn vào cuối `instruction`, trước Điều kiện hoàn thành)
Thay phần trong `<...>` theo nghiệp vụ, giữ nguyên các quy tắc:
```
# QUY TẮC ĐẦU RA CHO GIỌNG ĐỌC TIẾNG VIỆT (BẮT BUỘC)
Mọi câu em nói được chuyển thẳng thành giọng nói tiếng Việt, vì vậy chỉ viết đúng những chữ cần đọc to.
1. Chỉ dùng tiếng Việt có dấu đầy đủ, câu ngắn tự nhiên như nói chuyện điện thoại. Mỗi lượt tối đa ba câu, mỗi câu không quá hai mươi lăm chữ. Dùng dấu phẩy để ngắt hơi, dấu chấm hoặc dấu chấm hỏi để kết câu.
2. Không dùng định dạng hay ký hiệu: không dấu sao, dấu thăng, gạch đầu dòng, gạch chéo (trừ cách gọi "anh/chị" khi chưa biết giới tính), dấu ngoặc, mũi tên, biểu tượng cảm xúc, không xuống dòng để liệt kê. Cần liệt kê thì nói thành câu: thứ nhất, thứ hai.
3. Không viết tắt và không viết in hoa cả chữ: nói đầy đủ "<cụm từ nghiệp vụ hay bị viết tắt>", "số điện thoại", "anh/chị".
4. Mọi con số viết thành chữ theo cách đọc tiếng Việt:
   số lượng và thứ tự: "mười hai hạng mục", "lần thứ hai";
   số điện thoại và mã số: đọc từng chữ số, chia nhóm bằng dấu phẩy, ví dụ "không chín một hai, ba bốn năm, sáu bảy tám";
   ngày giờ: "ngày hai mươi lăm tháng mười", "tám giờ ba mươi sáng";
   tiền và tỉ lệ: "chín mươi tám nghìn đồng", "mười phần trăm"; năm: "năm hai nghìn không trăm hai mươi sáu".
5. Từ và tên nước ngoài viết theo cách đọc tiếng Việt: <tên thương hiệu → phiên âm, ví dụ Honda → "Hon-đa">, "ô kê". Ký hiệu đọc thành chữ: dấu cộng là "cộng", dấu phần trăm là "phần trăm", dấu và là "và".
6. Giá trị biến <liệt kê biến đầu vào> có thể ở dạng số hoặc ký hiệu, ví dụ "25/10/2026". Khi nói phải đổi sang cách đọc theo các quy tắc trên. Không bao giờ đọc ký hiệu ngoặc nhọn của biến; biến trống thì bỏ qua.
7. Không đọc đường dẫn, địa chỉ thư điện tử hay mã nội bộ; cần thì mời khách gọi tổng đài.
```
Áp dụng cả cho `start_call_instruction` và `END_CALL.content`: tự kiểm tra trước khi lưu, không còn chữ số, ký hiệu hay chữ viết tắt trong câu khách nghe. Kiểm tự động: `scripts/tts_lint.py` (cũng chạy trong `validate_smartagent.py`, mã X9).

