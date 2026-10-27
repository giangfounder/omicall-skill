# -*- coding: utf-8 -*-
"""Kiểm payload bot OmiBot (AI Chatbot) trước và sau khi lưu save_draft_v2. Chỉ đọc, không sửa file.

    python validate_bot.py <bot.json> [--mode pre|post] [--sent payload.json] [--context tenant_context.json]

<bot.json>: bot object (payload của GET) hoặc nguyên phản hồi GET {"payload": {...}}.
--mode pre  : kiểm payload sắp gửi (mặc định).
--mode post : kiểm bản GET lại sau khi lưu; kèm --sent <payload đã gửi> để so _id, is_draft, is_publish và trường đã sửa.

Mỗi dòng: `PASS|FAIL|WARN <mã> <mô tả> [json path]`; dòng cuối `RESULT PASS|FAIL`.
Mã C1..C7 = mục 1..7 "Validation checklist" trong references/api-reference.md; X<n> là mục bổ sung:
  X1 CUSTOM_INTENT có ở CẢ name_mappings (editor) lẫn ai_analyze.conditions (runtime) của BEGIN_CONTEXT, cùng id
  X2 2 điều kiện hệ thống bot_can_not_answer rồi customer_not_response nằm cuối name_mappings BEGIN_CONTEXT
  X3 api_knowledge_ids ⊆ api_knowledge[].ref_id; vector_store_ids ⊆ vector_store_files[].ref_id; ref_id là record _id, không phải file_id
  X4 (post) _id không đổi, is_draft:true, is_publish không đổi so với --sent
  X5 mọi next_node / next_nodes trỏ tới node có thật và có cạnh trong campaign.edges.connections
  X6 không in giá trị header ra output; FAIL khi bất kỳ chỗ nào trong payload còn giá trị đã che (`***`,
     `Bearer ***`, `"***"` trong chuỗi body JSON) — api_knowledge, actions[].data.headers, datas của editor...:
     lưu payload đó sẽ ghi đè token thật bằng `***`
  X7 (WARN) Trường hợp dùng ý định hệ thống (type INTENT) — quy ước chỉ dùng CUSTOM_INTENT
  X8 (WARN) Truy vấn có header Authorization tĩnh — token đổi từ apiKey hết hạn sau 24 giờ
  X9 tenant_id của bot khớp tenant_context (khi có --context)
Mức cảnh báo có chủ ý (WARN, không FAIL): C1 system_prompt rỗng, C4 history_config.enable khác true (bot vẫn chạy
được, cần người duyệt), C7 is_publish:true ở mode pre (payload sẽ giữ trạng thái xuất bản — chỉ khi user đã duyệt).
Exit: 0 khi không có FAIL (WARN vẫn cho qua), 1 khi có FAIL, 2 khi sai cách gọi.
"""
import argparse
import json
import re
import sys

SYSTEM_TAIL = ["bot_can_not_answer", "customer_not_response"]


class Report:
    def __init__(self):
        self.lines = []
        self.fail = False

    def add(self, level, code, msg, path=""):
        if level == "FAIL":
            self.fail = True
        self.lines.append(" ".join(x for x in (level, code, msg, path) if x))

    def ok(self, code, msg, path=""):
        self.add("PASS", code, msg, path)

    def bad(self, code, msg, path=""):
        self.add("FAIL", code, msg, path)

    def warn(self, code, msg, path=""):
        self.add("WARN", code, msg, path)


def load(path):
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and isinstance(obj.get("payload"), dict) and "campaign" not in obj:
        obj = obj["payload"]
    if not isinstance(obj, dict):
        raise ValueError("không phải JSON object bot")
    return obj


def campaign(bot):
    return bot.get("campaign") or {}


def find_begin(bot):
    """Tìm BEGIN_CONTEXT theo node_type/type, không theo vị trí [0]."""
    camp = campaign(bot)
    nodes = camp.get("nodes") or []
    maps = camp.get("name_mappings") or []
    ni = next((i for i, n in enumerate(nodes) if isinstance(n, dict) and n.get("node_type") == "BEGIN_CONTEXT"), None)
    mi = next((i for i, m in enumerate(maps) if isinstance(m, dict) and m.get("type") == "BEGIN_CONTEXT"), None)
    return ni, mi


