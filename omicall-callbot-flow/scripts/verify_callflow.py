"""Kiểm payload / bản GET kịch bản Callbot NORMAL theo checklist api-reference.md §6 (C1..C7) — chỉ đọc, không sửa.

  python verify_callflow.py <saved.json> [--sent payload.json] [--context tenant_context.json] [--mode pre|post]
                            [--base <bản GET dùng làm gốc>.json | --base-version N]

- pre : kiểm payload trước khi lưu (saved.json = payload do build_callflow.py sinh).
- post: kiểm bản GET lại sau khi lưu (saved.json = kết quả callbot/script/get/{id}, có hoặc không có vỏ "payload");
        --sent = payload đã gửi để so số node/dây.
        Version tăng (C7): so version bản GET với version cũ lấy từ --base (bản GET đã dùng làm gốc khi sửa),
        --base-version, hoặc 'version' trong --sent nếu có. Không có version cũ → WARN C7 (kịch bản mới: bỏ qua).
--context đọc Kho tri thức ở khối `kho_tri_thuc` (khuôn tenant_survey.py: intents, entity_types, training_history);
khối cũ `callbot_kb` (intents, entities/entity_types, training_status) vẫn đọc được, có cả hai thì gộp theo mã.
Mỗi dòng: `PASS|FAIL|WARN <mã> <mô tả> [json path]`; dòng cuối `RESULT PASS|FAIL`.
Exit 0 khi không có FAIL (WARN vẫn qua); 1 khi có FAIL, kể cả file mở được nhưng không phải JSON hợp lệ hoặc không
phải object; 2 khi sai cách gọi (tham số sai) hoặc không mở được file (không tồn tại, không có quyền).
Mã C1..C7 trùng số mục checklist api-reference.md §6; X<n> là mục bổ sung.
Không gọi mạng. Mục không tự kiểm được (huấn luyện SUCCESS khi context không có) in WARN để người soát.
"""
import argparse
import json
import re
import sys
from collections import Counter

PLACEHOLDER = re.compile(r"<[^<>\n]{1,80}>")
BRANCH_TYPES = ("INTENT", "CUSTOMER_NOT_RESPONSE", "CUSTOMER_RESPONSE_WRONG", "CUSTOMER_RESPONSE", "KEYWORD")
OUT = []


def emit(level, code, msg, path=""):
    OUT.append(level)
    print(f"{level} {code} {msg}" + (f" [{path}]" if path else ""))


def load(path, what):
    try:
        f = open(path, encoding="utf-8")
    except OSError as e:
        print(f"FAIL X0 không mở được {what} {path}: {e}")
        print("RESULT FAIL")
        sys.exit(2)
    try:
        with f:
            obj = json.load(f)
    except (OSError, ValueError) as e:
        print(f"FAIL X0 {what} {path} không phải JSON hợp lệ: {e}")
        print("RESULT FAIL")
        sys.exit(1)
    if isinstance(obj, dict) and isinstance(obj.get("payload"), dict) and "nodes" in obj["payload"]:
        obj = obj["payload"]
    return obj


