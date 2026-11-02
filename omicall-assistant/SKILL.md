---
name: omicall-assistant
description: >-
  [v1.1.1] Trợ lý tổng thể OMICall/OMICRM: trả lời câu hỏi về tính năng, cách làm, khả năng đáp ứng (kể cả checklist/RFP) bằng cách tra đúng skill con, không suy diễn, không biết nói không biết; cửa vào cho việc dựng nhiều phần: lập kế hoạch, xin duyệt, gọi đúng skill omicall-*, báo từng bước. Việc đã rõ thuộc một skill thì dùng thẳng skill đó.
---

# OMICall Assistant — Trợ lý tổng thể và cửa vào chung

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md). Câu đầu trả lời: `Đang dùng omicall-assistant v<phiên bản>` (dòng `SKILL_VERSION`, lỗi thì v1.0.1). Không cập nhật được → báo lý do, làm tiếp.

## Đường nhanh
Chỉ hiểu việc, tra tri thức, gọi skill khác; không tự dựng, không trả lời từ trí nhớ. Lời nói: `references/conversation.md`.
0. **Phân loại**: user **hỏi** (có không, làm thế nào, đáp ứng không, đánh giá checklist) → Hỏi đáp; muốn **dựng/sửa** → bước 1–7.
- **Hỏi đáp**: `references/knowledge-qa.md`: tra từng skill con, trả lời kèm nguồn; không biết nói không biết, nguồn ghi rõ không có mới nói không có.
- **Hiện từng bước** (cả hai chế độ): bảng bước → skill → cần duyệt, báo "Bước n/N": `references/plan-and-approval.md`.
1. **Vào**: hỏi domain, đăng nhập (`conversation.md` mục 1), script: `python "<thư mục skill>/../omicall-omiflow/scripts/omi_login.py" ensure --domain <domain>`.
2. **Hỏi việc**: chưa rõ thì dùng mẫu "Hỏi việc" (mục 4); có tài liệu thì đọc trước.
3. **Phiếu bài toán**: điền 5 ô Vào, Đối tượng, Luật, Ra, Ràng buộc (`references/solution-method.md` mục 1). Ô trống → hỏi gộp một lượt (`conversation.md` mục 3).
4. **Chọn phần việc**: tra `references/system-model.md` mục 2 cho từng ô; ưu tiên cấu hình sẵn (`solution-method.md` mục 2).
5. **Xin duyệt**: bảng kế hoạch và mẫu "Tóm tắt": số phần, mặc định, phần rủi ro (◐ hoặc ?).
6. **Gọi skill**: theo bảng "Gọi skill liên quan" bên dưới, đúng thứ tự dựng; mỗi skill nhận domain, `tenant_context.json` và đúng phần việc của nó.
7. **Giao**: gộp kết quả vào mẫu "Giao kết quả" (mục 4), ghi skill nào làm phần nào.

Không bao giờ: làm thay skill chuyên trách · đi tắt bằng kết quả cũ · nhiều skill cùng ghi một thứ · bỏ duyệt khi ghi lên hệ thống thật.

## Tư duy chức năng
- Hệ thống có gì: `references/system-model.md`. Phân rã bài toán Sự kiện → Điều kiện → Hành động: `references/solution-method.md`.

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json`, `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã trường/tên vừa tạo vào `tenant_context.json` hoặc manifest, rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → bot/callbot → omiflow (nháp) → user Xuất bản → pbx-config (gắn hotline/webhook).

| Khi gặp | Gọi skill |
|---|---|
| tổng đài trả lời tự động bằng giọng nói, hiểu ý khách bằng AI (SmartAgent) | `omicall-callbot-gen-ai` |
| tổng đài trả lời theo kịch bản cố định, cây hỏi đáp (callbot cổ điển) | `omicall-callbot-flow` |
| chatbot trả lời khách trên Zalo OA, Facebook, website (LiveTalk) | `omicall-chatbot-gen-ai` |
| tự động hoá: tạo phiếu, nhắn tin, nhắc lịch, chia khách, nối hệ thống ngoài | `omicall-omiflow` |
| số tổng đài, giờ làm việc, lời chào, menu bấm phím, nhóm nhân viên nhận cuộc gọi | `omicall-pbx-config` |
| trường thông tin khách/phiếu, trạng thái, chủ đề phiếu, chia khách cho nhân viên | `omicall-crm-config` |
| AI tóm tắt, chấm điểm, bóc thông tin từ cuộc gọi hoặc hội thoại | `omicall-ai-insight` |
<!-- skill-links:end -->

