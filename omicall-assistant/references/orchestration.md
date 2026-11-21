# Điều phối: chia đợt, giao subagent chạy song song, gom kết quả

Assistant là **người điều phối**: hiểu việc, chia phần, giao cho skill con (qua subagent khi chạy song song được), kiểm lại rồi báo user. Assistant **không tự dựng** và **không nạp tài liệu dài của skill con** (subagent nạp); việc nặng của assistant chỉ là kế hoạch, thứ tự, kiểm và giao. Lời nói với user theo `conversation.md`.

## 1. Chọn cách chạy (quyết định trước khi giao việc)
| Việc | Cách chạy |
|---|---|
| Rõ là một skill, một phần | Gọi thẳng skill đó (công cụ Skill), không subagent, không bảng kế hoạch dài |
| Hỏi đáp chạm ≥ 3 mảng (checklist, RFP) | Mục 6: mỗi nhóm câu một subagent chỉ đọc, chạy song song |
| Dựng/sửa ≥ 2 phần | Mục 2–5: chia đợt, mỗi artefact một subagent |
| Client không có subagent | Chạy tuần tự đúng thứ tự đợt, mọi quy tắc còn lại giữ nguyên |
Cách đánh giá song song/tuần tự (bốn câu hỏi, giới hạn, khi nào không cần subagent) chung cho mọi skill: `parallel.md`. Mục 6 của file đó ghi đơn vị chia và chỗ phải tuần tự của từng skill chuyên trách; assistant đọc khi xếp đợt. Subagent được giao việc không chia tiếp.
Cập nhật skill con: trước khi gọi thẳng hoặc giao một đợt, assistant chạy `scripts/self_update.py --skill <tên> [--skill <tên> …]` một lần cho mọi skill của đợt (không chạy khi subagent của đợt đó còn đang chạy). Một lần pull cập nhật cả repo; script báo đọc lại SKILL.md của skill vừa đổi, so phiên bản với GitHub khi cài chép tay và in `CALLED_SKILL=<tên> <phiên bản>`. Subagent vẫn không tự chạy self_update.
Công cụ Workflow/nhiều tác tử quy mô lớn chỉ dùng khi user yêu cầu rõ.