def connections(bot):
    edges = campaign(bot).get("edges") or {}
    return edges.get("connections") or [] if isinstance(edges, dict) else []


def check_c1(r, bot, sent):
    sp = bot.get("system_prompt")
    if not isinstance(sp, str):
        r.bad("C1", "system_prompt không phải chuỗi", "$.system_prompt")
    elif sent is not None:
        if sp == sent.get("system_prompt"):
            r.ok("C1", "system_prompt khớp bản đã gửi", "$.system_prompt")
        else:
            r.bad("C1", "system_prompt khác bản đã gửi", "$.system_prompt")
    elif not sp.strip():
        r.warn("C1", "system_prompt rỗng", "$.system_prompt")
    else:
        r.ok("C1", "system_prompt có nội dung (%d ký tự)" % len(sp), "$.system_prompt")


def check_c2(r, bot, mode):
    if not bot.get("_id"):
        r.bad("C2", "thiếu _id (bot tạo trên UI trước, save_draft_v2 giữ nguyên _id)", "$._id")
    else:
        r.ok("C2", "có _id", "$._id")
    if bot.get("is_draft") is True:
        r.ok("C2", "is_draft:true", "$.is_draft")
    elif mode == "post":
        r.bad("C2", "is_draft khác true sau khi lưu nháp", "$.is_draft")
    else:
        r.warn("C2", "is_draft khác true trong payload gửi (save_draft_v2 sẽ đặt lại — GET kiểm)", "$.is_draft")


def check_intents(r, bot):
    """C3 + X1 + X2 + X7."""
    ni, mi = find_begin(bot)
    camp = campaign(bot)
    if ni is None or mi is None:
        r.bad("C3", "không thấy BEGIN_CONTEXT ở %s" % ("campaign.nodes" if ni is None else "campaign.name_mappings"),
              "$.campaign")
        return
    node = camp["nodes"][ni]
    nm = camp["name_mappings"][mi]
    npath = "$.campaign.nodes[%d].ai_analyze.conditions" % ni
    mpath = "$.campaign.name_mappings[%d].conditions" % mi
    rt = [c for c in ((node.get("ai_analyze") or {}).get("conditions") or []) if isinstance(c, dict)]
    ed = [c for c in (nm.get("conditions") or []) if isinstance(c, dict)]
    rt_ids = [c.get("id") for c in rt if c.get("type") == "CUSTOM_INTENT"]
    ed_ids = [c.get("id") for c in ed if c.get("type") == "CUSTOM_INTENT"]
    only_ed = [i for i in ed_ids if i not in rt_ids]
    only_rt = [i for i in rt_ids if i not in ed_ids]
    if only_ed or only_rt:
        if only_ed:
            r.bad("X1", "CUSTOM_INTENT chỉ có ở name_mappings, thiếu runtime: %s" % ", ".join(map(str, only_ed)), npath)
        if only_rt:
            r.bad("X1", "CUSTOM_INTENT chỉ có ở runtime, thiếu name_mappings: %s" % ", ".join(map(str, only_rt)), mpath)
    else:
        r.ok("X1", "%d CUSTOM_INTENT khớp id ở cả editor và runtime" % len(ed_ids), mpath)
    for c in ed + rt:
        if c.get("type") == "INTENT":
            r.warn("X7", "Trường hợp dùng ý định hệ thống (INTENT) — quy ước dùng CUSTOM_INTENT mô tả tự nhiên", mpath)
            break
    types = [c.get("type") for c in ed]
    tail_ok = types[-2:] == SYSTEM_TAIL and all(t not in SYSTEM_TAIL for t in types[:-2])
    if tail_ok:
        r.ok("X2", "2 điều kiện hệ thống nằm cuối", mpath)
    else:
        r.bad("X2", "name_mappings BEGIN_CONTEXT phải kết thúc bằng bot_can_not_answer rồi customer_not_response "
                    "(hiện: %s)" % ", ".join(str(t) for t in types[-3:]), mpath)
    if (only_ed or only_rt) or not tail_ok:
        r.bad("C3", "ý định chưa đủ ở 2 nơi hoặc sai thứ tự điều kiện hệ thống", mpath)
    else:
        r.ok("C3", "ý định đủ ở 2 nơi, 2 hệ thống cuối", mpath)


