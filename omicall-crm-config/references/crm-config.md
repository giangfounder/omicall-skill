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

Dùng trong OMIFlow: trigger `GENERAL` theo thuộc tính trạng thái khách ("chuyển vào trạng thái X"), hành động `UPDATE_INFO_CONTACT` đổi trạng thái pipeline (+ ghi chú). Trigger theo trạng thái chỉ bắt lúc *chuyển vào* trạng thái (Gotchas "Trigger theo trạng thái" trong `omicall-omiflow/SKILL.md`).

### 1b. Bộ thuộc tính khách hàng (form động)
Danh sách bộ thuộc tính (vd. một bộ mặc định cho khách cá nhân). Mở bộ = **trình thiết kế form** chia nhóm:
- Nhóm mặc định: Thông tin cá nhân (ảnh, giới tính, tên đầy đủ*, SĐT*, email có nhãn, ngày sinh, chức vụ, CMND/Passport, địa chỉ, trường tùy chỉnh, mô tả…), File đính kèm (≤10MB/file), Mạng xã hội, Đánh giá, Trạng thái khách hàng, Nhân viên phụ trách / liên quan, Phân loại (Tag, Nhóm khách hàng, Ngành kinh doanh).
- **Thêm thuộc tính** vào nhóm, **Thêm nhóm thuộc tính** mới; nhóm có thể tự thu gọn.
- Kiểu trường khi thêm: **Hộp ký tự**, **Đoạn văn bản**, **Danh sách tùy chọn**, **Ô chọn (duy nhất)**, **Ô chọn (nhiều giá trị)**, **Thời gian** — chi tiết từng kiểu ở mục 3 (dùng chung cho Khách hàng và Phiếu ghi).

Mỗi trường tạo ra một **mã ngẫu nhiên** (`field_code`) — dùng mã này trong OMIFlow (`ASSIGN_ATTRIBUTE_STRUCTURE`, điều kiện), Public API (`attribute_structure[]`, `otherDynamicUpdates`) và biến chatbot/callbot. Tra mã: thuộc tính **Phiếu ghi** bằng API `tenant-v1 …/attribute/get_all?has_attr=true` (mục 3); thuộc tính **Khách hàng** API này không trả → đọc trên giao diện hoặc thử `GET /api/v2/contact/layout/list` (Public API, chưa kiểm chứng).

## 2. Phiếu ghi (`/config/attribute/ticket/{tab}`)
Tab: **Chủ đề**, **Trạng thái**, **Thuộc tính**, **Nhóm tiếp nhận**.
- **Bộ trạng thái phiếu**: tối đa 14 thành phần theo thứ tự (≤30 ký tự), đánh dấu trạng thái hoàn thành/kết thúc.
- **Chủ đề** (danh mục phiếu) gom: bộ thuộc tính, bộ trạng thái, quyền mở lại phiếu (người tạo/tiếp nhận/liên quan/không liên quan), bắt buộc ghi chú khi chuyển trạng thái, khoá sửa khi hoàn thành, tự ẩn sau N ngày, chia sẻ phiếu (link công khai), trình tự chuyển trạng thái (số bậc, không chuyển ngược), **phân loại** (mỗi phân loại một cấu hình chọn sẵn), **độ ưu tiên**, **ngày hết hạn mặc định** theo độ ưu tiên + áp dụng **ca làm việc** + nhắc trước N phút (Thông báo và Email) + tự gia hạn khi mở lại, nhân viên tiếp nhận mặc định (tối đa 3) / liên quan, tự thêm người phụ trách khách / cuộc gọi làm liên quan.
- Chi tiết phiếu ghi lại thời gian nằm ở từng trạng thái; thống kê phiếu có tỉ lệ hoàn thành trước hạn, đúng/chậm tiến độ, số lần mở lại.

Ca làm việc: **Cấu hình → Doanh nghiệp → Khác → Ca làm việc** (dùng cho hạn phiếu và báo cáo thời gian kết nối).
- **Ba loại trạng thái phiếu** [tài liệu]: *Trạng thái bắt đầu* (gán khi tạo), *Trạng thái hoàn thành* (vị trí tự chọn, là mốc tính **đúng/chậm tiến độ**), *Trạng thái kết thúc* (luôn cuối, phiếu hết hiệu lực); hoàn thành và kết thúc có thể trùng vị trí. Phiếu chưa tới trạng thái hoàn thành trước **ngày hết hạn** (lấy từ cấu hình chủ đề hoặc người tạo chọn) → chậm tiến độ. Đây là SLA có sẵn, không cần OMIFlow. Nguồn: https://omicrm.io/post/detail/huong-dan-su-dung-phieu-ghi-o-omicall-post60 (bài 2023).

