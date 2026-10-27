# -*- coding: utf-8 -*-
"""Nạp 1 file "Dữ liệu khác" (RAG) cho bot OmiBot bằng API rồi ghi vào payload bot. Không in token.

    python rag_upload.py <file> --bot <bot.json> [--name <tên>] [--description ..] [--language vi]
                         [--out payload.json] [--dry-run] [--api-base URL] [--timeout 600] [--poll 10]

Chuỗi đã kiểm chứng (references/api-reference.md mục "RAG — Dữ liệu khác" và "Tạo bot mới + nạp RAG"):
  1. filestore  POST /file_store/put_v2 (multipart field file_0, tên file viết thường) → object_info.name
  2. external   POST /omi_v2/warehouse_of_knowledge/other/get_id_by_name {"name"} → trùng tên thì DỪNG, hỏi user
  3. external   POST /omi_v2/warehouse_of_knowledge/other/add (add_bot_uuids = bot uuid) → record _id
  4. external   POST /omi_v2/warehouse_of_knowledge/other/training/<record _id>
  5. Ghi vector_store.vector_store_files (ref_id = record _id, KHÔNG phải file_id) + BEGIN ai_analyze.vector_store_ids
     vào payload (--out, mặc định scratch) → in lệnh lưu bằng omi_save.py bot (script này KHÔNG lưu bot)
  6. Poll POST /omi_v2/warehouse_of_knowledge/other/search tới status 'completed' hoặc hết --timeout. Mỗi lượt poll
     duyệt lần lượt page=1,2,... (size=10, body {}) tới khi thấy record _id hoặc hết trang (tối đa SEARCH_MAX_PAGES);
     thứ tự sắp xếp của search và cách lọc theo tên: Cần xác nhận → không dựa vào trang 1.
Payload ở bước 5 KHÔNG che bí mật (header Authorization của Truy vấn API...) vì omi_save cần bản thật để lưu —
chủ ý; vì vậy --out bị từ chối (exit 2) khi nằm trong thư mục skill hoặc repo.
Chạm giới hạn gói (quota) → dừng, exit 4, hỏi user: gỡ file cũ / gộp / nâng gói. Không tự xoá dữ liệu.
`bots_use_file` sau add: Cần xác nhận (2 lần chạy cho kết quả khác nhau) → script không dựa vào trường này.
vector_store_id / vector_store_file_id do server sinh khi lưu: Cần xác nhận — script để null nếu bot chưa có, GET lại kiểm.
--api-base: thay cả host filestore lẫn external (chỉ dùng cho test với stub 127.0.0.1).
Exit: 0 xong; 1 lỗi API; 2 sai cách gọi; 3 trùng tên; 4 quota; 5 hết thời gian chờ training.
"""
import argparse
import copy
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