def kb_of(ctx):
    """Gộp Kho tri thức từ context: khối `kho_tri_thuc` (tenant_survey.py) và khối cũ `callbot_kb`/top-level.
    Trả về (intents theo mã, entities theo mã, trạng thái huấn luyện mới nhất hoặc None)."""
    new = ctx.get("kho_tri_thuc") if isinstance(ctx.get("kho_tri_thuc"), dict) else {}
    old = ctx.get("callbot_kb") if isinstance(ctx.get("callbot_kb"), dict) else {}

    def as_list(v):
        # nhận cả mảng bản ghi lẫn map {mã: bản ghi} (cùng cách đọc với build_callflow._as_map)
        if isinstance(v, dict):
            return [dict(x, code=x.get("code") or k) for k, x in v.items() if isinstance(x, dict)]
        return v if isinstance(v, list) else []

    def merge(label, *lists):
        # bản sau ghi đè trường có giá trị: khối cũ callbot_kb trước, kho_tri_thuc (khảo sát mới) sau -> khảo sát mới thắng
        out = {}
        for lst in lists:
            for x in as_list(lst):
                if isinstance(x, dict) and x.get("code"):
                    cur = out.setdefault(x["code"], {})
                    if cur.get("id") and x.get("id") and cur["id"] != x["id"]:
                        emit("WARN", "C4", f"context: {label} '{x['code']}' có id khác nhau giữa callbot_kb và kho_tri_thuc "
                                           "— dùng kho_tri_thuc (khảo sát mới); xoá khối cũ nếu đã lỗi thời")
                    cur.update({k: v for k, v in x.items() if v not in (None, "") or k not in cur})
        return out
    intents = merge("ý định", old.get("intents") or ctx.get("intents"), new.get("intents"))
    entities = merge("thực thể", old.get("entities") or old.get("entity_types") or ctx.get("entities"),
                     new.get("entity_types") or new.get("entities"))
    st = old.get("training_status")
    hist = [h for h in new.get("training_history") or [] if isinstance(h, dict)]
    if not st and hist:
        dated = [h for h in hist if h.get("created_date") is not None]
        try:
            latest = max(dated, key=lambda h: h["created_date"]) if len(dated) == len(hist) else hist[0]
        except TypeError:
            latest = hist[0]
        st = latest.get("status")
    return intents, entities, st


def texts_of(n):
    out = [n.get("template_content") or ""]
    out += [c.get("content") or "" for c in n.get("return_contents") or [] if isinstance(c, dict)]
    return [t for t in out if t]