## 2. Chia đợt theo phụ thuộc và cổng của user
<!-- gen:waves (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
| Đợt | Ai làm | Việc | Song song? | Cổng user |
|---|---|---|---|---|
| 0 Chuẩn bị | Assistant | Đăng nhập; khảo sát tenant **một lần** (`tenant_survey.py`, `config_survey.py`) → `tenant_context.json` (từ đây **chỉ đọc**, giá trị mới ghi qua `manifest.py`); `manifest.py init`; bảng kế hoạch | Không | `duyet_ke_hoach` |
| 1 Nền | `crm-config`, `pbx-config` (nhóm, lời chào; chưa gắn hotline), `ai-insight` | Thuộc tính, trạng thái, chủ đề phiếu; nhóm, lời chào; AI Assistant | crm ‖ pbx; `ai-insight` cùng đợt khi không cần thuộc tính mới, ngược lại sau crm | `ghi_cau_hinh_song` |
| 2a Khuôn | skill dựng artefact (tenant chưa có bản mẫu) | Một subagent dựng artefact đầu, GET lại làm khuôn | Không | — |
| 2b Dựng | `omiflow` (flow webhook, flow không cần id bot), `callbot-gen-ai`, `callbot-flow`, `chatbot-gen-ai` | Bản nháp; mỗi artefact một subagent, dùng khuôn 2a | Có, nếu khác artefact | `callbot_flow_y_dinh`, `callbot_flow_huan_luyen`, `training_reset` |
| ⛔ | **User** | **User xuất bản flow** | Không | `xuat_ban_flow` |
| 3 Nối | `callbot-gen-ai`, `callbot-flow`, `chatbot-gen-ai` (gắn URL flow **đã xuất bản**); `omiflow` (flow chạy bot/callbot) | Đọc id/URL bằng `manifest.py get <producer>.<trường>`, ghi `consumed_values` | Theo producer-trước | — |
| 4 Kiểm | Assistant | GET lại, validator, `manifest.py check`, gom cổng chờ user | Không | — |
| ⛔ | **User** | **User xuất bản bot/callbot** | Không | `xuat_ban_bot` |
| 5 Gắn và thử | Assistant dùng `pbx-config` (không giao subagent) | `manifest.py stale <bot>` → GET id mới → gắn hotline/phím/webhook → `check_callin.py` → test đầu-cuối | Theo cổng | `gan_so`, `goi_thu` |

Thứ tự ngắn: crm-config → ai-insight → pbx-config (nhóm, lời chào) → omiflow (webhook, nháp) → user xuất bản flow → bot/callbot (URL flow, nháp) → user xuất bản bot → pbx-config gắn số → gọi thử (hai cổng user duyệt).
- `omicall-callbot-gen-ai` → `omicall-omiflow`: chỉ dùng kết quả sau cổng **User xuất bản flow**.
- `omicall-callbot-flow` → `omicall-omiflow`: chỉ dùng kết quả sau cổng **User xuất bản flow**.
- `omicall-chatbot-gen-ai` → `omicall-omiflow`: chỉ dùng kết quả sau cổng **User xuất bản flow**.
- Cần xác nhận: Flow chạy bot/callbot (đợt 3) dùng id bản nháp hay phải chờ bot xuất bản: chưa có kiểm chứng ✔; hiện xử lý bằng `manifest.py check` sau cổng xuất bản bot.
<!-- /gen:waves -->
Quy tắc xếp: A cần giá trị của B → B trước (ghi `consumed_values`). Phần không phụ thuộc nhau vào cùng đợt. Cổng (⛔) chỉ chặn nhánh phụ thuộc nó; quy tắc duyệt và danh sách cổng: `plan-and-approval.md`.

## 3. Giới hạn song song (đã gặp thật, không nới)
Theo `parallel.md` mục 3 (một artefact một tiến trình ghi; tài nguyên chung tuần tự; không truyền bí mật); số subagent cùng lúc: `parallel-brief.md` mục 2. Không chép lại ở đây để khỏi lệch.

## 4. Lời giao việc và mẫu trả về
Mẫu giao việc: **chỉ ở** `parallel.md` mục 5; danh sách CẤM và mẫu trả về: **chỉ ở** `parallel-brief.md` (cả hai sinh từ `shared/skill-graph.json`). Chọn loại tác tử mới, tự chứa đủ; chỉ dùng "fork" khi hội thoại còn ngắn. Việc chỉ đọc/tra cứu dùng model nhẹ; việc ghi lên hệ thống giữ model mặc định. Assistant chỉ tin kết quả sau khi tự kiểm (mục 7).

## 5. (gộp vào mục 4)

## 6. Hỏi đáp nhiều mảng chạy song song
Chia câu hỏi theo bảng `knowledge-qa.md` mục 2, mỗi skill con một subagent **chỉ đọc**, trả bảng `ý | kết luận (Có / Không có / Chưa có thông tin) | nguồn (skill + mục)`. Subagent phải theo năm quy tắc `knowledge-qa.md` mục 1; thiếu nguồn thì "Chưa có thông tin", không suy diễn. Assistant gộp theo mẫu trả lời mục 4 của file đó, ghi nguồn từng ý, không thêm điều không có trong bảng.

## 7. Assistant kiểm và gom (không tin báo cáo suông)
1. Với mỗi artefact đã ghi: tự GET lại và chạy validator, hoặc `manifest.py check`; lệch thì giao lại **đúng nhánh đó**, tối đa 1 lần.
2. Một nhánh blocked/lỗi không dừng các nhánh độc lập; gom mọi câu hỏi thành **một lượt** hỏi user (nút chọn), rồi chạy tiếp.
3. Báo tiến độ ngắn: "Đợt n/N: <skill> xong / đang chạy / chờ anh/chị"; mỗi subagent một dòng.
4. Giao: bảng kết quả (skill → đã làm → id/mã → cổng chờ user), danh sách "Cần xác nhận", việc user phải làm (xuất bản, gắn hotline), phần chưa làm kèm lý do.

## 8. Bài học từ lần dựng nhiều bot + menu bấm phím trên tenant trống (✔ 11/2026, chỉ nền tảng, không dữ liệu khách)
1. **Khuôn trước, dàn trải sau**: tenant chưa có kịch bản nào thì không có bản GET thật để nhân bản. Cho **một** subagent dựng bot đầu bằng giao diện, GET lại làm `bot_template.json`, rồi mới giao các bot còn lại chạy song song bằng API (`--new`). Giao tất cả cùng lúc khi chưa có khuôn thì mỗi bot tự dựng khuôn riêng và bị chặn.
2. **Phụ thuộc cuối cùng đi qua một tiến trình ghi**: nhóm nhận cuộc gọi, node chuyển nhóm, menu phím đều chung một subagent (một artefact = một tiến trình ghi); các bot không tự ghi vào menu. **Gắn đầu số** không giao subagent: là cổng của user (user tự làm, hoặc assistant làm sau khi user duyệt).
3. **Lưu bằng giao diện làm hỏng bản nháp** (mất thứ tự điều kiện, biến, nhãn phân loại). Chỉ lấy phần node cần từ bản đó, ghép vào payload gốc rồi lưu bằng API.
4. **Xuất bản đổi id** của bot (uuid giữ nguyên) và để lại bản cũ. **Mỗi lần sửa hoặc xuất bản lại bot** (không chỉ lần đầu) phải đồng bộ luồng gọi vào: lấy id mới từ sổ chung → **xin user duyệt** cập nhật menu phím (đổi đường đi cuộc gọi thật) → cập nhật → GET lại từng phím → kiểm đầu số vẫn gắn kịch bản gọi đến (chưa gắn thì báo user; gắn lại chỉ sau khi user duyệt). `is_publish` do server trả không dùng để biết đã xuất bản.
5. **Voice Bot GenAI không nhận phím và chưa có node chuyển sang bot khác**; chọn ngành bằng phím phải do Tương tác phím (hành động `Callbot` + id kịch bản). Lời chào menu là lời thoại TTS của tổng đài (tab "Robot đọc", chọn giọng Việt), không phải một bot.
6. **Báo cáo subagent có thể sai**: ví dụ báo nhóm có 0 thành viên trong khi GET thật có 1. Luôn tự chạy `config_survey.py --out <scratch>/kiem_tra.json` (file riêng; `tenant_context.json` chỉ đọc) và đối chiếu sổ chung trước khi báo user.
7. **Giới hạn song song**: đã chạy 8 subagent chỉ-API cùng lúc không gặp lỗi quá tải; số chốt ở `parallel-brief.md` mục 2. Một số phiên có bộ phân quyền chặn thao tác gắn kịch bản vào đầu số ("Production Deploy") kể cả khi user đã đồng ý trong chat: dừng, không vòng qua, đưa user các bước tự gắn trên giao diện.
8. **Subagent chủ động ghi** điều mới học vào reference của skill đích (`pbx-config.md`, `api-reference.md`, `agent-config-guide.md`); assistant chỉ ghi bài học điều phối ở mục này.

## 9. Tối ưu thời gian và token, không giảm chất lượng (✔ 11/2026)
Nguyên tắc: bớt chỗ **lặp và chờ**, không bớt chỗ **kiểm**. Validator mode post, GET lại và `check_callin.py` luôn chạy.
1. **Dựng khuôn rồi dàn trải** (mục 8.1): họ artefact giống nhau (nhiều bot cùng skill, cùng cấu trúc) → đợt 2a một subagent dựng khuôn, đợt 2b các subagent còn lại song song bằng API. Không dàn trải trước khi có khuôn.
2. **Một lời giao việc chung + phần riêng**: ghi phần giống nhau (domain, cấm, sổ chung, mẫu trả về, quy tắc tên) vào `<scratch>/brief_common.md` một lần; mỗi subagent chỉ nhận một dòng "đọc brief_common.md" cộng phần riêng (khoá, tên, tệp nguồn, owner). Giảm token giao việc lặp N lần mà nội dung không đổi.
3. **Tách theo artefact, không theo skill**: một skill có thể chia hai subagent nếu hai việc ghi hai artefact khác nhau và không phụ thuộc nhau (ví dụ `pbx-config`: lời chào TTS ‖ nhóm + menu). Menu cần id lời chào chưa có thì tạm trỏ lời chào có sẵn rồi thay sau, không chờ.
4. **Dùng lại subagent đã có ngữ cảnh** (`SendMessage`) cho việc tiếp theo cùng artefact/cùng tab thay vì tạo mới (tránh nạp lại skill và khảo sát). Việc mới, không liên quan → subagent mới, ngữ cảnh sạch.
5. **Chọn model theo việc**: viết nội dung, nghiên cứu, tra cứu → model nhẹ, chạy song song cả nhóm ngay đợt đầu (không cần tenant). Ghi lên hệ thống, xuất bản, sửa cấu hình thật → model mặc định.
6. **Kiểm bằng script, không bằng LLM**: sau mỗi đợt có sửa/xuất bản bot chạy `python <thư mục skill>/scripts/check_callin.py --domain <d> --scratch <scratch>` (một lệnh, ~1 giây): phím Tương tác phím và từng bước của kịch bản cuộc gọi (vd "Call in", `action_id`) → bot còn là bản mới nhất, nhóm/menu còn tồn tại, đầu số đã gắn kịch bản chưa. Script chỉ báo. STALE/MISSING → liệt kê phím/kịch bản cuộc gọi/đầu số sẽ đổi, **chờ user duyệt** (cổng riêng), rồi giao đúng subagent giữ menu map lại và chạy lại.
7. **Hỏi một lượt ngay đầu**: mọi điều chặn nhiều nhánh (thành viên nhóm nhận cuộc gọi, giờ làm việc, số đầu số dùng, tên công ty demo, giọng đọc) hỏi trong lượt duyệt đợt 0 để khỏi làm lại. Cổng hay bị chặn (gắn đầu số vào kịch bản, xuất bản) báo user ở đợt 0 là họ tự làm hoặc phải cấp quyền.
8. **Chạy nền, không hỏi thăm**: giao xong thì không poll; làm phần độc lập khác (kiểm, viết tài liệu, chuẩn bị đợt sau) trong lúc chờ thông báo.
9. **Báo cáo trả về ≤ 10 dòng** theo mẫu `parallel-brief.md` mục 4; chi tiết ghi vào tệp báo cáo ở scratch, assistant chỉ đọc khi cần kiểm.
10. **Không làm lại cái đã có**: trước khi dựng, liệt kê artefact đã có trên tenant (bot, menu, lời chào, bản "tối ưu" do người khác tạo) để dùng lại hoặc map, không tạo trùng.

## 10. Bài học từ demo hệ thống ngoài giả lập + gọi vào tra cứu + gọi ra nhắc lịch T+1 (✔ 16/11/2026)
1. **Cổng phải ghi đúng tên nút, xin trước khi giao việc**: bộ phân quyền chặn subagent khi lời giao việc mơ hồ ("không bấm Cập nhật" chặn luôn nút "Cập nhật" của hộp URL ở lần lưu đầu flow) và **không tính lời làm rõ của agent điều phối là đồng ý của user**. Ở lượt duyệt kế hoạch, liệt kê từng thao tác cần quyền (bấm "Cập nhật" trong hộp "Thông tin về URL" để tạo nháp flow, lưu đè bot đang gắn số, đổi kịch bản cuộc gọi của đầu số) để user đồng ý một lần.
2. **Lưu đè bot đang gắn số = đổi đường gọi vào ngay**: id cũ biến mất, đầu số trỏ vào bot không tồn tại cho tới khi cập nhật kịch bản cuộc gọi. Agent chính chạy liền: backup → lưu → `check_callin.py` → `call_script/update` → `check_callin.py` PASS (`omicall-callbot-gen-ai` `optimize-existing.md` mục 4). Không giao chuỗi này cho subagent.
3. **Mốc giờ đặt trong OMIFlow**: user muốn "8h sáng gọi khách có hẹn T+1" nằm trong flow (`PERIOD` "Trước khi" 1 ngày theo trường Ngày của khách, `omicall-omiflow` `node-trigger.md` 1d), không chấp nhận cron ở hệ thống ngoài. Hệ quả cần chốt từ đầu: trường **kiểu Ngày** trên khách (crm-config), dữ liệu lịch hẹn phải **có trên CRM trước giờ chạy** (flow đồng bộ), bot đọc thuộc tính khách.
4. **Hệ thống ngoài giả lập** (Google Sheet + Apps Script, mẫu `omicall-omiflow` `templates/apps_script_he_thong_gia_lap.gs`): khung trình duyệt phải đăng nhập **đúng tài khoản Google** (connector Drive có thể là tài khoản khác → Sheet tạo bằng connector bị 403 trong khung); cấp quyền OAuth do user bấm; sửa mã xong phải triển khai "Phiên bản mới". Dữ liệu giả chỉ được gọi ra cho **danh sách số thử** user đưa.
5. **User đổi thiết kế giữa chừng là bình thường** (bản sao → sửa bot đang chạy; 9h → 8h; cron → PERIOD): gửi `SendMessage` cho đúng subagent đang giữ artefact kèm "ĐỔI YÊU CẦU" + việc dừng/giữ; tránh để subagent cũ lưu tiếp theo thiết kế cũ.
6. **Subagent có thể dừng giữa chừng vì hết hạn mức (429)**: sổ chung + tệp trong thư mục owner giữ được tiến độ; nối lại bằng `SendMessage` sau giờ reset, không tạo subagent mới.
7. **Đường dẫn `verify_report`** ghi bằng Git Bash `$PWD` có dạng `/d/...`; `manifest.py` (từ 16/11) tự đổi sang `D:/...` trên Windows.
8. **Flow thử gọi 1 số**: giới hạn 1 lượt và tắt/xoá ngay sau khi thử (đã để sót một flow thử ở trạng thái xuất bản, trỏ bot id cũ).

