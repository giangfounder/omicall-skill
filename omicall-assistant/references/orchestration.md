# Điều phối: chia đợt, giao subagent chạy song song, gom kết quả

Assistant là **người điều phối**: hiểu việc, chia phần, giao cho skill con (qua subagent khi chạy song song được), kiểm lại rồi báo user. Assistant **không tự dựng** và **không nạp tài liệu dài của skill con** (subagent nạp); việc nặng của assistant chỉ là kế hoạch, thứ tự, kiểm và giao. Lời nói với user theo `conversation.md`.

## 1. Chọn cách chạy (quyết định trước khi giao việc)
| Việc | Cách chạy |
|---|---|
| Rõ là một skill, một phần | Gọi thẳng skill đó (công cụ Skill), không subagent, không bảng kế hoạch dài |
| Hỏi đáp chạm ≥ 3 mảng (checklist, RFP) | Mục 6: mỗi nhóm câu một subagent chỉ đọc, chạy song song |
| Dựng/sửa ≥ 2 phần | Mục 2–5: chia đợt, mỗi artefact một subagent |
| Client không có subagent | Chạy tuần tự đúng thứ tự đợt, mọi quy tắc còn lại giữ nguyên |
Công cụ Workflow/nhiều tác tử quy mô lớn chỉ dùng khi user yêu cầu rõ.

## 2. Chia đợt theo phụ thuộc (đồ thị: `shared/skill-graph.json`; thứ tự gốc crm-config → ai-insight → pbx-config → bot/callbot → omiflow nháp → user xuất bản → pbx-config gắn)
| Đợt | Ai làm | Việc | Song song? |
|---|---|---|---|
| 0 | Assistant | Đăng nhập (`conversation.md` mục 1), khảo sát tenant **một lần** (`tenant_survey.py`, `config_survey.py`) → `tenant_context.json`; `manifest.py init`; bảng kế hoạch, **một lượt duyệt** cho cả bài toán | Không |
| 1 Nền | `crm-config`, `pbx-config` (nhóm, lời chào; chưa gắn hotline), `ai-insight` | Thuộc tính, trạng thái, chủ đề phiếu; nhóm đổ chuông, lời chào; AI Assistant | crm ‖ pbx. `ai-insight` chạy cùng đợt khi không cần thuộc tính mới, ngược lại sang sau crm |
| 2 Dựng | `callbot-gen-ai`, `callbot-flow`, `chatbot-gen-ai`, `omiflow` (flow không cần id của bot/callbot) | Mỗi artefact một subagent | Có, nếu khác artefact |
| 3 Nối | `omiflow` (flow chạy bot/callbot hoặc cần id của chúng), phần gắn webhook/URL của bot/callbot | Dùng id/URL lấy từ `manifest.py get <producer>.<trường>` | Theo producer-trước |
| 4 Kiểm | Assistant | GET lại, chạy validator, `manifest.py check`, gom cổng chờ user | Không |
| 5 Sau duyệt | User xuất bản → `pbx-config` gắn hotline/phím/webhook, test đầu-cuối | `manifest.py stale <producer>` rồi GET lại id mới | Theo cổng |
Quy tắc xếp: A cần giá trị của B → B trước (ghi `consumed_values`). Webhook flow: nháp (đợt 2) → user xuất bản (cổng) → URL/id mới vào bot/callbot (đợt 3). Phần không phụ thuộc nhau vào cùng đợt.

## 3. Giới hạn song song (đã gặp thật, không nới)
- Tối đa **3 subagent giao diện** cùng lúc, mỗi subagent **một tab riêng** (`tabs_create`, truyền `tabId` ở mọi lệnh); khung trình duyệt dùng chung với user nên thêm nữa sẽ tranh nhau. Subagent chỉ API/MCP: tối đa 5.
- **Một artefact = một subagent = một tiến trình ghi**. Không giao hai việc cùng chạm một flow, bot, kịch bản.
- **Tài nguyên chung chạy tuần tự**, một tiến trình mỗi lúc: Kho tri thức NLU của callbot (mỗi lần nhập huấn luyện lại), cấu hình AI Assistant, cấu hình phân bổ, bộ trạng thái đang được flow dùng.
- Không truyền token, cookie, mật khẩu cho subagent (kể cả trong lời giao việc hay sổ chung); subagent dùng phiên sẵn có. Chưa đăng nhập giao diện thì user tự đăng nhập trước khi giao việc giao diện.
- Subagent **không xuất bản, bật/tắt, xoá, gắn hotline/kênh thật, gọi hoặc nhắn người thật**; mọi cổng này do user quyết (cổng ghi ở `manifest.py gates`).

