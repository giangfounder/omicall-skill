#!/usr/bin/env python3
"""Tạo bản ghi 'Dữ liệu khác' từ 1 file FAQ rồi huấn luyện. In record _id. Không in token.
python rag_other.py <file.docx> --name <tên> --domain <domain>"""
import argparse, json, mimetypes, os, sys, time
sk = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'omicall-chatbot-gen-ai', 'scripts')
sys.path.insert(0, sk)
import rag_upload as R
import omi_bot_lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file'); ap.add_argument('--name', required=True); ap.add_argument('--domain', required=True)
    ap.add_argument('--timeout', type=float, default=300)
    a = ap.parse_args()
    ext = a.file.rsplit('.', 1)[-1].lower()
    fname = os.path.basename(a.file).lower()
    ctype = R.CTYPES.get(ext) or mimetypes.guess_type(fname)[0] or 'application/octet-stream'
    c = R.Client(omi_bot_lib.get_token(a.domain), R.FILESTORE, R.EXTERNAL)
    r1 = c.put_file(fname, open(a.file, 'rb').read(), ctype)
    info = (r1['payload'][0] or {}).get('object_info')
    r2 = c.post_json(R.WK + '/get_id_by_name', {'name': a.name}, 'get_id_by_name')
    ex = r2.get('data') if isinstance(r2, dict) else None
    if ex is None and isinstance(r2, dict):
        p2 = r2.get('payload'); ex = p2.get('data') if isinstance(p2, dict) else p2
    if ex:
        print(json.dumps({'status': 'DUPLICATE_NAME', 'name': a.name})); return 3
    body = {'name': a.name, 'language': 'vi', 'description': 'FAQ chuẩn hoá theo ngành (dữ liệu mẫu trình diễn)',
            'type': 'file', 'enable_training': True, 'url_website': '', 'url_sitemap': '',
            'object_info': {'file_name': fname, 'content_type': ctype, 'url_file': info['name'], 'file_type': ext},
            'add_bot_uuids': [], 'remove_bot_uuids': []}
    r3 = c.post_json(R.WK + '/add', body, 'other/add')
    rec = r3.get('payload') or {}
    if not rec.get('_id'):
        print(json.dumps({'status': 'ADD_FAILED', 'resp': json.dumps(r3, ensure_ascii=False)[:300]})); return 1
    rid = rec['_id']
    c.post_json(R.WK + '/training/' + rid, {}, 'other/training')
    deadline = time.time() + a.timeout; st = None
    while time.time() < deadline:
        found, st, _ = R.search_status(c, rid)
        if st == 'completed': break
        time.sleep(8)
    print(json.dumps({'status': 'OK', 'record_id': rid, 'file_id': rec.get('file_id'), 'training': st,
                      'name': a.name, 'file_name': fname}, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
