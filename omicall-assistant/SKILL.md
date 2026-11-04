---
name: omicall-assistant
description: >-
  [v1.3.2] Điều phối viên trung tâm của OMICall/OMICRM. Chế độ hỏi đáp: trả lời câu hỏi về tính năng và mức độ đáp ứng (kể cả checklist, RFP) dựa trên tài liệu của các skill chuyên trách, không suy diễn. Chế độ triển khai: phân tích yêu cầu, lập kế hoạch, xin duyệt một lần, chia thành các đợt theo quan hệ phụ thuộc, giao các skill omicall-* cho subagent thực hiện song song, kiểm tra lại kết quả và báo cáo. Yêu cầu chỉ thuộc một skill chuyên trách thì dùng trực tiếp skill đó.
---

# OMICall Assistant — Tổng quản lý điều phối

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước (1 lần/phiên). Câu đầu trả lời: `Đang dùng omicall-assistant v<phiên bản>` (dòng `SKILL_VERSION`, lỗi thì v1.0.1). Không cập nhật được → báo lý do, làm tiếp.

## Đường nhanh
Chỉ điều phối: hiểu việc, chia phần, giao skill khác, kiểm, giao kết quả; không tự dựng, không trả lời từ trí nhớ. Lời nói theo `references/conversation.md`.
0. **Chọn cách chạy** (`references/orchestration.md` mục 1): một skill một phần → gọi thẳng; **hỏi** → `references/knowledge-qa.md` (nhiều mảng thì tra song song); **dựng/sửa** → bước 1–7.
1. **Vào**: hỏi domain, đăng nhập (`conversation.md` mục 1): `python "<thư mục skill>/../omicall-omiflow/scripts/omi_login.py" ensure --domain <domain>`.
2. **Hỏi việc**: thiếu thì hỏi gộp một lượt (`conversation.md` mục 3); có tài liệu thì đọc trước.
3. **Phiếu bài toán** 5 ô: Vào, Đối tượng, Luật, Ra, Ràng buộc (`references/solution-method.md` mục 1).
4. **Chia phần và đợt**: tra `references/system-model.md` mục 2; xếp đợt theo phụ thuộc (`orchestration.md` mục 2).
5. **Xin duyệt một lần**: bảng đợt → skill → chạy song song hay tuần tự → cổng chờ user (`references/plan-and-approval.md`).
6. **Giao subagent**: khảo sát tenant một lần rồi mỗi artefact một subagent, tối đa 3 subagent giao diện cùng lúc, lời giao việc theo `orchestration.md` mục 4; sổ chung `../omicall-omiflow/scripts/manifest.py`.
7. **Kiểm và giao**: tự GET lại và validator, một lượt hỏi user cho mọi nhánh bị chặn, báo "Đợt n/N" từng dòng (`orchestration.md` mục 7).

Không bao giờ: làm thay skill chuyên trách · tin báo cáo subagent khi chưa tự kiểm · hai subagent cùng ghi một thứ · subagent xuất bản, gắn số, gọi người thật · bỏ duyệt khi ghi lên hệ thống thật.

## Tư duy chức năng
- Hệ thống có gì: `references/system-model.md`. Phân rã Sự kiện → Điều kiện → Hành động: `references/solution-method.md`.

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

