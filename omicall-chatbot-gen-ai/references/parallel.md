# Đánh giá chạy song song và chia subagent (chung cho mọi skill OMI)

Làm ở bước lập kế hoạch, **trước lượt duyệt**: kết quả (việc nào song song, việc nào tuần tự, vì sao) đưa luôn vào bảng gửi user duyệt. Đơn vị chia và chỗ phải tuần tự của từng skill: mục 6.

## 1. Ai được chia
- **Đang là subagent** (được `omicall-assistant` hoặc agent khác giao việc): không chia tiếp, chỉ làm đúng danh sách được giao. Gặp việc cần chia hoặc thuộc skill khác thì trả "blocked" kèm đề xuất.
- **Skill được gọi thẳng**: chỉ chia các artefact của chính skill mình.
- **Việc phải ghi vào từ 2 skill khác trở lên** (ví dụ bot + flow + menu phím): chuyển cho `omicall-assistant` điều phối, skill chuyên trách không tự làm điều phối viên.

## 2. Bốn câu hỏi cho từng cặp việc
1. **Cùng artefact?** (cùng flow, bot, kịch bản, menu phím, nhóm, lời chào). Có → tuần tự, một tiến trình ghi.
2. **Cần giá trị của nhau?** (id, mã trường, URL webhook, id mới sau xuất bản). Có → bên tạo trước, bên dùng ở đợt sau, đọc giá trị bằng `manifest.py get` ngay trước khi lưu.
3. **Chạm tài nguyên chung?** (mục 3). Có → tuần tự.
4. **Cần cổng user?** (duyệt, xuất bản, gắn hotline/kênh, gọi hoặc nhắn thật). Có → dừng nhánh đó ở cổng; nhánh không phụ thuộc cổng vẫn chạy.

Cả bốn câu đều "không" → chạy song song được.

## 3. Giới hạn (đã gặp thật, không nới)
- Tối đa **3 subagent giao diện** cùng lúc, mỗi subagent một tab riêng (`tabs_create`, truyền `tabId` ở mọi lệnh); khung trình duyệt dùng chung với user. Subagent chỉ API/MCP: tối đa 5.
- **Một artefact = một subagent = một tiến trình ghi.**
- **Tài nguyên chung chạy tuần tự**, một tiến trình mỗi lúc: Kho tri thức NLU của callbot (mỗi lần nhập là huấn luyện lại toàn bộ), cấu hình AI Assistant, cấu hình phân bổ, bộ trạng thái đang được flow dùng.
- Không truyền token, cookie, mật khẩu cho subagent (kể cả trong lời giao việc, sổ chung, file tạm); subagent dùng phiên sẵn có. Chưa đăng nhập giao diện thì user tự đăng nhập trước khi giao việc giao diện.
- Subagent **không xuất bản, bật/tắt, xoá, gắn hotline/kênh thật, gọi hoặc nhắn người thật**.

## 4. Chọn cách chạy
| Tình huống | Cách chạy |
|---|---|
| Một việc, hoặc sửa nhỏ (một nút, một lời nhắc, một trường) | Tự làm, không subagent: chi phí giao việc lớn hơn lợi ích |
| Từ 2 artefact độc lập, mỗi cái nhiều bước | Mỗi artefact một subagent |
| Nhiều artefact cùng loại, tenant chưa có bản GET mẫu | **Khuôn trước**: một subagent dựng bản đầu, GET lại làm khuôn; sau đó dàn trải song song bằng API |
| Việc cơ học lặp lại trên nhiều artefact (cùng một script) | Nhiều tiến trình script chạy nền, mỗi tiến trình thư mục ra riêng; không cần subagent |
| Có thời gian chờ (đăng nhập, huấn luyện, user duyệt) | Làm phần offline trong lúc chờ: soạn spec, nội dung, chạy validator mode pre |
| Soạn nội dung, tra cứu chỉ đọc | Subagent model nhẹ, chạy song song ngay từ đầu |
| Client không có subagent | Chạy tuần tự đúng thứ tự, các quy tắc khác giữ nguyên |

## 5. Giao việc và kiểm
- Khảo sát tenant **một lần** (`tenant_context.json`); subagent đọc file đó, không khảo sát lại. Sổ chung `manifest.py` và mẫu giao việc: `omi-mcp-extra.md` mục 7–8.
- Phần giống nhau (domain, điều cấm, sổ chung, mẫu trả về) ghi một lần vào `<scratch>/brief_common.md`; mỗi subagent chỉ nhận thêm phần riêng.
- Subagent trả về tối đa 10 dòng: artefact, trạng thái (done / partial / blocked), id đã GET lại, đường dẫn verify_report, các điểm "Cần xác nhận".
- Agent chính **tự GET lại và chạy validator** trước khi nối artefact hoặc báo user; lệch thì giao lại đúng nhánh đó, tối đa 1 lần. Một nhánh bị chặn không dừng các nhánh độc lập; câu hỏi cho user gom thành một lượt.