## 4. Lời giao việc cho subagent (chọn loại tác tử mới và tự chứa đủ; chỉ dùng "fork" khi hội thoại còn ngắn)
```
Nạp skill <omicall-…> bằng công cụ Skill (chỉ skill này). Domain <d>. Việc đã duyệt, CHỈ làm đúng danh sách này: <liệt kê>.
Đầu vào: <scratch>/tenant_context.json (đã khảo sát, KHÔNG khảo sát lại); sổ <manifest>, artefact <key>, owner <tên>;
giá trị cần từ phần khác: <producer>.<trường> (đọc bằng manifest.py get, không đoán).
Giao diện: chỉ khi API/MCP không làm được; tab riêng; theo omi-mcp.md mục 4c (≤1 ảnh mỗi ngăn, bấm theo ref, xác nhận bằng chữ/GET).
Sau khi lưu: GET lại, chạy validator của skill (mode post), manifest.py set <key> kèm verify_report.
CẤM: xuất bản, bật/tắt, xoá, gắn hotline/kênh, gọi hoặc nhắn người thật, nhập mật khẩu, in token, đụng artefact không phải của mình.
Gặp điều cần user quyết hoặc cần đăng nhập giao diện: dừng nhánh đó, trả "blocked" (không tự đoán).
Trả về đúng mẫu mục 5, tối đa 15 dòng, không dán JSON hay log dài.
```
Chọn model: việc chỉ đọc/tra cứu dùng model nhẹ; việc ghi lên hệ thống giữ model mặc định.

## 5. Mẫu kết quả subagent trả về (assistant chỉ tin sau khi tự kiểm)
```
key: <artefact> | trạng thái: done | partial | blocked
đã ghi: <id/mã/tên, nháp hay đã có>
verify_report: <đường dẫn> (PASS/FAIL)
cần xác nhận: <…>   chưa làm được + lý do: <…>   chờ user: <cổng>
```

## 6. Hỏi đáp nhiều mảng chạy song song
Chia câu hỏi theo bảng `knowledge-qa.md` mục 2, mỗi skill con một subagent **chỉ đọc**, trả bảng `ý | kết luận (Có / Không có / Chưa có thông tin) | nguồn (skill + mục)`. Subagent phải theo năm quy tắc `knowledge-qa.md` mục 1; thiếu nguồn thì "Chưa có thông tin", không suy diễn. Assistant gộp theo mẫu trả lời mục 4 của file đó, ghi nguồn từng ý, không thêm điều không có trong bảng.

## 7. Assistant kiểm và gom (không tin báo cáo suông)
1. Với mỗi artefact đã ghi: tự GET lại và chạy validator, hoặc `manifest.py check`; lệch thì giao lại **đúng nhánh đó**, tối đa 1 lần.
2. Một nhánh blocked/lỗi không dừng các nhánh độc lập; gom mọi câu hỏi thành **một lượt** hỏi user (nút chọn), rồi chạy tiếp.
3. Báo tiến độ ngắn: "Đợt n/N: <skill> xong / đang chạy / chờ anh/chị"; mỗi subagent một dòng.
4. Giao: bảng kết quả (skill → đã làm → id/mã → cổng chờ user), danh sách "Cần xác nhận", việc user phải làm (xuất bản, gắn hotline), phần chưa làm kèm lý do.

## 8. Bài học từ lần dựng nhiều bot + menu bấm phím trên tenant trống (✔ 11/2026, chỉ nền tảng, không dữ liệu khách)
1. **Khuôn trước, dàn trải sau**: tenant chưa có kịch bản nào thì không có bản GET thật để nhân bản. Cho **một** subagent dựng bot đầu bằng giao diện, GET lại làm `bot_template.json`, rồi mới giao các bot còn lại chạy song song bằng API (`--new`). Giao tất cả cùng lúc khi chưa có khuôn thì mỗi bot tự dựng khuôn riêng và bị chặn.
2. **Phụ thuộc cuối cùng đi qua một tiến trình ghi**: nhóm nhận cuộc gọi, node chuyển nhóm, menu phím, gắn đầu số đều chung một subagent (một artefact = một tiến trình ghi); các bot không tự ghi vào menu.
3. **Lưu bằng giao diện làm hỏng bản nháp** (mất thứ tự điều kiện, biến, nhãn phân loại). Chỉ lấy phần node cần từ bản đó, ghép vào payload gốc rồi lưu bằng API.
4. **Xuất bản đổi id** của bot (uuid giữ nguyên) và để lại bản cũ. **Mỗi lần sửa hoặc xuất bản lại bot** (không chỉ lần đầu) phải đồng bộ luồng gọi vào: lấy id mới từ sổ chung → cập nhật menu phím → GET lại từng phím → kiểm đầu số vẫn gắn kịch bản gọi đến (gắn lại nếu chưa). `is_publish` do server trả không dùng để biết đã xuất bản.
5. **Voice Bot GenAI không nhận phím và chưa có node chuyển sang bot khác**; chọn ngành bằng phím phải do Tương tác phím (hành động `Callbot` + id kịch bản). Lời chào menu là lời thoại TTS của tổng đài (tab "Robot đọc", chọn giọng Việt), không phải một bot.
6. **Báo cáo subagent có thể sai**: ví dụ báo nhóm có 0 thành viên trong khi GET thật có 1. Luôn tự chạy `config_survey.py` và đối chiếu sổ chung trước khi báo user.
7. **Giới hạn song song**: 8 subagent chỉ-API chạy cùng lúc không gặp lỗi quá tải; subagent giao diện vẫn tối đa 3, mỗi cái một tab. Một số phiên có bộ phân quyền chặn thao tác gắn kịch bản vào đầu số ("Production Deploy") kể cả khi user đã đồng ý trong chat: dừng, không vòng qua, đưa user các bước tự gắn trên giao diện.
8. **Subagent chủ động ghi** điều mới học vào reference của skill đích (`pbx-config.md`, `api-reference.md`, `agent-config-guide.md`); assistant chỉ ghi bài học điều phối ở mục này.