def check(doc, sent=None, ctx=None, mode="pre", base_version=None):
    nodes = doc.get("nodes")
    org = doc.get("org_nodes")
    conns = doc.get("connections")
    if not isinstance(nodes, list) or not isinstance(org, list) or not isinstance(conns, list):
        emit("FAIL", "X1", "thiếu nodes/org_nodes/connections dạng mảng")
        return
    for k, lst in (("nodes", nodes), ("org_nodes", org), ("connections", conns)):
        for i, x in enumerate(lst):
            if not isinstance(x, dict):
                emit("FAIL", "X1", f"phần tử không phải object ({type(x).__name__}) — bỏ qua khi kiểm tiếp", f"{k}[{i}]")
    nodes = [x for x in nodes if isinstance(x, dict)]
    org = [x for x in org if isinstance(x, dict)]
    conns = [x for x in conns if isinstance(x, dict)]
    if sent is not None and not isinstance(sent, dict):
        emit("FAIL", "X5", "--sent không phải object JSON — bỏ qua so với payload đã gửi")
        sent = None
    if ctx is not None and not isinstance(ctx, dict):
        emit("FAIL", "C4", "--context không phải object JSON — bỏ qua đối chiếu Kho tri thức")
        ctx = None
    N = {n.get("id"): n for n in nodes}
    O = {o.get("id"): o for o in org}

    # X2 — loại kịch bản, placeholder, id/uuid
    if doc.get("type") != "NORMAL":
        emit("FAIL", "X2", f"type = {doc.get('type')!r}, cần 'NORMAL' (AI_AGENT dùng omicall-callbot-gen-ai)", "type")
    ph = Counter()
    for m in PLACEHOLDER.findall(json.dumps(doc, ensure_ascii=False)):
        ph[m] += 1
    if ph:
        emit("FAIL", "X3", f"còn {sum(ph.values())} placeholder: " + ", ".join(f"{k} x{v}" for k, v in ph.most_common(5)))
    if bool(doc.get("id")) != bool(doc.get("uuid")) and mode == "pre":
        emit("FAIL", "X4", "chỉ có một trong id/uuid — cập nhật phải gửi CẢ id + uuid của bản mới nhất (chỉ id sinh kịch bản trùng)")

    # C1 — next_nodes tồn tại; CONDITION con của STAFF nằm trong org STAFF.data.conditions
    f0 = OUT.count("FAIL")
    for i, n in enumerate(nodes):
        for t in n.get("next_nodes") or []:
            if t not in N:
                emit("FAIL", "C1", f"node {n.get('id')} trỏ tới node không tồn tại {t}", f"nodes[{i}].next_nodes")
        for j, c in enumerate(n.get("conditions") or []):
            for t in c.get("next_nodes") or []:
                if t not in N:
                    emit("FAIL", "C1", f"FROM_SYSTEM {n.get('id')} nhánh {c.get('name')} trỏ tới node không tồn tại {t}",
                         f"nodes[{i}].conditions[{j}]")
    for n in nodes:
        if n.get("node_type") != "STAFF":
            continue
        o = O.get(n["id"])
        if not o:
            emit("FAIL", "C1", f"STAFF {n['id']} không có bản editor trong org_nodes")
            continue
        org_ids = set()
        for c in (o.get("data") or {}).get("conditions") or []:
            org_ids.add(c.get("id"))
            org_ids.add(c.get("conditionId"))
        for t in n.get("next_nodes") or []:
            tn = N.get(t) or {}
            if tn.get("node_type") == "CONDITION" and tn.get("condition_type") in BRANCH_TYPES and t not in org_ids:
                emit("FAIL", "C1", f"nhánh {t} ({tn.get('condition_type')}) của STAFF {n['id']} không có trong org_nodes[STAFF].data.conditions")
    if OUT.count("FAIL") == f0:
        emit("PASS", "C1", "next_nodes trỏ node tồn tại; nhánh của STAFF có trong editor")

    # C2 — nhánh có câu trả lời phải có đích; repeat editor khớp số câu
    f0 = OUT.count("FAIL")
    for n in nodes:
        if n.get("node_type") == "CONDITION" and n.get("return_contents") and not n.get("next_nodes"):
            emit("FAIL", "C2", f"nhánh {n['id']} ({n.get('condition_type')}) có return_contents nhưng thiếu next_nodes")
    for o in org:
        if o.get("type") != "STAFF":
            continue
        for c in (o.get("data") or {}).get("conditions") or []:
            t = c.get("type")
            rid = c.get("conditionId") if t in ("CUSTOMER_NOT_RESPONSE", "CUSTOMER_RESPONSE_WRONG") else c.get("id")
            rn = N.get(rid)
            if t == "COLLECT_INFO" or not rn:
                continue
            k = len(rn.get("return_contents") or [])
            rep = c.get("repeat")
            if t == "INTENT":
                want = str(k) if k else "0"
                got = rep.get("value") if isinstance(rep, dict) else None
                if got != want:
                    emit("FAIL", "C2", f"repeat editor của nhánh INTENT {rid} = {got!r}, số câu runtime = {k} (cần {want!r})", f"org_nodes[{o['id']}]")
            elif t == "CUSTOMER_NOT_RESPONSE":
                got = rep.get("value") if isinstance(rep, dict) else None
                if got != str(k):
                    emit("FAIL", "C2", f"repeat editor của NOT_RESPONSE {rid} = {got!r}, số câu runtime = {k}", f"org_nodes[{o['id']}]")
            elif t == "CUSTOMER_RESPONSE_WRONG" and not isinstance(rep, int):
                emit("FAIL", "C2", f"repeat editor của RESPONSE_WRONG {rid} phải là số (0), đang là {rep!r}", f"org_nodes[{o['id']}]")
    if OUT.count("FAIL") == f0:
        emit("PASS", "C2", "nhánh có câu trả lời đều có đích; repeat editor khớp số câu")
    emit("WARN", "C2", "đích của nhánh hỏi đáp/lặp lại/phản hồi sai (phải về bước báo chuyển) — soát theo spec, script không suy được ý nghiệp vụ")

    # C3 — STAFF chờ khách có NR + RW
    f0 = OUT.count("FAIL")
    for n in nodes:
        if n.get("node_type") != "STAFF":
            continue
        kinds = [N.get(t, {}).get("condition_type") for t in n.get("next_nodes") or [] if N.get(t, {}).get("node_type") == "CONDITION"]
        waiting = [k for k in kinds if k in BRANCH_TYPES]
        if not waiting:
            continue
        for need in ("CUSTOMER_NOT_RESPONSE", "CUSTOMER_RESPONSE_WRONG"):
            if need not in waiting:
                emit("FAIL", "C3", f"STAFF {n['id']} ({n.get('name', '')}) chờ khách nhưng thiếu nhánh {need}")
    if OUT.count("FAIL") == f0:
        emit("PASS", "C3", "mọi STAFF chờ khách có NOT_RESPONSE + RESPONSE_WRONG")

    # C4 — intent/entity có trong Kho tri thức (context); huấn luyện SUCCESS
    ic = Counter(n.get("intent_code") for n in nodes if n.get("intent_code"))
    ec = Counter(n.get("entity_code") for n in nodes if n.get("entity_code"))
    if ctx is None:
        emit("WARN", "C4", f"không có --context: chưa đối chiếu {len(ic)} mã ý định, {len(ec)} mã thực thể với Kho tri thức")
    else:
        known_i, known_e, st = kb_of(ctx)
        f0 = OUT.count("FAIL")
        for c in sorted(ic):
            if c not in known_i:
                emit("FAIL", "C4", f"ý định '{c}' không có trong Kho tri thức (context)")
        for c in sorted(ec):
            if c not in known_e:
                emit("FAIL", "C4", f"thực thể '{c}' không có trong Kho tri thức (context)")
        for o in org:
            for c in (o.get("data") or {}).get("conditions") or []:
                it = c.get("intent") or {}
                ki = known_i.get(it.get("code"))
                if ki and ki.get("id") and it.get("id") != ki.get("id"):
                    emit("FAIL", "C4", f"editor: ý định {it.get('code')} id {it.get('id')} khác Kho tri thức {ki.get('id')}", f"org_nodes[{o.get('id')}]")
                if not ki or not it:
                    continue
                sid = ki.get("system_intent_id")
                if sid and it.get("systemIntentId") != sid:
                    emit("FAIL", "C4", f"editor: ý định hệ thống {it.get('code')} systemIntentId {it.get('systemIntentId')!r} khác Kho tri thức {sid!r}",
                         f"org_nodes[{o.get('id')}]")
                elif ki.get("is_system") is True and not it.get("systemIntentId"):
                    emit("FAIL", "C4", f"editor: ý định hệ thống {it.get('code')} có systemIntentId rỗng (Kho tri thức ghi is_system=true)",
                         f"org_nodes[{o.get('id')}]")
                elif ki.get("is_system") is None and not it.get("systemIntentId"):
                    emit("WARN", "C4", f"editor: ý định {it.get('code')} có systemIntentId rỗng và context không ghi is_system "
                                       "— Cần xác nhận system_intent_id (intent/list-by-tenant)", f"org_nodes[{o.get('id')}]")
        no_sid = sorted(c for c in ic if (known_i.get(c) or {}).get("is_system") is True and not (known_i.get(c) or {}).get("system_intent_id"))
        if no_sid:
            emit("WARN", "C4", "context thiếu system_intent_id của ý định hệ thống: " + ", ".join(no_sid)
                 + " — chưa đối chiếu được systemIntentId với Kho tri thức (lấy từ intent/list-by-tenant)")
        tid = (ctx.get("tenant") or {}).get("tenant_id") or ctx.get("tenant_id")
        if tid and not PLACEHOLDER.fullmatch(str(tid)) and doc.get("tenant_id") != tid:
            emit("FAIL", "C4", f"tenant_id payload khác context", "tenant_id")
        if OUT.count("FAIL") == f0:
            emit("PASS", "C4", f"{len(ic)} mã ý định, {len(ec)} mã thực thể có trong Kho tri thức")
        if st == "SUCCESS":
            emit("PASS", "C4", "huấn luyện mới nhất SUCCESS (theo context)")
        else:
            emit("WARN", "C4", f"huấn luyện mới nhất: {st or 'chưa rõ'} — chờ training/history/search = SUCCESS trước khi gọi thử")

    # C5 — TRANSFER có ids + transfer_collected_info
    f0 = OUT.count("FAIL")
    nx = 0
    for n in nodes:
        for a in n.get("actions") or []:
            if a.get("type") != "TRANSFER_CALL":
                continue
            nx += 1
            d = a.get("data") or {}
            if not [x for x in d.get("ids") or [] if x]:
                emit("FAIL", "C5", f"TRANSFER_CALL ở node {n.get('id')} có ids rỗng")
            if d.get("transfer_collected_info") is not True:
                emit("FAIL", "C5", f"TRANSFER_CALL ở node {n.get('id')} chưa bật transfer_collected_info")
            if ctx is not None and d.get("ids"):
                ag = {str(x.get("agent_id") or x.get("id")) for x in ctx.get("agents") or [] if isinstance(x, dict)}
                for x in d["ids"]:
                    if ag and x not in ag:
                        emit("WARN", "C5", f"TRANSFER_CALL ids {x} không có trong context.agents (agent_id)")
    if OUT.count("FAIL") == f0:
        emit("PASS", "C5", f"{nx} hành động chuyển máy có ids nhân viên + transfer_collected_info")

    # C6 — biến khai báo; không còn 'anh/chị' trần
    f0 = OUT.count("FAIL")
    top = {v.get("field_code") for v in doc.get("variables") or [] if isinstance(v, dict)}
    for n in nodes:
        local = {v.get("field_code") for v in n.get("variables") or [] if isinstance(v, dict)}
        for t in texts_of(n):
            for v in re.findall(r"\{\{(\w+)\}\}", t):
                if v.startswith("diff_days_"):
                    continue
                if v not in local:
                    emit("FAIL", "C6", f"node {n.get('id')}: biến {{{{{v}}}}} chưa khai báo trong variables của node")
                if v not in top:
                    emit("FAIL", "C6", f"node {n.get('id')}: biến {{{{{v}}}}} chưa khai báo top-level variables")
            if re.search(r"anh/chị", t, re.I):
                emit("FAIL", "C6", f"node {n.get('id')}: lời còn 'anh/chị' trần — dùng {{{{gender1_ai}}}}")
    if OUT.count("FAIL") == f0:
        emit("PASS", "C6", "biến {{...}} đã khai báo ở node + top-level; không còn 'anh/chị' trần")

    # C7 — connections khớp next_nodes (theo từng nhánh: nguồn, id nhánh, đích); version
    f0 = OUT.count("FAIL")
    want = Counter()
    for n in nodes:
        nt = n.get("node_type")
        if nt == "CONDITION" and n.get("condition_type") == "FROM_SYSTEM":
            for c in n.get("conditions") or []:
                for t in c.get("next_nodes") or []:
                    want[(n["id"], c.get("id"), t)] += 1
            for t in n.get("next_nodes") or []:
                want[(n["id"], "-", t)] += 1
        elif nt in ("BEGIN", "STAFF", "ACTION"):
            for t in n.get("next_nodes") or []:
                tn = N.get(t) or {}
                if tn.get("node_type") == "CONDITION" and tn.get("condition_type") in BRANCH_TYPES:
                    for tt in tn.get("next_nodes") or []:
                        want[(n["id"], t, tt)] += 1
                else:
                    want[(n["id"], "-", t)] += 1
    have = Counter()
    for i, e in enumerate(conns):
        s, t = e.get("source"), e.get("target")
        if s not in O or t not in O:
            emit("FAIL", "C7", f"dây {e.get('id')} nối node không có trong org_nodes ({s} → {t})", f"connections[{i}]")
            continue
        if e.get("sourceHandle") == "COLLECT_INFO" or (O.get(t) or {}).get("type") == "COLLECT_INFO":
            continue
        h = e.get("conditionId") or e.get("sourceHandle")
        have[(s, "-" if h in ("1", "2", None) else h, t)] += 1
    for (s, b, t), k in sorted((want - have).items()):
        emit("FAIL", "C7", f"thiếu dây {s} → {t} (nhánh {b}; có trong next_nodes, không có trong connections)")
    for (s, b, t), k in sorted((have - want).items()):
        emit("FAIL", "C7", f"dây thừa {s} → {t} (nhánh {b}; không có trong next_nodes)")
    if mode == "post":
        old = base_version
        if old is None and sent and isinstance(sent.get("version"), int) and not isinstance(sent.get("version"), bool):
            old = sent["version"]
        cur = doc.get("version")
        if "version" not in doc:
            emit("WARN", "C7", "bản GET không có 'version' — kiểm bằng list-by-tenant")
        elif not isinstance(cur, int) or isinstance(cur, bool):
            emit("FAIL", "C7", f"version bản GET không phải số nguyên: {cur!r}", "version")
        elif old is None:
            emit("WARN", "C7", f"chưa kiểm được version tăng (version GET = {cur}; không có version cũ — truyền --base hoặc "
                               "--base-version; kịch bản tạo mới thì bỏ qua)")
        elif cur <= old:
            emit("FAIL", "C7", f"version không tăng ({old} → {cur}) — có thể đã ghi đè từ bản cũ hoặc đang xem bản cũ", "version")
        else:
            emit("PASS", "C7", f"version tăng ({old} → {cur})")
        if "is_newest_version" in doc and doc.get("is_newest_version") is not True:
            emit("FAIL", "C7", "is_newest_version khác true — đang xem bản cũ")
        elif "is_newest_version" not in doc:
            emit("WARN", "C7", "bản GET không có 'is_newest_version'")
    if OUT.count("FAIL") == f0:
        emit("PASS", "C7", f"{sum(have.values())} dây khớp next_nodes")

    # X5 — so với payload đã gửi
    if sent is not None:
        f0 = OUT.count("FAIL")
        for k in ("nodes", "org_nodes", "connections"):
            a, b = len(sent.get(k) or []), len(doc.get(k) or [])
            if a != b:
                emit("FAIL", "X5", f"số {k}: gửi {a}, bản kiểm {b}")
        ta = Counter(n.get("node_type") for n in sent.get("nodes") or [])
        tb = Counter(n.get("node_type") for n in nodes)
        if ta != tb:
            emit("FAIL", "X5", f"số node theo loại lệch: gửi {dict(ta)}, bản kiểm {dict(tb)}")
        if OUT.count("FAIL") == f0:
            emit("PASS", "X5", f"khớp payload đã gửi: {len(nodes)} node, {len(org)} org, {len(conns)} dây")
    elif mode == "post":
        emit("WARN", "X5", "mode post không có --sent: chưa so số node/dây với payload đã gửi")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kiểm kịch bản Callbot NORMAL theo checklist C1..C7 (chỉ đọc).")
    ap.add_argument("saved")
    ap.add_argument("--sent")
    ap.add_argument("--context")
    ap.add_argument("--mode", choices=("pre", "post"), default="pre")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--base", help="bản GET đã dùng làm gốc khi sửa (lấy version cũ cho C7)")
    g.add_argument("--base-version", type=int, help="version cũ (bản mới nhất trước khi lưu) cho C7")
    a = ap.parse_args(argv)
    doc = load(a.saved, "bản kiểm")
    sent = load(a.sent, "payload đã gửi") if a.sent else None
    ctx = load(a.context, "context") if a.context else None
    if not isinstance(doc, dict):
        print("FAIL X0 file kiểm không phải object JSON")
        print("RESULT FAIL")
        return 1
    base_version = a.base_version
    if a.base:
        b = load(a.base, "bản gốc")
        bv = b.get("version") if isinstance(b, dict) else None
        if isinstance(bv, int) and not isinstance(bv, bool):
            base_version = bv
        else:
            emit("WARN", "C7", f"--base không có 'version' dạng số ({bv!r}) — chưa so được version", "version")
    try:
        check(doc, sent, ctx, a.mode, base_version)
    except (TypeError, AttributeError, KeyError, ValueError, IndexError) as e:
        # dữ liệu sai kiểu ở tầng sâu (next_nodes không phải chuỗi, action không phải object, id không băm được...)
        emit("FAIL", "X1", f"cấu trúc không hợp lệ: {type(e).__name__}: {str(e)[:150]}")
    ok = "FAIL" not in OUT
    print("RESULT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