## 6. Theo từng skill (đơn vị chia và chỗ phải tuần tự)
**omicall-omiflow**
- Song song: mỗi flow một subagent khi các flow không cần id của nhau.
- Khuôn trước: `name_mappings` chỉ chép từ bản GET của nút cùng loại đã dựng trên giao diện → loại nút chưa có bản mẫu thì một subagent dựng trước, rồi mới dàn trải.
- Tuần tự: flow gọi flow khác dựng sau flow đích; webhook Tương tác phím, URL cho bot/callbot chỉ gắn sau khi user Xuất bản (xuất bản đổi id flow).
- Trong lúc chờ: soạn payload, chạy `validate_flow.py --mode pre` offline.

**omicall-pbx-config**
- Song song: lời chào ‖ nhóm nội bộ (khác artefact, không cần id của nhau).
- Tuần tự theo cây, dựng từ dưới lên: lời chào + nhóm → Tương tác phím (cần id nhóm, lời chào; lời chào mới chưa có thì tạm trỏ lời chào có sẵn rồi thay sau) → kịch bản cuộc gọi → gắn hotline (bước cuối, user duyệt riêng).
- Mỗi menu phím, mỗi kịch bản cuộc gọi một tiến trình ghi; mọi bước nối phím → bot/flow do cùng một subagent giữ menu đó làm.
- Đích là bot hoặc flow chưa xuất bản → nhánh đó chờ cổng xuất bản, phần còn lại vẫn làm.

**omicall-crm-config**
- Thường là việc nhỏ → tự làm, không subagent.
- Tuần tự (tài nguyên chung): cấu hình phân bổ, bộ trạng thái đang được flow dùng.
- Mã trường, trạng thái tạo ở đây là đầu vào của skill khác → làm ở đợt đầu, ghi vào `tenant_context.json` trước khi skill khác dùng.

**omicall-ai-insight**
- Cấu hình AI Assistant là tài nguyên chung → một tiến trình ghi, không chia.
- Cần thuộc tính mới từ `omicall-crm-config` → chạy sau khi có mã trường; không cần thì chạy cùng đợt đầu với crm-config.
- Song song được: soạn dòng hướng dẫn offline; kiểm nhiều cuộc gọi bằng `get_call_detail` (chỉ đọc).

**omicall-callbot-flow**
- Kho tri thức NLU là tài nguyên chung → đẩy dữ liệu và chờ huấn luyện tuần tự, một tiến trình, kể cả khi dựng nhiều kịch bản.
- Trong lúc huấn luyện: soạn `spec_callflow.json`, chạy `build_callflow.py --allow-pending`.
- Nhiều kịch bản: mỗi kịch bản một subagent cho phần dựng luồng và lưu, sau khi dữ liệu NLU đã huấn luyện xong.
- Hai lần duyệt (bảng ý định, file huấn luyện) giữ riêng, không gộp để chạy nhanh hơn.

**omicall-callbot-gen-ai**
- Nhiều kịch bản mới: khuôn trước. Có bản GET mẫu (`script_outline.py --save`) thì mỗi kịch bản một subagent dựng bằng `build_smartagent.py --new`; tenant chưa có kịch bản nào thì một subagent dựng bản đầu trên giao diện rồi mới dàn trải.
- Tối ưu nhiều kịch bản có sẵn: mỗi kịch bản một tiến trình `optimize_script.py` chạy nền, thư mục ra riêng (script, không cần subagent), theo `optimize-existing.md`.
- Tuần tự: flow webhook phải được user Xuất bản trước khi gắn URL vào kịch bản; mỗi lần lưu hoặc xuất bản kịch bản đổi id → lấy id mới nhất trước khi gắn vào hotline/phím.
- Trong lúc chờ đăng nhập: soạn lời nhắc và lời thoại theo `voice-rules.md` offline.

**omicall-chatbot-gen-ai**
- Mỗi bot một subagent; tài liệu RAG của bot nào do subagent của bot đó tải (cùng tiến trình ghi bot).
- Tuần tự: flow WEB_HOOK cho Truy vấn API lưu nháp → user Xuất bản → gắn URL vào bot ở đợt sau.
- Chat thử nhiều bot cùng lúc trên widget LiveTalk test: Cần xác nhận → mặc định từng bot một, gõ `/end` sau mỗi lần cập nhật.
- Chấm điểm `eval_report.py` trên bản ghi hội thoại chạy offline, song song được.