def check_c4_c5(r, bot, sent):
    hc = bot.get("history_config")
    if sent is not None:
        for k in ("history_config", "max_characters_reply", "mode_reply"):
            if bot.get(k) != sent.get(k):
                r.bad("C4", "%s khác bản đã gửi" % k, "$." + k)
                break
        else:
            r.ok("C4", "history_config, max_characters_reply, mode_reply khớp bản đã gửi", "$.history_config")
    elif not isinstance(hc, dict):
        r.warn("C4", "history_config không phải object", "$.history_config")
    elif hc.get("enable") is not True:
        r.warn("C4", "history_config.enable khác true — bot có thể quên lượt trước", "$.history_config.enable")
    else:
        r.ok("C4", "history_config.enable:true", "$.history_config.enable")
    name = bot.get("assistant_name")
    if not isinstance(name, str) or not name.strip():
        r.bad("C5", "assistant_name rỗng", "$.assistant_name")
    elif sent is not None and (name != sent.get("assistant_name")
                               or bot.get("assistant_description") != sent.get("assistant_description")):
        r.bad("C5", "assistant_name/assistant_description khác bản đã gửi", "$.assistant_name")
    else:
        r.ok("C5", "assistant_name có giá trị", "$.assistant_name")


def check_rag(r, bot, mode):
    """C6 + X3."""
    ni, _ = find_begin(bot)
    aa = {}
    if ni is not None:
        aa = campaign(bot)["nodes"][ni].get("ai_analyze") or {}
    base = "$.campaign.nodes[%s].ai_analyze" % ni
    vs = bot.get("vector_store") or {}
    files = [f for f in (vs.get("vector_store_files") or []) if isinstance(f, dict)] if isinstance(vs, dict) else []
    vs_ids = aa.get("vector_store_ids") or []
    refs = [f.get("ref_id") for f in files]
    bad_ref = [f.get("ref_id") for f in files
               if not f.get("ref_id") or f.get("ref_id") == f.get("file_id") or str(f.get("ref_id")).startswith("file-")]
    if bad_ref:
        r.bad("X3", "ref_id phải là record _id của other/add, không phải file_id", "$.vector_store.vector_store_files")
    missing = [i for i in vs_ids if i not in refs]
    if missing:
        r.bad("X3", "vector_store_ids không có trong vector_store_files[].ref_id: %s" % ", ".join(map(str, missing)),
              base + ".vector_store_ids")
    elif vs_ids:
        r.ok("X3", "vector_store_ids ⊆ vector_store_files[].ref_id", base + ".vector_store_ids")
    ak_refs = [a.get("ref_id") for a in (bot.get("api_knowledge") or []) if isinstance(a, dict)]
    ak_ids = aa.get("api_knowledge_ids") or []
    miss_ak = [i for i in ak_ids if i not in ak_refs]
    if miss_ak:
        r.bad("X3", "api_knowledge_ids không có trong api_knowledge[].ref_id: %s" % ", ".join(map(str, miss_ak)),
              base + ".api_knowledge_ids")
    else:
        r.ok("X3", "api_knowledge_ids ⊆ api_knowledge[].ref_id (%d)" % len(ak_ids), base + ".api_knowledge_ids")
    if not vs_ids and not files and not bot.get("question_answer"):
        r.ok("C6", "không dùng RAG (vector_store/question_answer rỗng)", "$.vector_store")
        return
    pending = [f.get("ref_id") for f in files if f.get("file_training_status") != "completed"]
    if pending:
        lvl = r.warn
        lvl("C6", "file chưa train xong (file_training_status khác completed): %s" % ", ".join(map(str, pending)),
            "$.vector_store.vector_store_files")
    elif files:
        r.ok("C6", "%d file RAG, file_training_status completed" % len(files), "$.vector_store.vector_store_files")
    else:
        r.warn("C6", "có vector_store_ids nhưng vector_store rỗng", "$.vector_store")


