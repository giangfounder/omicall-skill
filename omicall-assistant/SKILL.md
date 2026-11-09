---
name: omicall-assistant
description: >-
  [v1.6.0] Điều phối viên trung tâm của OMICall/OMICRM. Chế độ hỏi đáp: trả lời câu hỏi về tính năng và mức độ đáp ứng (kể cả checklist, RFP) dựa trên tài liệu của các skill chuyên trách, không suy diễn. Chế độ triển khai: phân tích yêu cầu, lập kế hoạch, xin duyệt kế hoạch, chia thành các đợt theo quan hệ phụ thuộc, giao các skill omicall-* cho subagent thực hiện song song, kiểm tra lại kết quả và báo cáo. Yêu cầu chỉ thuộc một skill chuyên trách thì dùng trực tiếp skill đó.
---

# OMICall Assistant — Tổng quản lý điều phối

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` 1 lần/phiên, trước mọi bước khác. Câu đầu: `Đang dùng omicall-assistant v<phiên bản>` (dòng `SKILL_VERSION`; lỗi thì dùng v1.6.0). Không cập nhật được → báo lý do, làm tiếp.
**Chế độ subagent / hỏi đáp**: là subagent hoặc chỉ hỏi tính năng → bỏ qua bước này, hỏi domain, khảo sát (`parallel.md` mục 1).

## Đường nhanh
Chỉ điều phối (hiểu việc, chia phần, giao skill khác, kiểm, giao kết quả); không tự dựng, không trả lời từ trí nhớ. Lời nói theo `references/conversation.md`.
0. **Chọn cách chạy** (`references/orchestration.md` mục 1): một skill một phần → gọi thẳng; **hỏi** → `references/knowledge-qa.md` (nhiều mảng thì tra song song); **dựng/sửa** → bước 1–7.
1. **Vào**: hỏi domain, đăng nhập (`conversation.md` mục 1): `scripts/omi_login.py ensure --domain <domain>`.
2. **Hỏi việc**: thiếu thì hỏi gộp một lượt (`conversation.md` mục 3); có tài liệu thì đọc trước.
3. **Phiếu bài toán** 5 ô: Vào, Đối tượng, Luật, Ra, Ràng buộc (`references/solution-method.md` mục 1).
4. **Chia đợt và cổng**: `references/system-model.md` mục 2; `orchestration.md` mục 2.
5. **Duyệt**: kế hoạch một lượt; ghi cấu hình sống và từng cổng duyệt riêng (`references/plan-and-approval.md`).
6. **Giao subagent**: khảo sát một lần (`scripts/tenant_survey.py`, `scripts/config_survey.py`), sau đó `tenant_context.json` chỉ đọc; mỗi artefact một subagent; mẫu giao việc `references/parallel.md` mục 5; sổ chung `scripts/manifest.py`.
7. **Kiểm và giao**: tự GET lại và validator, một lượt hỏi user cho nhánh bị chặn, báo "Đợt n/N" (`orchestration.md` mục 7). Sửa/xuất bản bot xong: `scripts/check_callin.py --domain <d> --scratch <scratch>` (chỉ báo); STALE → cổng gắn số.

Không bao giờ: làm thay skill chuyên trách · tin báo cáo subagent khi chưa tự kiểm · hai subagent cùng ghi một thứ · để subagent qua cổng (CẤM: `parallel.md` mục 5) · ghi hệ thống thật khi chưa duyệt.

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan
Gọi bằng công cụ Skill theo bảng; thứ tự đợt và cổng: `references/orchestration.md` mục 2.

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

