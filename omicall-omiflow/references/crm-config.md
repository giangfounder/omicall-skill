# OMICRM — Cấu hình thuộc tính động, bộ trạng thái, chủ đề phiếu (dùng chung mọi tenant)

Nguồn: khảo sát giao diện OMICRM (bản stg, 10/2026), chỉ xem, không lưu. Đây là năng lực nền tảng; giá trị cụ thể (tên trạng thái, trường) do từng tenant tự đặt — luôn tra trong tenant, không giả định.

Menu: **Cấu hình → Thuộc tính** → tab đối tượng: **Phiếu ghi**, **Khách hàng**, **Đa kênh**.

## 1. Khách hàng (`/config/attribute/customer/{tab}`)
3 tab: **Trạng thái** (`/status`), **Thuộc tính** (`/attribute`), **Sản phẩm**.

### 1a. Bộ trạng thái khách hàng (pipeline)
Danh sách bộ trạng thái (cột: Trạng thái, Phân quyền, Phân cấp). Mỗi bộ cấu hình được:
- **Tên bộ trạng thái**.
- **Tự động gán bộ trạng thái khi tạo khách hàng**.
- **Bắt buộc nhập phản hồi khi chuyển trạng thái** (ghi chú lý do).
- **Bắt buộc chọn giá trị mặc định khi tạo mới**.
- **Trình tự chuyển trạng thái**: giới hạn số bậc được nhảy, **không cho phép chuyển ngược**, áp dụng cho **trạng thái cấp 2** (bộ trạng thái có phân cấp).
- **Phân quyền**: nhân viên / nhóm nhân viên được áp dụng.
- **Thành phần trạng thái** (danh sách có thứ tự) + mục **Cơ hội bán hàng**: mỗi trạng thái gắn cờ **WIN**, **LOST** hoặc **Mặc định** → dùng cho báo cáo chuyển đổi.

Dùng trong OMIFlow: trigger `GENERAL` theo thuộc tính trạng thái khách ("chuyển vào trạng thái X"), hành động `UPDATE_INFO_CONTACT` đổi trạng thái pipeline (+ ghi chú). Trigger theo trạng thái chỉ bắt lúc *chuyển vào* trạng thái (xem Gotchas trong SKILL.md).

### 1b. Bộ thuộc tính khách hàng (form động)
Danh sách bộ thuộc tính (vd. một bộ mặc định cho khách cá nhân). Mở bộ = **trình thiết kế form** chia nhóm:
- Nhóm mặc định: Thông tin cá nhân (ảnh, giới tính, tên đầy đủ*, SĐT*, email có nhãn, ngày sinh, chức vụ, CMND/Passport, địa chỉ, trường tùy chỉnh, mô tả…), File đính kèm (≤10MB/file), Mạng xã hội, Đánh giá, Trạng thái khách hàng, Nhân viên phụ trách / liên quan, Phân loại (Tag, Nhóm khách hàng, Ngành kinh doanh).
- **Thêm thuộc tính** vào nhóm, **Thêm nhóm thuộc tính** mới; nhóm có thể tự thu gọn.
- Kiểu trường khi thêm: **Hộp ký tự**, **Đoạn văn bản**, **Danh sách tùy chọn**, **Ô chọn (duy nhất)**, **Ô chọn (nhiều giá trị)**, **Thời gian**.
- Tuỳ chọn trường (Hộp ký tự): Tên trường* (≤48 ký tự), Gợi ý, **Kiểu dữ liệu** (Văn bản, Số tự nhiên, Số thập phân, Phần trăm, Tiền tệ), Giới hạn dữ liệu, Giới hạn ký tự, **Dữ liệu bắt buộc**, Bao gồm nhãn, Giá trị mặc định. Có công tắc "Tiếp tục thêm mới" để thêm liên tiếp.

Mỗi trường tạo ra một **mã ngẫu nhiên** (`field_code`) — dùng mã này trong OMIFlow (`ASSIGN_ATTRIBUTE_STRUCTURE`, điều kiện), Public API (`attribute_structure[]`, `otherDynamicUpdates`) và biến chatbot/callbot. Tra mã bằng API `tenant-v1 …/attribute/get_all?has_attr=true` hoặc `GET /api/v2/contact/layout/list` (Public API).