## 3. Thêm thuộc tính — các kiểu trường (✔ khảo sát giao diện 10/2026, chỉ xem, không lưu)
Mở bộ thuộc tính → **Thêm thuộc tính** (cuối mỗi nhóm) → ngăn "Thêm thuộc tính": cột trái chọn kiểu, phải cấu hình, phía trên có ô xem trước. Khách hàng và Phiếu ghi có **cùng 6 kiểu**. "Thêm nhóm thuộc tính" tạo nhóm (vùng) mới trong form.

| Kiểu (UI) | Cấu hình | Ghi chú dùng |
|---|---|---|
| **Hộp ký tự** | Tên* (≤48), Gợi ý, **Kiểu dữ liệu** (Văn bản / Số tự nhiên / Số thập phân / Phần trăm / Tiền tệ), Giới hạn dữ liệu, Giới hạn ký tự, Bắt buộc, Bao gồm nhãn, Giá trị mặc định | `field_type: single_text`; nhận biến trong OMIFlow |
| **Đoạn văn bản** | Văn bản nhiều dòng | thường `multi_text` (Cần xác nhận cho trường tự tạo) |
| **Danh sách tùy chọn** (dropdown) | Tên*, **Dữ liệu** = chỉ có **"Tùy chỉnh"**, Bắt buộc, Danh sách giá trị (mỗi giá trị ≤256 ký tự, thêm/xoá từng dòng, đánh dấu một **Mặc định**) | lựa chọn **nhập tay**, không có nguồn API trên giao diện |
| **Ô chọn (duy nhất)** (radio) | Tên*, **Bố cục** (Chiều dọc/ngang), Danh sách giá trị, một giá trị mặc định | như dropdown |
| **Ô chọn (nhiều giá trị)** (checkbox) | Tên*, Bố cục, Bắt buộc, Danh sách giá trị, tick sẵn **nhiều** mặc định | như dropdown, giá trị là mảng |
| **Thời gian** | Tên*, **Kiểu dữ liệu**: Giờ (HH:mm) / Ngày (dd/MM/yyyy) / Ngày giờ (HH:mm dd/MM/yyyy), Bắt buộc | dùng cho trigger Định kỳ "trước/sau thuộc tính thời gian" |

Phiếu ghi còn có kiểu công tắc `ticket_switch` (thấy trong dữ liệu API, nhãn có thể rỗng).

**Mã `field_type` của 3 kiểu chọn (dropdown, radio, checkbox): Cần xác nhận** — muốn biết thì tạo một trường thử (thao tác ghi, hỏi user), đọc lại bằng API bên dưới, rồi ghi bổ sung vào đây. Trong OMIFlow coi cả 3 là **kiểu danh sách**: không gán biến tự do, rẽ nhánh theo từng giá trị (Gotchas "AI điền CRM" trong `omicall-omiflow/SKILL.md`).

**Dropdown động từ API**: dữ liệu API của mỗi thuộc tính có khối `data_type: {used_rest_api_from_third_party, values, api_info}` — dấu hiệu backend có hỗ trợ nguồn REST bên thứ ba, nhưng giao diện (10/2026) chỉ hiện "Tùy chỉnh" ở cả Khách hàng lẫn Phiếu ghi. Chưa bật được → không hứa với khách; ghi "Cần xác nhận với OMI".

### API đọc thuộc tính (✔ GET 10/2026)
`GET tenant-v1-stg.omicrm.com/attribute/get_all?has_attr=true` → `payload[]` = **bộ thuộc tính Phiếu ghi** (thêm `type=customer` vẫn chỉ trả bộ phiếu; không có `has_attr` thì `attributes` rỗng):
```
{_id, type:"ticket", name, is_default, is_published,
 zone:[{zone, zone_name, zone_type:"default|assign|timeAndReminder|classify|attachFile|evaluationZone|ticketObject", cols, position, collapse}],
 attributes:[{_id, field_code, field_type, field_name:{custom, vi, en, i18}, field_format, zone, index, required,
              multi, have_data_type, data_type:{used_rest_api_from_third_party, values, api_info},
              default_value, placeholder, max_length, min_length, is_deleted, ...}]}
```
Tên hiển thị trường tự tạo nằm ở `field_name.custom`. `scripts/tenant_survey.py` đã đọc endpoint này và dàn phẳng thành `attributes[]` (`code, name, type, is_list, set`).

