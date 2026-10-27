# -*- coding: utf-8 -*-
"""Kiểm payload hoặc bản GET của kịch bản Callbot SmartAgent (AI_AGENT). Chỉ đọc, không sửa file.

Lệnh:
  python validate_smartagent.py <file.json> [--sent payload.json] [--mode pre|post] [--context tenant_context.json]

Mỗi dòng output: `PASS|FAIL|WARN <mã> <mô tả> [json path]`. Dòng cuối `RESULT PASS|FAIL`.
Exit 0 khi không có FAIL (WARN vẫn cho qua), 1 khi có FAIL, 2 khi sai cách gọi hoặc không đọc được file.

Mã C1..C11 = checklist trong references/api-reference.md (mục "Validation checklist").
Mã X<n> = mục bổ sung:
  X1  không có next_node trỏ về BEGIN (bất biến không cạnh ngược)
  X2  bot_can_not_answer khớp 3 chỗ: condition, ai_analyze.bot_can_not_answer, connection → TRANSFER_CALL
  X3  TRANSFER_CALL có data.ids khác rỗng và khác [""]
  X4  ADD_CLASSIFY runtime dùng `data`, editor dùng `datas`, khớp classifies top-level
  X5  mọi next_node có node đích và có connection; connection có source/target tồn tại
      (không kiểm định dạng id cạnh: tài liệu còn "Cần xác nhận")
  X6  chỉ intent Hoàn tất đi tới END_CALL
  X7  END_CALL mô tả trình tự kết thúc (cảm ơn ... tạm biệt) — WARN
  X8  không còn placeholder dạng <...>
  X9  lời thoại cho giọng đọc (tts_lint.py)
  X10 mode post có --sent: bản GET giữ đủ node, intent, connection, knowledge.apis (ref_id) và knowledge.files đã gửi;
      mode post thiếu --sent → WARN X10 bỏ qua
  X11 có --context: nhân viên ở TRANSFER_CALL có trong tenant_context.agents — WARN
  X12 (build_smartagent.py --update in ra, không phải validator) knowledge.apis/files bản gửi ít hơn base — WARN
C6 kiểm: không connection/next_node về BEGIN, không connection đi ra từ END_CALL. Phần "node cuối của nhánh không
terminal không có connection đi ra" với node ACTION thì validator không biết nhánh nào là cuối → agent tự kiểm theo thiết kế.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_lint  # noqa: E402

PLACEHOLDER_RE = re.compile(r"<[A-Za-z_À-ỹ][^<>\n]{0,60}>")
SYSTEM_IDS = ("bot_can_not_answer", "customer_not_response")


class Report:
    def __init__(self):
        self.lines = []
        self.fail = 0

    def add(self, level, code, msg, path=""):
        if level == "FAIL":
            self.fail += 1
        self.lines.append("%s %s %s%s" % (level, code, msg, (" [%s]" % path) if path else ""))

    def ok(self, code, msg):
        self.add("PASS", code, msg)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and "nodes" not in obj and isinstance(obj.get("payload"), dict):
        obj = obj["payload"]
    return obj


def walk_strings(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            for x in walk_strings(v, "%s.%s" % (path, k)):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in walk_strings(v, "%s[%d]" % (path, i)):
                yield x
    elif isinstance(obj, str):
        yield path, obj


def lower(s):
    return (s or "").lower() if isinstance(s, str) else ""


class Script:
    def __init__(self, s):
        self.s = s
        self.nodes = [n for n in (s.get("nodes") or []) if isinstance(n, dict)]
        self.org = [n for n in (s.get("org_nodes") or []) if isinstance(n, dict)]
        self.conns = [c for c in (s.get("connections") or []) if isinstance(c, dict)]
        self.node_by_id = {n.get("id"): n for n in self.nodes}
        self.org_by_id = {n.get("id"): n for n in self.org}
        self.begin = next((n for n in self.nodes if n.get("node_type") == "BEGIN"), None)
        self.begin_id = self.begin.get("id") if self.begin else None
        self.begin_idx = self.nodes.index(self.begin) if self.begin else -1
        ob = self.org_by_id.get(self.begin_id)
        if ob is None:
            ob = next((o for o in self.org if (o.get("data") or {}).get("type") == "BEGIN" or o.get("type") == "BEGIN"), None)
        self.org_begin = ob
        self.org_begin_idx = self.org.index(ob) if ob is not None else -1
        cfg = (self.begin or {}).get("ai_agent_config") or {}
        self.analyze = cfg.get("ai_analyze") or {}
        self.rt_conds = [c for c in (self.analyze.get("conditions") or []) if isinstance(c, dict)]
        self.ed_conds = [c for c in (((ob or {}).get("data") or {}).get("conditions") or []) if isinstance(c, dict)]
        self.rt_intents = [c for c in self.rt_conds if c.get("type") == "CUSTOM_INTENT"]
        self.ed_intents = [c for c in self.ed_conds if c.get("type") == "CUSTOM_INTENT"]

    def rt_cond_path(self, j):
        return "nodes[%d].ai_agent_config.ai_analyze.conditions[%d]" % (self.begin_idx, j)

    def ed_cond_path(self, j):
        return "org_nodes[%d].data.conditions[%d]" % (self.org_begin_idx, j)

    def actions_of(self, node, typ):
        return [a for a in (node.get("actions") or []) if isinstance(a, dict) and a.get("type") == typ]

    def org_actions_of(self, org, typ):
        return [a for a in (((org or {}).get("data") or {}).get("actions") or []) if isinstance(a, dict) and a.get("type") == typ]

    def out_edges(self, node_id):
        return [c for c in self.conns if c.get("source") == node_id]

    def reachable(self, start):
        seen, stack = set(), [start]
        while stack:
            x = stack.pop()
            if x in seen or x is None:
                continue
            seen.add(x)
            for c in self.out_edges(x):
                if c.get("source") != self.begin_id:
                    stack.append(c.get("target"))
        return seen


def check(sc, mode, sent=None, context=None):
    r = Report()
    s = sc.s
    if sc.begin is None:
        r.add("FAIL", "C1", "không có node BEGIN trong nodes", "nodes")
        return r
    if sc.org_begin is None:
        r.add("FAIL", "C2", "không có BEGIN trong org_nodes", "org_nodes")

    # C1
    c1 = True
    for j, c in sorted(((sc.rt_conds.index(c), c) for c in sc.rt_intents)):
        data = c.get("data") or []
        if not data:
            r.add("FAIL", "C1", "intent '%s' không có data[]" % c.get("name"), sc.rt_cond_path(j) + ".data")
            c1 = False
        for k, d in enumerate(data):
            if not isinstance(d, dict) or d.get("type") != "OMI_BOT_INTENT":
                r.add("FAIL", "C1", "runtime intent '%s' data[].type khác OMI_BOT_INTENT" % c.get("name"), "%s.data[%d].type" % (sc.rt_cond_path(j), k))
                c1 = False
    if len(sc.rt_intents) < 5:
        r.add("WARN", "C1", "chỉ có %d CUSTOM_INTENT; quy ước tối thiểu 5 intent (Cần xác nhận theo nghiệp vụ)" % len(sc.rt_intents), "nodes[%d].ai_agent_config.ai_analyze.conditions" % sc.begin_idx)
    if c1:
        r.ok("C1", "%d CUSTOM_INTENT, data[].type đều là OMI_BOT_INTENT" % len(sc.rt_intents))

    # C2
    if sc.org_begin is not None:
        rt_ids = [c.get("id") for c in sc.rt_intents]
        ed_ids = [c.get("id") for c in sc.ed_intents]
        c2 = True
        if rt_ids != ed_ids:
            r.add("FAIL", "C2", "intent ids runtime %s khác editor %s (phải cùng id, cùng thứ tự)" % (rt_ids, ed_ids), "org_nodes[%d].data.conditions" % sc.org_begin_idx)
            c2 = False
        for name, conds, pathf in (("runtime", sc.rt_conds, sc.rt_cond_path), ("editor", sc.ed_conds, sc.ed_cond_path)):
            types = [c.get("type") for c in conds]
            tail = types[-2:]
            if sorted(tail) != sorted(SYSTEM_IDS) or any(t in SYSTEM_IDS for t in types[:-2]):
                r.add("FAIL", "C2", "%s: 2 điều kiện hệ thống (bot_can_not_answer, customer_not_response) phải nằm CUỐI, sau mọi CUSTOM_INTENT; thứ tự hiện tại %s" % (name, types), pathf(max(0, len(conds) - 1)))
                c2 = False
        if c2:
            r.ok("C2", "intent runtime và editor cùng id, cùng thứ tự; 2 hệ thống ở cuối")

    # C3
    c3 = True
    for c in sc.ed_intents:
        j = sc.ed_conds.index(c)
        for k, d in enumerate(c.get("data") or []):
            if not isinstance(d, dict) or d.get("isCustomComp") is not True or d.get("targetType") != "OMI_BOT_INTENT":
                r.add("FAIL", "C3", "editor intent '%s' thiếu isCustomComp:true hoặc targetType OMI_BOT_INTENT (editor hiện ô trống)" % c.get("name"), "%s.data[%d]" % (sc.ed_cond_path(j), k))
                c3 = False
    if c3:
        r.ok("C3", "editor intent đủ isCustomComp và targetType")

    # C4
    c4 = True
    for c in sc.rt_intents:
        j = sc.rt_conds.index(c)
        for k, d in enumerate(c.get("data") or []):
            if not isinstance(d, dict) or not (d.get("content") or "").strip():
                r.add("FAIL", "C4", "runtime intent '%s' data[].content rỗng" % c.get("name"), "%s.data[%d].content" % (sc.rt_cond_path(j), k))
                c4 = False
    if c4:
        r.ok("C4", "runtime intent đều có content")

    # C5
    c5 = True
    for c in sc.rt_intents:
        nn = c.get("next_node")
        if not nn:
            if any(e.get("source") == sc.begin_id and e.get("sourceHandle") == c.get("id") for e in sc.conns):
                r.add("FAIL", "C5", "intent '%s' next_node null nhưng có connection đi ra" % c.get("name"), sc.rt_cond_path(sc.rt_conds.index(c)) + ".next_node")
                c5 = False
            continue
        edges = [e for e in sc.conns if e.get("source") == sc.begin_id and e.get("sourceHandle") == c.get("id")]
        if not any(e.get("target") == nn and str(e.get("targetHandle")) == "1" for e in edges):
            r.add("FAIL", "C5", "intent '%s' next_node=%s nhưng không có connection begin→%s (sourceHandle=%s, targetHandle \"1\")" % (c.get("name"), nn, nn, c.get("id")), sc.rt_cond_path(sc.rt_conds.index(c)) + ".next_node")
            c5 = False
        elif any(e.get("target") != nn for e in edges):
            r.add("FAIL", "C5", "intent '%s' có connection tới node khác next_node" % c.get("name"), "connections")
            c5 = False
    if c5:
        r.ok("C5", "intent chuyển/cúp có next_node và connection khớp")

    # C6 + X1
    back = [i for i, e in enumerate(sc.conns) if e.get("target") == sc.begin_id]
    for i in back:
        r.add("FAIL", "C6", "connection trỏ ngược về BEGIN (%s → %s)" % (sc.conns[i].get("source"), sc.begin_id), "connections[%d].target" % i)
    end_out = [i for i, e in enumerate(sc.conns) if (sc.node_by_id.get(e.get("source")) or {}).get("node_type") == "END_CALL"]
    for i in end_out:
        r.add("FAIL", "C6", "END_CALL %s là node cuối nhưng có connection đi ra (→ %s)" % (sc.conns[i].get("source"), sc.conns[i].get("target")), "connections[%d].source" % i)
    if not back and not end_out:
        r.ok("C6", "không có connection nào trỏ về BEGIN hay đi ra từ END_CALL")
    x1 = not back
    for i in back:
        r.add("FAIL", "X1", "cấm cạnh ngược về BEGIN (connection từ %s)" % sc.conns[i].get("source"), "connections[%d]" % i)
    for j, c in enumerate(sc.rt_conds):
        if sc.begin_id and c.get("next_node") == sc.begin_id:
            r.add("FAIL", "X1", "condition '%s' có next_node = BEGIN" % (c.get("name") or c.get("id")), sc.rt_cond_path(j) + ".next_node")
            x1 = False
    for key in ("bot_can_not_answer", "customer_not_response", "customer_response_wrong", "customer_has_response"):
        v = sc.analyze.get(key)
        if isinstance(v, dict) and sc.begin_id and v.get("next_node") == sc.begin_id:
            r.add("FAIL", "X1", "ai_analyze.%s.next_node = BEGIN" % key, "nodes[%d].ai_agent_config.ai_analyze.%s.next_node" % (sc.begin_idx, key))
            x1 = False
    if x1:
        r.ok("X1", "không có connection hay next_node nào trỏ về BEGIN")

    # C7
    if sc.org_begin is not None:
        co = ((sc.org_begin.get("data") or {}).get("collapseObj")) or {}
        miss = [c.get("id") for c in sc.ed_intents if c.get("id") not in co]
        if miss:
            r.add("FAIL", "C7", "collapseObj BEGIN thiếu entry cho intent %s" % miss, "org_nodes[%d].data.collapseObj" % sc.org_begin_idx)
        else:
            r.ok("C7", "collapseObj có entry cho mọi intent")

    # C8
    c8 = True
    ed_by_id = {c.get("id"): c for c in sc.ed_intents}
    for c in sc.rt_intents:
        rt_vars = []
        for st in c.get("action_steps") or []:
            if isinstance(st, dict) and st.get("action") == "collect_variables":
                rt_vars += list(st.get("variables_code") or [])
        ed = ed_by_id.get(c.get("id")) or {}
        ed_vars = []
        for st in ed.get("actionStep") or []:
            if isinstance(st, dict) and st.get("action") == "collect_variables":
                ed_vars += [v.get("value") or v.get("id") for v in (st.get("variablesCode") or []) if isinstance(v, dict)]
        if sorted(rt_vars) != sorted(ed_vars):
            r.add("FAIL", "C8", "intent '%s' thu biến runtime %s khác editor %s" % (c.get("name"), rt_vars, ed_vars), sc.rt_cond_path(sc.rt_conds.index(c)) + ".action_steps")
            c8 = False
            continue
        nn = c.get("next_node")
        if rt_vars and nn in sc.node_by_id and sc.node_by_id[nn].get("node_type") == "ACTION":
            n_vars = [v.get("field_code") for v in (sc.node_by_id[nn].get("variables") or []) if isinstance(v, dict)]
            o_vars = [v.get("variable") for v in (((sc.org_by_id.get(nn) or {}).get("data") or {}).get("variables") or []) if isinstance(v, dict)]
            lack = [v for v in rt_vars if v not in n_vars or v not in o_vars]
            if lack:
                r.add("FAIL", "C8", "node %s được nối từ intent thu biến nhưng variables (runtime/org) thiếu %s" % (nn, lack), "nodes[id=%s].variables" % nn)
                c8 = False
    if c8:
        r.ok("C8", "action_steps runtime và actionStep editor khớp")

    # C9 + X4
    top = [x.get("name") for x in (s.get("classifies") or []) if isinstance(x, dict)]
    c9 = x4 = True
    any_clf = False
    for i, n in enumerate(sc.nodes):
        for a in sc.actions_of(n, "ADD_CLASSIFY"):
            any_clf = True
            org = sc.org_by_id.get(n.get("id"))
            oacts = sc.org_actions_of(org, "ADD_CLASSIFY")
            rt_data = a.get("data")
            if not isinstance(rt_data, dict) or "datas" in a:
                r.add("FAIL", "X4", "ADD_CLASSIFY runtime phải dùng khoá `data` (không `datas`)", "nodes[%d].actions" % i)
                x4 = False
            if not oacts:
                r.add("FAIL", "X4", "node %s thiếu action ADD_CLASSIFY trong org_nodes" % n.get("id"), "org_nodes[id=%s]" % n.get("id"))
                x4 = False
                continue
            oa = oacts[0]
            if not isinstance(oa.get("datas"), dict) or "data" in oa:
                r.add("FAIL", "X4", "ADD_CLASSIFY editor phải dùng khoá `datas` (không `data`)", "org_nodes[id=%s].data.actions" % n.get("id"))
                x4 = False
            rc = [x.get("name") for x in ((rt_data or {}).get("classifies") or []) if isinstance(x, dict)] if isinstance(rt_data, dict) else []
            ec = [x.get("name") for x in ((oa.get("datas") or {}).get("classifies") or []) if isinstance(x, dict)] if isinstance(oa.get("datas"), dict) else []
            if rc != ec or not rc:
                r.add("FAIL", "C9", "node %s classifies runtime %s khác editor %s" % (n.get("id"), rc, ec), "nodes[%d].actions" % i)
                c9 = False
            lack = [x for x in set(rc + ec) if x not in top]
            if lack:
                r.add("FAIL", "C9", "classifies top-level thiếu nhãn %s" % lack, "classifies")
                c9 = False
    if any_clf:
        if c9:
            r.ok("C9", "ADD_CLASSIFY runtime/editor khớp, top-level đủ nhãn")
        if x4:
            r.ok("X4", "ADD_CLASSIFY dùng đúng data (runtime) / datas (editor)")

    # C10 + X7
    for i, n in enumerate(sc.nodes):
        if n.get("node_type") != "END_CALL":
            continue
        od = ((sc.org_by_id.get(n.get("id")) or {}).get("data")) or {}
        desc = (n.get("description") or "").strip()
        if not desc:
            r.add("FAIL", "C10", "END_CALL %s thiếu description runtime (cách kết thúc)" % n.get("id"), "nodes[%d].description" % i)
        elif not ((od.get("description") or "").strip() or (od.get("content") or "").strip()):
            r.add("FAIL", "C10", "END_CALL %s thiếu data.description/data.content ở org_nodes" % n.get("id"), "org_nodes[id=%s].data" % n.get("id"))
        else:
            r.ok("C10", "END_CALL %s có description runtime và editor" % n.get("id"))
            low = lower(desc)
            if "cảm ơn" not in low or "tạm biệt" not in low:
                r.add("WARN", "X7", "END_CALL %s description nên nêu trình tự cảm ơn → chúc → xin phép kết thúc → tạm biệt" % n.get("id"), "nodes[%d].description" % i)

    # C11
    if mode == "post":
        if s.get("is_newest_version") is not True:
            r.add("WARN", "C11", "is_newest_version khác true", "is_newest_version")
        if s.get("is_publish") is not True:
            r.add("WARN", "C11", "is_publish khác true (Cần xác nhận ngữ nghĩa is_publish: server có thể trả true dù gửi false)", "is_publish")
        if sent is not None and isinstance(sent.get("version"), int) and isinstance(s.get("version"), int) and s["version"] <= sent["version"]:
            r.add("WARN", "C11", "version %s chưa tăng so với bản gửi %s" % (s.get("version"), sent.get("version")), "version")
        r.add("WARN", "C11", "is_publish chỉ để tham khảo, Cần xác nhận ngữ nghĩa; không dùng để biết đã xuất bản", "is_publish")

    # X2
    cond = next((c for c in sc.rt_conds if c.get("id") == "bot_can_not_answer"), None)
    bca = sc.analyze.get("bot_can_not_answer") if isinstance(sc.analyze.get("bot_can_not_answer"), dict) else {}
    t1 = (cond or {}).get("next_node")
    t2 = bca.get("next_node")
    edge_t = [e.get("target") for e in sc.conns if e.get("source") == sc.begin_id and e.get("sourceHandle") == "bot_can_not_answer"]
    if not t1 or not t2 or not edge_t:
        r.add("FAIL", "X2", "bot_can_not_answer phải nối TRANSFER_CALL ở cả condition.next_node (%s), ai_analyze.bot_can_not_answer.next_node (%s) và connection (%s)" % (t1, t2, edge_t), "nodes[%d].ai_agent_config.ai_analyze.bot_can_not_answer" % sc.begin_idx)
    elif not (t1 == t2 and edge_t == [t1]):
        r.add("FAIL", "X2", "bot_can_not_answer lệch: condition=%s, ai_analyze=%s, connection=%s" % (t1, t2, edge_t), "nodes[%d].ai_agent_config.ai_analyze.bot_can_not_answer.next_node" % sc.begin_idx)
    elif not sc.actions_of(sc.node_by_id.get(t1) or {}, "TRANSFER_CALL"):
        r.add("FAIL", "X2", "bot_can_not_answer trỏ tới %s không phải node TRANSFER_CALL" % t1, "connections")
    else:
        r.ok("X2", "bot_can_not_answer → %s khớp 3 chỗ" % t1)

    # X3 + X11
    agent_ids = None
    if context:
        agent_ids = set()
        for a in context.get("agents") or []:
            if isinstance(a, dict):
                for k in ("_id", "agent_id", "contact_id", "id"):
                    if a.get(k):
                        agent_ids.add(str(a[k]))
    for i, n in enumerate(sc.nodes):
        for a in sc.actions_of(n, "TRANSFER_CALL"):
            ids = ((a.get("data") or {}).get("ids")) or []
            if not ids or any(not str(x).strip() for x in ids):
                r.add("FAIL", "X3", "TRANSFER_CALL %s có data.ids rỗng hoặc [\"\"] (editor có thể đã ghi mất nhân viên)" % n.get("id"), "nodes[%d].actions[0].data.ids" % i)
            else:
                r.ok("X3", "TRANSFER_CALL %s có nhân viên" % n.get("id"))
                if agent_ids is not None:
                    lack = [x for x in ids if str(x) not in agent_ids]
                    if lack:
                        r.add("WARN", "X11", "nhân viên %s không có trong tenant_context.agents (Cần xác nhận)" % lack, "nodes[%d].actions[0].data.ids" % i)

    # X5
    x5 = True
    for i, e in enumerate(sc.conns):
        for k in ("source", "target"):
            if e.get(k) not in sc.node_by_id:
                r.add("FAIL", "X5", "connection %s=%s không có node" % (k, e.get(k)), "connections[%d].%s" % (i, k))
                x5 = False
    for j, c in enumerate(sc.rt_conds):
        nn = c.get("next_node")
        if not nn:
            continue
        if nn not in sc.node_by_id:
            r.add("FAIL", "X5", "next_node %s của '%s' không có node đích" % (nn, c.get("name") or c.get("id")), sc.rt_cond_path(j) + ".next_node")
            x5 = False
        elif not any(e.get("source") == sc.begin_id and e.get("sourceHandle") == c.get("id") and e.get("target") == nn for e in sc.conns):
            r.add("FAIL", "X5", "next_node %s của '%s' không có connection" % (nn, c.get("name") or c.get("id")), sc.rt_cond_path(j) + ".next_node")
            x5 = False
    for n in sc.nodes:
        if n.get("id") not in sc.org_by_id:
            r.add("FAIL", "X5", "node %s có ở nodes nhưng thiếu ở org_nodes (DUAL-SCHEMA)" % n.get("id"), "org_nodes")
            x5 = False
    if x5:
        r.ok("X5", "next_node và connection đều có node đích")

    # X6
    end_ids = {n.get("id") for n in sc.nodes if n.get("node_type") == "END_CALL"}
    x6 = True
    for c in sc.rt_conds:
        start = c.get("next_node")
        if not start:
            continue
        reach = sc.reachable(start)
        if reach & end_ids and "hoàn tất" not in lower(c.get("name")):
            r.add("FAIL", "X6", "'%s' đi tới END_CALL; chỉ intent Hoàn tất mới được nối END_CALL" % (c.get("name") or c.get("id")), sc.rt_cond_path(sc.rt_conds.index(c)) + ".next_node")
            x6 = False
    if x6:
        r.ok("X6", "chỉ intent Hoàn tất đi tới END_CALL")

    # X8
    x8 = True
    for path, val in walk_strings(s):
        m = PLACEHOLDER_RE.search(val)
        if m:
            r.add("FAIL", "X8", "còn placeholder '%s'" % m.group(0), path)
            x8 = False
    if x8:
        r.ok("X8", "không còn placeholder <...>")

    # X9
    issues = tts_lint.lint_script(s)
    for it in issues:
        r.add("FAIL", "X9", "%s: %s | ...%s..." % (it["kind"], it["msg"], it["snippet"]), it["where"])
    if not issues:
        r.ok("X9", "lời thoại đạt quy tắc giọng đọc")

    # X10
    if mode == "post" and sent is not None:
        ss = Script(sent)
        lack_nodes = [x for x in ss.node_by_id if x not in sc.node_by_id]
        lack_int = [c.get("id") for c in ss.rt_intents if c.get("id") not in [x.get("id") for x in sc.rt_intents]]
        lack_conn = [(e.get("source"), e.get("sourceHandle"), e.get("target")) for e in ss.conns
                     if not any((f.get("source"), f.get("sourceHandle"), f.get("target")) == (e.get("source"), e.get("sourceHandle"), e.get("target")) for f in sc.conns)]
        def kn(sx):
            return ((sx.begin or {}).get("ai_agent_config") or {}).get("knowledge") or {}
        g_api = [str(a.get("ref_id") or a.get("name")) for a in (kn(sc).get("apis") or []) if isinstance(a, dict)]
        g_file = [str(f.get("id") or f.get("url") or f.get("name")) for f in (kn(sc).get("files") or []) if isinstance(f, dict)]
        lack_api = [str(a.get("ref_id") or a.get("name")) for a in (kn(ss).get("apis") or []) if isinstance(a, dict) and str(a.get("ref_id") or a.get("name")) not in g_api]
        lack_file = [str(f.get("id") or f.get("url") or f.get("name")) for f in (kn(ss).get("files") or []) if isinstance(f, dict) and str(f.get("id") or f.get("url") or f.get("name")) not in g_file]
        if lack_nodes or lack_int or lack_conn or lack_api or lack_file:
            r.add("FAIL", "X10", "bản GET thiếu so với bản gửi: nodes %s, intents %s, connections %s, knowledge.apis %s, knowledge.files %s" % (lack_nodes, lack_int, lack_conn, lack_api, lack_file), "$")
        else:
            r.ok("X10", "bản GET giữ đủ nodes, intents, connections, knowledge đã gửi")
    elif mode == "post":
        r.add("WARN", "X10", "bỏ qua: thiếu --sent (không so được bản GET với payload đã gửi)")
    return r


def main(argv=None):
    tts_lint.utf8_stdout()
    ap = argparse.ArgumentParser(description="Validator kịch bản Callbot SmartAgent (AI_AGENT). Chỉ đọc.")
    ap.add_argument("file", help="payload hoặc bản GET (JSON; chấp nhận cả {payload:{...}})")
    ap.add_argument("--sent", help="payload đã gửi (dùng ở mode post)")
    ap.add_argument("--mode", choices=("pre", "post"), default="pre")
    ap.add_argument("--context", help="tenant_context.json")
    a = ap.parse_args(argv)
    try:
        s = load_json(a.file)
        sent = load_json(a.sent) if a.sent else None
        ctx = load_json(a.context) if a.context else None
    except (OSError, ValueError) as e:
        print("Không đọc được file JSON: %s" % e, file=sys.stderr)
        return 2
    if not isinstance(s, dict):
        print("File không phải object JSON của script", file=sys.stderr)
        return 2
    r = check(Script(s), a.mode, sent, ctx)
    for line in r.lines:
        print(line)
    print("RESULT %s" % ("FAIL" if r.fail else "PASS"))
    return 1 if r.fail else 0


if __name__ == "__main__":
    sys.exit(main())
