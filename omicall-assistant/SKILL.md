---
name: omicall-assistant
description: >-
  [v1.0.1] Cửa vào chung cho việc trên OMICall/OMICRM khi user chưa biết cần skill nào hoặc việc gồm nhiều phần (tổng đài, callbot, chatbot, quy trình tự động, CRM, AI phân tích): hỏi việc bằng lời thường, lập kế hoạch rồi gọi đúng skill omicall-*. Yêu cầu đã rõ thuộc một skill thì dùng thẳng skill đó.
---

# OMICall Assistant — Cửa vào chung

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-assistant v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.0.1). Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có.

## Đường nhanh
Skill này chỉ hiểu việc, lập kế hoạch và gọi skill khác; không tự dựng gì. Lời nói với user theo `references/conversation.md`.
1. **Vào**: hỏi domain, đăng nhập theo `references/conversation.md` mục 1, dùng script của skill bên cạnh: `python "<thư mục skill>/../omicall-omiflow/scripts/omi_login.py" ensure --domain <domain>`.
2. **Hỏi việc**: user chưa nói rõ thì dùng mẫu "Hỏi việc" (mục 4); có tài liệu thì đọc trước, không hỏi lại điều tài liệu đã có.
3. **Phiếu bài toán**: điền 5 ô Vào, Đối tượng, Luật, Ra, Ràng buộc (`references/solution-method.md` mục 1). Ô trống → hỏi gộp một lượt theo `conversation.md` mục 3.
4. **Chọn phần việc**: tra `references/system-model.md` mục 2 cho từng ô; mỗi năng lực thuộc một skill. Ưu tiên cấu hình sẵn của hệ thống trước quy trình tự động (`solution-method.md` mục 2).
5. **Xin duyệt**: mẫu "Tóm tắt" (mục 4), nêu số phần, mặc định đang dùng, phần nào có rủi ro (◐ hoặc ?).
6. **Gọi skill**: theo bảng "Gọi skill liên quan" bên dưới, đúng thứ tự dựng; mỗi skill nhận domain, `tenant_context.json` và đúng phần việc của nó. Báo tiến độ mỗi phần một dòng.
7. **Giao**: gộp kết quả các skill vào một mẫu "Giao kết quả" (mục 4).

Không bao giờ: tự dựng thay skill chuyên trách · gọi nhiều skill cùng ghi một thứ · bỏ bước xin duyệt khi việc có ghi lên hệ thống thật.

## Tư duy chức năng (trước khi chọn module)
- Hệ thống có gì, làm được gì: `references/system-model.md`. Cách phân rã bài toán thành chuỗi Sự kiện → Điều kiện → Hành động: `references/solution-method.md`.

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

