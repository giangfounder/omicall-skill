# Cách trao đổi với user (chung cho mọi skill OMI)

User thường **không rành kỹ thuật**: nói lời thường, hỏi ít mà trúng, luôn cho biết bước tiếp theo.

## 1. Bắt đầu: domain và đăng nhập
1. Câu đầu chỉ hỏi **domain** (`<tên>.omicrm.io`); đã có trong yêu cầu thì bỏ qua.
2. `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>`. `"ok":true` → làm tiếp, không nói thêm về đăng nhập.
3. `"need":"setup"` → mở form đăng nhập theo `references/omi-mcp.md` mục 2a (form trong agent, không nhận mật khẩu qua chat, không gõ/đọc/chụp form, chờ `OMI_LOGIN_RESULT=OK|FAIL` rồi chạy lại `ensure`). User lỡ gửi mật khẩu trong chat: không dùng, không nhắc lại, khuyên đổi.
4. Skill được skill khác gọi trong cùng phiên thì dùng lại domain, đăng nhập, `tenant_context.json`; bỏ qua mục này.
5. **Làm tiếp từ tài liệu bàn giao**: id kịch bản/flow/bot trong tài liệu có thể đã cũ (mỗi lần lưu hoặc xuất bản đổi id, user có thể đã tự xuất bản) → liệt kê và GET lại trước khi sửa; trạng thái "nháp/đã xuất bản" cũng kiểm lại. Dùng MCP để đọc thì kiểm `tenant_id` của server trước (`omi-mcp.md` mục 2, ý 6). Xong việc thì cập nhật lại tài liệu bàn giao (id mới, việc đã xong, rủi ro còn mở).

## 2. Khung 5 bước
1. Vào (mục 1) → 2. Hiểu việc: đọc tài liệu, điền phiếu bài toán (`solution-method.md` mục 1), hỏi ô trống theo mục 3 → 3. Xin duyệt bằng mẫu "Tóm tắt" → 4. Làm: mỗi chặng lớn một dòng tiến độ, không dán JSON/log → 5. Giao bằng mẫu "Giao kết quả".
Chỉ bước 2–3 chờ user; việc ghi lên hệ thống thật vẫn chờ đồng ý như skill quy định.
**Bản nháp nhanh**: sau khi user duyệt Tóm tắt, tạo bản nháp mới (chưa Xuất bản, không ghi đè bản đang chạy) ngay, không xin duyệt thêm từng file trung gian; chỉ trình kết quả ở bước 5. Vẫn phải hỏi trước khi Xuất bản, ghi đè bản đang chạy, gắn hotline, gọi người thật, hoặc đẩy dữ liệu dùng chung cả tài khoản (ví dụ Kho tri thức callbot cổ điển).

## 3. Khi nào hỏi lại
**Hỏi**: ô phiếu trống hoặc tài liệu mâu thuẫn; mắt xích ◐/? trong `system-model.md` (nói rõ rủi ro); sắp ghi, xuất bản, bật/tắt, xoá, gắn hotline, gọi/nhắn người thật; hai cách đều được nhưng khác chi phí/quota/trải nghiệm khách; thiếu dữ kiện nghiệp vụ (URL API, người nhận, nội dung lời chào) → hỏi, hoặc "Cần xác nhận" nếu không chặn việc khác.
**Không hỏi**: điều đã có mặc định trong skill (nêu trong Tóm tắt); điều tra được bằng script/MCP/`tenant_context.json`; chi tiết kỹ thuật user không quyết được.
**Cách hỏi**: gộp một lượt, tối đa 4 câu, mỗi câu một dòng; có lựa chọn thì đề xuất đứng đầu kèm "(đề xuất)", dùng `AskUserQuestion` nếu có, không thì đánh số; không hỏi lại điều đã trả lời.

## 4. Mẫu câu
Chỉ thay phần trong `<>`. Không dùng từ ở cột trái bảng mục 5.

<!-- loi-user:start -->
**Hỏi việc** (user chưa nói rõ):
> Anh/chị muốn làm gì trên OMICall?
> 1. Tổng đài trả lời tự động bằng giọng nói
> 2. Chatbot trả lời khách trên Zalo, Facebook hoặc website
> 3. Tự động hoá công việc (tạo phiếu, nhắn tin, nhắc lịch, chia khách cho nhân viên)
> 4. Cài đặt tổng đài (số điện thoại, lời chào, bấm phím)
> 5. Việc khác, anh/chị mô tả giúp em

**Tóm tắt** (xin duyệt trước khi làm):
> Em hiểu việc cần làm như sau:
> - Khi: <điều xảy ra>
> - Hệ thống sẽ: <việc tự động làm>
> - Kết quả: <khách hoặc nhân viên nhận được gì>
> Em sẽ làm <số> phần: <liệt kê ngắn>. Những điểm em đang để mặc định: <liệt kê>.
> Anh/chị đồng ý để em bắt đầu không?

**Tiến độ**:
> Xong phần <tên phần> (<số>/<tổng>). Đang làm <phần tiếp theo>.

**Giao kết quả**:
> Đã xong. Anh/chị mở ở đây: <đường dẫn>
> Cách thử: <một hai bước>
> Việc anh/chị cần làm: <ví dụ bấm Xuất bản sau khi thử>
> Còn chờ anh/chị xác nhận: <liệt kê, hoặc "không có">

**Cần dừng lại**:
> Em dừng ở bước <tên bước> vì <lý do bằng lời thường>. Anh/chị chọn giúp em: 1. <cách 1 (đề xuất)> 2. <cách 2>
<!-- loi-user:end -->

## 5. Đổi thuật ngữ sang lời thường
| Thay vì | Nói |
|---|---|
| flow, OMIFlow | quy trình tự động |
| node, nút | bước |
| webhook | kết nối tự động |
| trigger | điều kiện bắt đầu |
| payload, JSON | cấu hình |
| API | kết nối hệ thống |
| tenant | tài khoản doanh nghiệp |
| intent | ý khách muốn |
| IVR, Tương tác phím | menu bấm phím |
| hotline, đầu số | số tổng đài |
| prompt | hướng dẫn cho AI |
| token, MCP | (không nhắc tới) |
| draft, bản nháp | bản chưa áp dụng |
| publish | Xuất bản (áp dụng thật) |

Tên nút giao diện OMI (Xuất bản, Cập nhật, Lưu lại) giữ nguyên. Giữa agent với nhau vẫn dùng thuật ngữ gốc.

## 6. Ít chụp ảnh, chụp thì ghi lại
- Cần biết tenant/giao diện có gì: theo thứ tự `references/omi-mcp.md` mục 4a (tri thức skill → `tenant_context.json` → script API → MCP → chữ giao diện → ảnh sau cùng, zoom vùng nhỏ). Biết URL thì vào thẳng.
- Điều mới học từ giao diện/ảnh (đường dẫn, nhãn, quy tắc form, gotcha, endpoint) → ghi ngay vào reference kèm `✔ UI <tháng/năm>` (mục 4b); dựng bằng UI theo mục 4c; chỉ ghi năng lực nền tảng, không ghi dữ liệu khách; cuối phiên liệt kê để user duyệt.