def check_publish(r, bot, sent, mode):
    """C7 + X4."""
    if sent is None:
        if mode == "pre" and bot.get("is_publish") is True:
            r.warn("C7", "is_publish:true trong payload sắp gửi — chỉ giữ khi user đã duyệt xuất bản rõ ràng; "
                         "lưu nháp không tự xuất bản", "$.is_publish")
        else:
            r.ok("C7", "is_publish=%s (không đổi trừ khi user yêu cầu xuất bản)" % json.dumps(bot.get("is_publish")),
                 "$.is_publish")
        if mode == "post":
            r.warn("X4", "mode post không có --sent → không so được _id/is_publish", "$")
        return
    if bot.get("is_publish") != sent.get("is_publish"):
        r.bad("C7", "is_publish đổi so với bản đã gửi", "$.is_publish")
    else:
        r.ok("C7", "is_publish giữ nguyên", "$.is_publish")
    if mode != "post":
        return
    errs = []
    if bot.get("_id") != sent.get("_id"):
        errs.append("_id đổi")
    if bot.get("is_draft") is not True:
        errs.append("is_draft khác true")
    if bot.get("is_publish") != sent.get("is_publish"):
        errs.append("is_publish đổi")
    if errs:
        r.bad("X4", "; ".join(errs), "$")
    else:
        r.ok("X4", "_id giữ nguyên, is_draft:true, is_publish không đổi", "$")


def node_targets(node):
    out = []
    for t in node.get("next_nodes") or []:
        out.append(("next_nodes", t))
    aa = node.get("ai_analyze") or {}
    for i, c in enumerate(aa.get("conditions") or []):
        if isinstance(c, dict) and c.get("next_node"):
            out.append(("ai_analyze.conditions[%d].next_node" % i, c["next_node"]))
    for k in ("bot_can_not_answer", "customer_not_response"):
        v = aa.get(k)
        if isinstance(v, dict) and v.get("next_node"):
            out.append(("ai_analyze.%s.next_node" % k, v["next_node"]))
    return out


def check_edges(r, bot):
    """X5."""
    nodes = [n for n in (campaign(bot).get("nodes") or []) if isinstance(n, dict)]
    ids = {n.get("id") for n in nodes}
    conns = [c for c in connections(bot) if isinstance(c, dict)]
    has_st = all("source" in c and "target" in c for c in conns)
    pairs = {(c.get("source"), c.get("target")) for c in conns}
    targets = {c.get("target") for c in conns}
    problems = 0
    for i, n in enumerate(nodes):
        for where, t in node_targets(n):
            path = "$.campaign.nodes[%d].%s" % (i, where)
            if t not in ids:
                r.bad("X5", "trỏ tới node không tồn tại: %s" % t, path)
                problems += 1
            elif has_st and (n.get("id"), t) not in pairs:
                r.bad("X5", "thiếu cạnh %s → %s trong campaign.edges.connections" % (n.get("id"), t), path)
                problems += 1
            elif not has_st and t not in targets:
                r.bad("X5", "không có cạnh nào tới %s" % t, path)
                problems += 1
    for i, c in enumerate(conns):
        for k in ("source", "target"):
            if k in c and c[k] not in ids:
                r.bad("X5", "cạnh trỏ tới node không tồn tại: %s" % c[k], "$.campaign.edges.connections[%d].%s" % (i, k))
                problems += 1
    if conns and not has_st:
        r.warn("X5", "cạnh thiếu source/target — chỉ so được theo target", "$.campaign.edges.connections")
    if not problems:
        r.ok("X5", "mọi next_node/next_nodes có node đích và có cạnh (%d cạnh)" % len(conns), "$.campaign")


# '***' đứng riêng (giữa khoảng trắng, trong đường dẫn URL '/***/', sau '?', trước ',') cũng bị bắt: mask_text che JWT
# nằm trong câu hay trong URL thành '***' trần. Markdown ***chữ*** không bị bắt (cùng mẫu với omi_save.MASK_RE).
MASK_RE = re.compile(r'^\s*(?:bearer\s+)?\*\*\*\s*$|bearer\s+\*\*\*|"\*\*\*"|\\"\*\*\*\\"|[=:]\s*\*\*\*(?![*\w])'
                     r'|(?<![*\w])\*\*\*(?![*\w])', re.I)


