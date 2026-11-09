# Gọi API Kho tri thức và kịch bản (ngoài trang) + đoạn mã DOM còn dùng

**Không đọc cookie hay token bằng JS/CDP** (SKILL.md Rule 6). Token lấy qua `scripts/omi_session.py` (phiên đăng nhập của `omi_login.py`); chưa có token thì đăng nhập theo `references/conversation.md` mục 1, hoặc làm trên giao diện. Tôn trọng tenant: ít lượt tải trang, không crawl giao diện.

Các khối Python dưới chạy với `<thư mục skill>/scripts/` trong `sys.path`, dùng `omi_api` (host chatbot-gateway, kiểm hạn và domain token). Chỉ in bản tóm tắt.

## 1. Khảo sát kịch bản và Kho tri thức
Đường chính: `scripts/tenant_survey.py --out <scratch>/tenant_context.json`. Cần thêm số liệu Kho tri thức:
```python
import omi_api, omi_session
D = '<domain>'
T = omi_session.claims(omi_session.get_token(expect_domain=D))['tenant_id']
L  = omi_api.get('chatbot', '/callbot/script/list-by-tenant/' + T, expect_domain=D)['payload']
IE = omi_api.get('chatbot', '/callbot/intent/list-by-tenant/' + T, expect_domain=D)['payload']
TR = omi_api.post_json('chatbot', '/callbot/training/search_v3?page=1&size=1', {'keyword': '', 'tenantId': T}, expect_domain=D)['payload']
print({'scripts': [[s['id'], s['name'], s['type'], s['version'], len(s['nodes'])] for s in L],
       'intents': [[i['id'], i['code'], i['name']] for i in IE], 'trainings': TR['total_items']})
```

## 2. Đếm câu huấn luyện theo ý định
Dùng khi `tenant_survey.py` chưa đếm số câu theo ý định. Chạy sau khối §1 (dùng `D`, `T`, `IE`). Server trả tối đa 50 câu/trang → duyệt đủ trang (chỉ làm khi cần quyết định bù câu).
```python
items, p = [], 1
while True:
    r = omi_api.post_json('chatbot', '/callbot/training/search_v3?page=%d&size=100' % p,
                          {'keyword': '', 'tenantId': T}, expect_domain=D)['payload']
    items += r.get('items') or []
    if not r.get('items') or len(items) >= r['total_items']:
        break
    p += 1
code = {i['id']: i['code'] for i in IE}
cnt = {}
for t in items:
    k = code.get(t['intent_id'], t['intent_id'])
    cnt[k] = cnt.get(k, 0) + 1
print(cnt)
```

## 3. Theo dõi nhập file và huấn luyện
Chạy sau khối §1 (dùng `D`).
```python
st = omi_api.get('chatbot', '/callbot/training/upload_excel/status/<session>', expect_domain=D)['payload']
h = omi_api.get('chatbot', '/callbot/training/history/search?page=1&size=1', expect_domain=D)['payload']['items'][0]
print(st['completed'], st['successTotalRecord'], st['total'], st['errorTotalRecord'], h['status'], h['total_trainings'])
```
`<session>`: id phiên trong response `upload_excel` khi user tải file trên giao diện (đọc bằng công cụ xem request mạng của trình duyệt, chỉ lấy id phiên, không lấy header).

## 4. Lưu và kiểm kịch bản
Chỉ lưu bằng `scripts/omi_save.py callflow payload.json --domain <domain> --new|--update` (luôn chạy `verify_callflow.py` trước và sau khi lưu; `--update` còn so phiên bản mới nhất và cần `--confirm-update`). Không gọi `add_v2` trong trang, không sửa kịch bản bằng JS rồi lưu lại (bỏ qua các lớp kiểm của `omi_save`). Kiểm: `scripts/verify_callflow.py` (checklist C1..C7). Sau khi lưu chuyển tab editor sang id mới (`/ai/callbot/script/update/<id>`).

## 5. Đo chiều cao node để xếp bố cục (tuỳ chọn, chỉ đọc DOM)
```js
const d={};document.querySelectorAll('.react-flow__node').forEach(n=>d[n.getAttribute('data-id')]=n.offsetHeight);d
```
Node ngoài khung nhìn không có trong DOM → `build_callflow.py` ước lượng `120 + 90 × số nhánh`.