FILESTORE = "https://filestore-v1-stg.omicrm.com"
EXTERNAL = "https://external-v1-stg.omicrm.com"
QS = "lng=vi&utm_source=web"
WK = "/omi_v2/warehouse_of_knowledge/other"
MAX_BYTES = 15 * 1024 * 1024
ALLOWED = {"xls", "xlsx", "doc", "docx", "pdf", "txt", "rtf"}
CTYPES = {"txt": "text/plain", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "doc": "application/msword", "pdf": "application/pdf", "rtf": "application/rtf",
          "xls": "application/vnd.ms-excel", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
SEARCH_SIZE = 10
SEARCH_MAX_PAGES = 50
QUOTA_WORDS = ("quota", "giới hạn", "gioi han", "limit", "vượt quá", "exceed")


class ApiError(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


def is_quota(text):
    t = str(text).lower()
    return any(w in t for w in QUOTA_WORDS)


class Client:
    def __init__(self, token, filestore, external, timeout=120):
        self.tok = token
        self.fs = filestore.rstrip("/")
        self.ex = external.rstrip("/")
        self.timeout = timeout

    def _send(self, url, data, ctype, step):
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", "Bearer " + self.tok)
        req.add_header("Content-Type", ctype)
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace") if e.fp else ""
            try:  # bỏ escape \uXXXX để nhận ra thông báo tiếng Việt "đạt giới hạn"
                body = json.dumps(json.loads(body), ensure_ascii=False)
            except ValueError:
                pass
            if e.code == 401:
                raise ApiError("%s: HTTP 401 — token hết hạn hoặc sai tenant → chạy omi_preflight.py" % step)
            if is_quota(body):
                raise ApiError("%s: quota — đã đạt giới hạn gói (HTTP %d). Hỏi user: gỡ file cũ khỏi Dữ liệu khác / "
                               "gộp nội dung / nâng gói." % (step, e.code), 4)
            raise ApiError("%s: HTTP %d" % (step, e.code))
        try:
            obj = json.loads(body)
        except ValueError:
            raise ApiError("%s: phản hồi không phải JSON" % step)
        if isinstance(obj, dict) and obj.get("payload") is None and is_quota(json.dumps(obj, ensure_ascii=False)):
            raise ApiError("%s: quota — đã đạt giới hạn gói. Hỏi user: gỡ file cũ khỏi Dữ liệu khác / gộp nội dung / "
                           "nâng gói." % step, 4)
        return obj

    def post_json(self, path, body, step):
        return self._send(self.ex + path + ("&" if "?" in path else "?") + QS,
                          json.dumps(body, ensure_ascii=False).encode("utf-8"), "application/json", step)

    def put_file(self, fname, content, ctype):
        boundary = "----omi" + uuid.uuid4().hex
        head = ("--%s\r\nContent-Disposition: form-data; name=\"file_0\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                % (boundary, fname, ctype)).encode("utf-8")
        data = head + content + ("\r\n--%s--\r\n" % boundary).encode("utf-8")
        url = (self.fs + "/file_store/put_v2?business_type=warehouse_of_knowledge_files&keep_content_type=true&" + QS)
        return self._send(url, data, "multipart/form-data; boundary=" + boundary, "put_v2")


def search_status(c, record_id):
    """Tìm record_id qua các trang other/search. Trả (found, status, pages_read)."""
    for page in range(1, SEARCH_MAX_PAGES + 1):
        r = c.post_json(WK + "/search?page=%d&size=%d" % (page, SEARCH_SIZE), {}, "other/search")
        its = (((r or {}).get("payload") or {}).get("items") or []) if isinstance(r, dict) else []
        for it in its:
            if isinstance(it, dict) and it.get("_id") == record_id:
                return True, it.get("status"), page
        if len(its) < SEARCH_SIZE:
            return False, None, page
    return False, None, SEARCH_MAX_PAGES


def find_begin(bot):
    camp = bot.get("campaign") or {}
    return next((n for n in camp.get("nodes") or [] if n.get("node_type") == "BEGIN_CONTEXT"), None)


def attach(bot, record_id, file_id, language, status):
    """Ghi file vào vector_store + BEGIN vector_store_ids (api-reference.md bước 5). ref_id = record _id."""
    bot = copy.deepcopy(bot)
    vs = bot.get("vector_store")
    if not isinstance(vs, dict):
        vs = {"vector_store_id": None, "vector_store_files": [], "all_file_ref_ids": []}
    files = [f for f in vs.get("vector_store_files") or [] if f.get("ref_id") != record_id]
    files.append({"vector_store_file_id": None, "file_id": file_id, "file_training_status": status,
                  "ref_id": record_id, "language": language, "total_website": None, "is_post": False})
    vs["vector_store_files"] = files
    refs = [r for r in vs.get("all_file_ref_ids") or [] if r != record_id] + [record_id]
    vs["all_file_ref_ids"] = refs
    bot["vector_store"] = vs
    begin = find_begin(bot)
    if begin is None:
        raise ApiError("payload bot không có BEGIN_CONTEXT", 2)
    ids = begin.setdefault("ai_analyze", {}).setdefault("vector_store_ids", [])
    if record_id not in ids:
        ids.append(record_id)
    return bot


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Nạp file Dữ liệu khác (RAG) cho bot và ghi vào payload (không lưu bot).")
    ap.add_argument("file")
    ap.add_argument("--bot", required=True, help="payload/GET bot (lấy uuid và ghi vector_store)")
    ap.add_argument("--name", help="tên bản ghi Dữ liệu khác (mặc định tên file không đuôi)")
    ap.add_argument("--description", default="")
    ap.add_argument("--language", default="vi")
    ap.add_argument("--out", help="payload đã gắn RAG (mặc định OMI_SCRATCH/thư mục tạm)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in các request sẽ gửi, không gọi mạng")
    ap.add_argument("--api-base", help="thay host filestore và external (chỉ stub test 127.0.0.1/localhost)")
    ap.add_argument("--domain", default=os.environ.get("OMI_DOMAIN"), help="domain tenant để kiểm token")
    ap.add_argument("--timeout", type=float, default=600, help="giây chờ training completed")
    ap.add_argument("--poll", type=float, default=10, help="giây giữa 2 lần poll other/search")
    a = ap.parse_args(argv)

    if a.api_base:
        host = (urllib.parse.urlsplit(a.api_base).hostname or "").lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            print("--api-base chỉ nhận host 127.0.0.1/localhost/[::1] (stub test); không gửi token tới host khác: %s"
                  % (host or a.api_base), file=sys.stderr)
            return 2
    if a.out:
        import omi_bot_lib
        try:
            a.out = omi_bot_lib.guard_out_path(a.out)
        except SystemExit as e:
            return e.code
    if not os.path.isfile(a.file):
        print("Không thấy file %s" % a.file, file=sys.stderr)
        return 2
    ext = a.file.rsplit(".", 1)[-1].lower() if "." in os.path.basename(a.file) else ""
    if ext not in ALLOWED:
        print("Đuôi .%s không hỗ trợ (cho phép: %s)" % (ext, ", ".join(sorted(ALLOWED))), file=sys.stderr)
        return 2
    size = os.path.getsize(a.file)
    if size > MAX_BYTES:
        print("File %.1f MB > 15 MB (giới hạn mỗi file)" % (size / 1048576.0), file=sys.stderr)
        return 2
    with open(a.bot, encoding="utf-8") as f:
        bot = json.load(f)
    if isinstance(bot, dict) and isinstance(bot.get("payload"), dict) and "campaign" not in bot:
        bot = bot["payload"]
    bot_uuid = bot.get("uuid")
    if not bot_uuid:
        print("Payload bot thiếu uuid (add_bot_uuids dùng bot uuid, không phải _id)", file=sys.stderr)
        return 2
    if find_begin(bot) is None:
        print("Payload bot không có BEGIN_CONTEXT", file=sys.stderr)
        return 2
    fname = os.path.basename(a.file).lower()
    name = a.name or fname.rsplit(".", 1)[0]
    ctype = CTYPES.get(ext) or mimetypes.guess_type(fname)[0] or "application/octet-stream"
    fs = a.api_base or FILESTORE
    ex = a.api_base or EXTERNAL

    plan = [
        "POST %s/file_store/put_v2?business_type=warehouse_of_knowledge_files&keep_content_type=true (file_0=%s, %d byte)"
        % (fs, fname, size),
        "POST %s%s/get_id_by_name {\"name\": %s}" % (ex, WK, json.dumps(name, ensure_ascii=False)),
        "POST %s%s/add {name, language:%s, type:file, enable_training:true, object_info{url_file=<object name bước 1>, "
        "file_type:%s}, add_bot_uuids:[<bot uuid>]}" % (ex, WK, a.language, ext),
        "POST %s%s/training/<record _id>" % (ex, WK),
        "ghi vector_store + ai_analyze.vector_store_ids (ref_id = record _id) vào payload",
        "POST %s%s/search?page=1..%d&size=%d (poll tới completed, tối đa %ds)"
        % (ex, WK, SEARCH_MAX_PAGES, SEARCH_SIZE, a.timeout),
    ]
    if a.dry_run:
        print("DRY-RUN — không gửi request nào. Header Authorization: Bearer *** (che).")
        for i, p in enumerate(plan, 1):
            print("%d. %s" % (i, p))
        return 0

    import omi_bot_lib
    tok = omi_bot_lib.get_token(a.domain)
    c = Client(tok, fs, ex)
    try:
        with open(a.file, "rb") as f:
            content = f.read()
        r1 = c.put_file(fname, content, ctype)
        items = r1.get("payload") if isinstance(r1, dict) else None
        info = (items[0] or {}).get("object_info") if isinstance(items, list) and items else None
        if not isinstance(info, dict) or not info.get("name"):
            raise ApiError("put_v2: không thấy payload[0].object_info.name")
        print("1. put_v2 OK → object name đã nhận")
        r2 = c.post_json(WK + "/get_id_by_name", {"name": name}, "get_id_by_name")
        # tài liệu: "`data` non-empty = đã tồn tại"; vị trí `data` (gốc hay trong payload) — Cần xác nhận, xét cả hai
        existing = r2.get("data") if isinstance(r2, dict) else None
        if existing is None and isinstance(r2, dict):
            p2 = r2.get("payload")
            existing = p2.get("data") if isinstance(p2, dict) else p2
        if existing:
            print("2. Đã có bản ghi Dữ liệu khác tên '%s' → DỪNG. Hỏi user: dùng lại bản ghi cũ hay đổi --name." % name)
            return 3
        print("2. get_id_by_name: chưa trùng tên")
        body = {"name": name, "language": a.language, "description": a.description, "type": "file",
                "enable_training": True, "url_website": "", "url_sitemap": "",
                "object_info": {"file_name": fname, "content_type": ctype, "url_file": info["name"], "file_type": ext},
                "add_bot_uuids": [bot_uuid], "remove_bot_uuids": []}
        r3 = c.post_json(WK + "/add", body, "other/add")
        rec = (r3 or {}).get("payload") if isinstance(r3, dict) else None
        if not isinstance(rec, dict) or not rec.get("_id"):
            if is_quota(json.dumps(r3, ensure_ascii=False)):
                raise ApiError("other/add: quota — đã đạt giới hạn gói. Hỏi user: gỡ file cũ / gộp / nâng gói.", 4)
            raise ApiError("other/add: không thấy payload._id")
        record_id, file_id = rec["_id"], rec.get("file_id")
        print("3. other/add OK → record _id=%s (status=%s)" % (record_id, rec.get("status")))
        r4 = c.post_json(WK + "/training/" + urllib.parse.quote(str(record_id)), {}, "other/training")
        if not (isinstance(r4, dict) and r4.get("payload")):
            raise ApiError("other/training: payload không phải true")
        print("4. other/training OK")
        new_bot = attach(bot, record_id, file_id, a.language, rec.get("status") or "not_training")
        out = a.out or os.path.join(omi_bot_lib.scratch_dir(), "bot_rag_payload.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(new_bot, f, ensure_ascii=False, indent=1)
        print("5. Đã ghi payload: %s (ref_id = record _id). Lưu nháp: python <thư mục skill>/scripts/omi_save.py bot %s "
              "--domain <domain>" % (out, out))
        deadline = time.time() + a.timeout
        while True:
            found, st, pages = search_status(c, record_id)
            if st == "completed":
                print("6. Training completed")
                return 0
            if time.time() + a.poll > deadline:
                if not found:
                    print("6. Hết %ds: KHÔNG THẤY record _id=%s trong other/search (đã đọc %d trang × %d) — "
                          "khác với 'chưa train xong'; kiểm tab Đào tạo trên UI (Cần xác nhận thứ tự/lọc của search)"
                          % (a.timeout, record_id, pages, SEARCH_SIZE))
                else:
                    print("6. Hết %ds, record có trong other/search nhưng status=%s (chưa completed) — kiểm lại sau "
                          "bằng other/search hoặc tab Đào tạo" % (a.timeout, st))
                return 5
            time.sleep(a.poll)
    except ApiError as e:
        print("LỖI %s" % e, file=sys.stderr)
        return e.code
    except (urllib.error.URLError, OSError) as e:
        print("LỖI mạng: %s" % type(e).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