## 2. Phiếu ghi (`/config/attribute/ticket/{tab}`)
Tab: **Chủ đề**, **Trạng thái**, **Thuộc tính**, **Nhóm tiếp nhận**.
- **Bộ trạng thái phiếu**: tối đa 14 thành phần theo thứ tự (≤30 ký tự), đánh dấu trạng thái hoàn thành/kết thúc.
- **Chủ đề** (danh mục phiếu) gom: bộ thuộc tính, bộ trạng thái, quyền mở lại phiếu (người tạo/tiếp nhận/liên quan/không liên quan), bắt buộc ghi chú khi chuyển trạng thái, khoá sửa khi hoàn thành, tự ẩn sau N ngày, chia sẻ phiếu (link công khai), trình tự chuyển trạng thái (số bậc, không chuyển ngược), **phân loại** (mỗi phân loại một cấu hình chọn sẵn), **độ ưu tiên**, **ngày hết hạn mặc định** theo độ ưu tiên + áp dụng **ca làm việc** + nhắc trước N phút (Thông báo và Email) + tự gia hạn khi mở lại, nhân viên tiếp nhận mặc định (tối đa 3) / liên quan, tự thêm người phụ trách khách / cuộc gọi làm liên quan.
- Chi tiết phiếu ghi lại thời gian nằm ở từng trạng thái; thống kê phiếu có tỉ lệ hoàn thành trước hạn, đúng/chậm tiến độ, số lần mở lại.

Ca làm việc: **Cấu hình → Doanh nghiệp → Khác → Ca làm việc** (dùng cho hạn phiếu và báo cáo thời gian kết nối).

## 3. Khi thiết kế
- Bài toán cần trường mới (mã đơn, hạng hội viên, cửa hàng…) → tạo thuộc tính động đúng kiểu dữ liệu, rồi lấy `field_code` để dùng; không nhét vào ghi chú.
- Bài toán pipeline/lead → dùng bộ trạng thái khách hàng (WIN/LOST cho báo cáo), đổi trạng thái làm mốc nối flow.
- Bài toán SLA phiếu → ưu tiên cấu hình sẵn của Chủ đề (hạn theo độ ưu tiên, ca làm việc, nhắc trước) trước khi dựng OMIFlow; OMIFlow chỉ bù phần thiếu (vd. hạn phản hồi đầu tiên, leo thang).
- Tạo/sửa cấu hình là thao tác ghi trên tenant khách → hỏi user trước.

## Cấu hình phân bổ (Cấu hình → Doanh nghiệp → Khác → Cấu hình phân bổ) — đã kiểm chứng 10/2026
- API đọc: `POST tenant-v1-stg.omicrm.com/sale_allocation/search?page=1&size=50` body `{}` → `payload.items[]` `{_id,name,type,staffs:[{contact_id,full_name,percent}]}`.
- `type`: `split_evenly` (Phân chia đồng đều) · `prioritize_employees_with_fewer_customers` (Ưu tiên nhân viên có ít dữ liệu nhất) · `specific_division` (Phân chia cụ thể theo %; `staffs[].percent`, tổng phải = 100, form hiện "Phần trăm hiện tại"). Tuỳ chọn áp dụng: nhân viên cụ thể / nhóm nhân viên / nhóm nội bộ (chọn nhóm thì mất lựa chọn "theo %").
- Flow dùng qua hành động `ASSIGN_SALE_ALLOCATION` `data.ids:[<_id>]`. Đổi cơ chế cho mọi flow cùng lúc: sửa "Hình thức" của chính cấu hình đang gắn; đổi riêng từng flow: chọn cấu hình khác trong nút Thêm khách hàng rồi xuất bản.
- Gotcha UI: ô "Nhóm nhân viên" nằm ngay dưới danh sách chọn nhân viên — bấm ra ngoài để đóng danh sách dễ trúng ô này và reset form; đóng danh sách bằng Esc.