## 4. Khi thiết kế
- Bài toán cần trường mới (mã đơn, hạng hội viên, cửa hàng…) → tạo thuộc tính động đúng kiểu dữ liệu, rồi lấy `field_code` để dùng; không nhét vào ghi chú.
- Bài toán pipeline/lead → dùng bộ trạng thái khách hàng (WIN/LOST cho báo cáo), đổi trạng thái làm mốc nối flow.
- Bài toán SLA phiếu → ưu tiên cấu hình sẵn của Chủ đề (hạn theo độ ưu tiên, ca làm việc, nhắc trước) trước khi dựng OMIFlow; OMIFlow chỉ bù phần thiếu (vd. hạn phản hồi đầu tiên, leo thang).
- Trường có tập giá trị cố định (hạng, nguồn lead, kết quả gọi) → Danh sách tùy chọn / Ô chọn; nhớ kiểu này không nhận biến trong flow. Giá trị lấy từ hệ thống ngoài, thay đổi thường xuyên → để Hộp ký tự (nhận biến) thay vì dropdown nhập tay.
- Danh mục phiếu (Chủ đề) đọc bằng MCP `get_ticket_categories`; lệnh này có thể lỗi 500 → xem tab Chủ đề trên giao diện (mở chủ đề chỉ để xem, bấm Đóng).
- Tạo/sửa cấu hình là thao tác ghi trên tenant khách → hỏi user trước.

## 5. Cấu hình doanh nghiệp liên quan dữ liệu (✔ UI 10/2026, chỉ xem)
Cấu hình → Doanh nghiệp → **Khác** (`/config/company/other/list`):
| Mục | Tác dụng khi thiết kế giải pháp |
|---|---|
| **Cấu hình phân bổ** | chia khách, phiếu, **cuộc gọi nhỡ** cho nhân viên; dùng cho Tải lên Excel, phân cuộc gọi nhỡ, Chiến dịch, OMIFlow (mục dưới) |
| **Thêm khách hàng tự động qua cuộc gọi** | bật theo Cuộc gọi đi / Cuộc gọi đến, "Ưu tiên nhân viên thực hiện cuộc gọi" (người gọi thành phụ trách) — bật thì không cần flow chỉ để tạo khách từ cuộc gọi |
| **Ca làm việc** | gán cho nhân viên; dùng cho hạn phiếu và báo cáo thời gian kết nối tổng đài |
| **Phân loại bắt buộc** | bắt buộc chọn phân loại (tag/nhóm/ngành) khi tương tác Khách hàng, Nhân viên, Phiếu ghi, Lịch sử cuộc gọi |
| **Mã quốc gia mặc định** | gán cho khách mới |
| **Đồng bộ dữ liệu** | thêm lại khách đã xoá thì khôi phục lịch sử tương tác |
| **Trạng thái Tổng đài / Đa kênh / Phiếu ghi** | nguyên nhân chuyển trạng thái nhân viên và chuyển tự động, có log |
| Giới hạn truy cập IP, Hình thức xuất dữ liệu, Bảo mật (2 lớp, hết hạn phiên) | an ninh — không đổi khi chưa có yêu cầu |

Cấu hình → **Phân loại**: **Tag** (`/config/classify/tag/all`), **Nhóm** khách hàng (`/config/classify/group/customer`), **Ngành** kinh doanh (`/config/classify/business/list`) — dùng cho phân khúc, điều kiện flow, đối tượng Marketing. Tag cũng là đầu ra của AI Assistant (chức năng Phân loại Tag, `omicall-ai-insight`).

Cấu hình → Thuộc tính có thêm tab **Đa kênh** (`/config/attribute/social/attribute`): thuộc tính của hội thoại/khách đa kênh (biến `social_*` trong flow).

## Cấu hình phân bổ (Cấu hình → Doanh nghiệp → Khác → Cấu hình phân bổ) — đã kiểm chứng 10/2026
- API đọc: `POST tenant-v1-stg.omicrm.com/sale_allocation/search?page=1&size=50` body `{}` → `payload.items[]` `{_id,name,type,staffs:[{contact_id,full_name,percent}]}`.
- `type`: `split_evenly` (Phân chia đồng đều) · `prioritize_employees_with_fewer_customers` (Ưu tiên nhân viên có ít dữ liệu nhất) · `specific_division` (Phân chia cụ thể theo %; `staffs[].percent`, tổng phải = 100, form hiện "Phần trăm hiện tại"). Tuỳ chọn áp dụng: nhân viên cụ thể / nhóm nhân viên / nhóm nội bộ (chọn nhóm thì mất lựa chọn "theo %").
- Flow dùng qua hành động `ASSIGN_SALE_ALLOCATION` `data.ids:[<_id>]`. Đổi cơ chế cho mọi flow cùng lúc: sửa "Hình thức" của chính cấu hình đang gắn; đổi riêng từng flow: chọn cấu hình khác trong nút Thêm khách hàng rồi xuất bản.
- Gotcha UI: ô "Nhóm nhân viên" nằm ngay dưới danh sách chọn nhân viên — bấm ra ngoài để đóng danh sách dễ trúng ô này và reset form; đóng danh sách bằng Esc.
