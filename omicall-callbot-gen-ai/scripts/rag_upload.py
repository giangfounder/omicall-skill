"""Tải file kho tri thức (RAG) lên "File đào tạo" của kịch bản Callbot SmartAgent, rồi ghi vào payload để lưu.

  python <thư mục skill>/scripts/rag_upload.py <file.docx> [file2.pdf ...] --base GET.json --out payload.json
         [--replace] [--dry-run]
  python <thư mục skill>/scripts/omi_save.py callbot payload.json --domain <domain> --update --confirm-update --base GET.json

Chuỗi lấy từ mã editor (chunk kịch bản callbot, đọc 10/2026), khớp dữ liệu thật của kịch bản đã tải file qua giao diện:
  1) POST filestore /file_store/put?business_type=callbot_recording_file&keep_content_type=true
     multipart: 'image' = file, 'name' = tên file (một file mỗi request, giống editor).
     Phản hồi: payload[0].object_info.name = "<tenant_id>/callbot_recording_file/<yyyy>/<mm>/<uuid>.<đuôi>".
  2) url = "https://cdn.omicrm.com/crm/" + object name; id = uuid mới; name = tên file gốc.
  3) Ghi {"id","name","url"} vào CẢ HAI chỗ (editor đọc org_nodes, runtime đọc nodes):
       nodes[BEGIN].ai_agent_config.knowledge.files[]
       org_nodes[BEGIN].data.selectedTraining[]  (+ data.typeTrainingFile = "file")
  4) Lưu bằng omi_save.py callbot --update (add_v2). Không có bước "huấn luyện" riêng trong editor: server xử lý khi lưu.
     Cần xác nhận lần đầu: gọi thử hỏi một câu có trong file mới.
Chế độ "other" (chọn bản ghi Dữ liệu khác thay vì tải file): files[] = {"id","name","other_wok_id": <_id bản ghi>},
typeTrainingFile = "other"; tạo bản ghi bằng chuỗi RAG của skill omicall-chatbot-gen-ai (rag_upload.py bên đó).

--replace: bỏ các file cũ, chỉ giữ file vừa tải. Mặc định nối thêm, bỏ qua file trùng tên.
--dry-run: không gửi gì, chỉ in việc sẽ làm.
Token: omi_session (Bearer, kiểm hạn); không in token. Exit: 0 xong; 2 sai cách gọi; 4 lỗi API.
"""
import argparse
import json
import mimetypes
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omi_api  # noqa: E402

UPLOAD_PATH = '/file_store/put?business_type=callbot_recording_file&keep_content_type=true'
CDN = 'https://cdn.omicrm.com/crm/'
EXTS = ('.doc', '.docx', '.pdf', '.txt', '.xls', '.xlsx', '.rtf')
MAX_MB = 15  # theo giới hạn Dữ liệu khác bên chatbot; Cần xác nhận cho callbot


def die(code, msg):
    sys.stderr.write(msg + '\n')
    sys.exit(code)


def payload_of(obj):
    return obj.get('payload', obj) if isinstance(obj, dict) else obj


def begin_nodes(script):
    node = next((n for n in script.get('nodes') or [] if n.get('ai_agent_config') is not None
                 or n.get('node_type') == 'BEGIN'), None)
    org = next((n for n in script.get('org_nodes') or [] if n.get('type') == 'BEGIN'
                or (n.get('data') or {}).get('type') == 'BEGIN'), None)
    if node is None or org is None:
        die(2, 'không thấy node BEGIN trong nodes/org_nodes của --base')
    return node, org


def upload(path):
    rq = omi_api._requests()
    name = os.path.basename(path)
    ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    with open(path, 'rb') as f:
        r = rq.post(omi_api.url('filestore', UPLOAD_PATH), headers=omi_api._headers(),
                    files={'image': (name, f, ctype)}, data={'name': name}, timeout=omi_api.TIMEOUT)
    body = payload_of(omi_api._handle(r))
    item = body[0] if isinstance(body, list) and body else body
    obj_name = ((item or {}).get('object_info') or {}).get('name') if isinstance(item, dict) else None
    if not obj_name:
        raise omi_api.ApiError('phản hồi upload không có payload[0].object_info.name: %s'
                               % omi_api.mask_text(json.dumps(body, ensure_ascii=False)[:300]))
    return {'id': str(uuid.uuid1()), 'name': name, 'url': CDN + obj_name}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('files', nargs='+')
    ap.add_argument('--base', required=True, help='bản GET kịch bản (/callbot/script/get/{id}), chưa che')
    ap.add_argument('--out', required=True, help='payload để lưu bằng omi_save.py callbot --update')
    ap.add_argument('--replace', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)

    for p in a.files:
        if not os.path.isfile(p):
            die(2, 'không thấy file: %s' % p)
        if not p.lower().endswith(EXTS):
            die(2, 'đuôi không hỗ trợ: %s (nhận %s)' % (p, ', '.join(EXTS)))
        if os.path.getsize(p) > MAX_MB * 1024 * 1024:
            die(2, 'file quá %d MB: %s' % (MAX_MB, p))

    with open(a.base, encoding='utf-8') as f:
        script = payload_of(json.load(f))
    node, org = begin_nodes(script)
    knowledge = node.setdefault('ai_agent_config', {}).setdefault('knowledge', {})
    data = org.setdefault('data', {})
    old = [] if a.replace else list(knowledge.get('files') or [])
    if data.get('typeTrainingFile') == 'other' and old:
        die(2, 'kịch bản đang dùng chế độ "other" (Dữ liệu khác); chạy lại với --replace nếu muốn đổi sang tải file')
    names = {x.get('name') for x in old}

    added = []
    for p in a.files:
        name = os.path.basename(p)
        if name in names:
            print('bỏ qua (trùng tên đã có): %s' % name)
            continue
        names.add(name)
        if a.dry_run:
            print('[dry-run] POST filestore%s  image=%s' % (UPLOAD_PATH, name))
            continue
        try:
            entry = upload(p)
        except omi_api.ApiError as e:
            die(4, 'upload lỗi %s: %s' % (name, e))
        added.append(entry)
        print('đã tải: %s -> %s' % (name, entry['url']))

    if a.dry_run:
        return 0
    files = old + added
    knowledge['files'] = files
    data['selectedTraining'] = [dict(x) for x in files]
    data['typeTrainingFile'] = 'file'
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False)
    print('knowledge.files: %d file (%d mới) -> %s' % (len(files), len(added), a.out))
    print('Tiếp: omi_save.py callbot %s --domain <domain> --update --confirm-update --base %s' % (a.out, a.base))
    return 0


if __name__ == '__main__':
    sys.exit(main())