def is_masked(v):
    """Giá trị đã bị mask_secrets che: '***', 'Bearer ***', hoặc chuỗi JSON chứa "***". Không bắt markdown ***chữ***."""
    return isinstance(v, str) and bool(MASK_RE.search(v))


def walk_masked(obj, path, out, counter):
    """Duyệt toàn payload: mọi chuỗi đã che và mọi danh sách header {key, value} (đếm, không in giá trị)."""
    if isinstance(obj, dict):
        if "key" in obj and "value" in obj:
            counter[0] += 1
        for k, v in obj.items():
            walk_masked(v, "%s.%s" % (path, k), out, counter)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_masked(v, "%s[%d]" % (path, i), out, counter)
    elif is_masked(obj):
        out.append(path)


def check_secrets(r, bot):
    """X6 + X8. Không bao giờ in giá trị header."""
    static = []
    for i, a in enumerate(bot.get("api_knowledge") or []):
        for h in (a or {}).get("headers") or []:
            if isinstance(h, dict) and str(h.get("key", "")).lower() == "authorization" and h.get("value"):
                if not is_masked(str(h.get("value"))):
                    static.append("$.api_knowledge[%d].headers" % i)
    masked = []
    counter = [0]
    walk_masked(bot, "$", masked, counter)
    r.ok("X6", "không in giá trị header (%d cặp key/value được bỏ qua)" % counter[0], "$")
    for p in masked:
        r.bad("X6", "giá trị đang là bản đã che (***) — lưu sẽ ghi đè bí mật thật; "
                    "dùng bản GET chưa che làm base", p)
    for p in static:
        r.warn("X8", "Truy vấn có header Authorization tĩnh — token đổi từ apiKey hết hạn sau 24 giờ "
                     "(Cần xác nhận cách làm mới, hoặc đi Hướng B qua OMIFlow)", p)


def check_context(r, bot, ctx_path):
    try:
        with open(ctx_path, encoding="utf-8") as f:
            ctx = json.load(f)
    except (OSError, ValueError) as e:
        r.warn("X9", "không đọc được tenant_context: %s" % type(e).__name__, "")
        return
    tid = ((ctx.get("tenant") or {}).get("tenant_id") or "") if isinstance(ctx, dict) else ""
    if not tid or tid.startswith("<"):
        r.warn("X9", "tenant_context chưa có tenant_id thật — bỏ qua so khớp", "$.tenant_id")
    elif bot.get("tenant_id") and bot.get("tenant_id") != tid:
        r.bad("X9", "tenant_id của bot khác tenant_context", "$.tenant_id")
    else:
        r.ok("X9", "tenant_id khớp tenant_context", "$.tenant_id")


def validate(bot, mode="pre", sent=None, context=None):
    r = Report()
    check_c1(r, bot, sent)
    check_c2(r, bot, mode)
    check_intents(r, bot)
    check_c4_c5(r, bot, sent)
    check_rag(r, bot, mode)
    check_publish(r, bot, sent, mode)
    check_edges(r, bot)
    check_secrets(r, bot)
    if context:
        check_context(r, bot, context)
    return r


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Kiểm payload bot OmiBot theo checklist api-reference.md (chỉ đọc).")
    ap.add_argument("file")
    ap.add_argument("--sent", help="payload đã gửi (dùng với --mode post)")
    ap.add_argument("--mode", choices=["pre", "post"], default="pre")
    ap.add_argument("--context", help="tenant_context.json")
    a = ap.parse_args(argv)
    try:
        bot = load(a.file)
        sent = load(a.sent) if a.sent else None
    except (OSError, ValueError) as e:
        print("FAIL X0 không đọc được JSON: %s" % e)
        print("RESULT FAIL")
        return 2
    r = validate(bot, a.mode, sent, a.context)
    for line in r.lines:
        print(line)
    print("RESULT %s" % ("FAIL" if r.fail else "PASS"))
    return 1 if r.fail else 0


if __name__ == "__main__":
    sys.exit(main())
