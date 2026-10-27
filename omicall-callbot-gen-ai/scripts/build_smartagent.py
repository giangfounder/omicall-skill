# -*- coding: utf-8 -*-
"""Dựng payload kịch bản Callbot SmartAgent (AI_AGENT) bằng cách NHÂN BẢN mẫu từ một bản GET thật (baseline).

  python build_smartagent.py spec.json --base base.json (--new | --update) [--context tenant_context.json] --out payload.json

- Không lấy khung từ tài liệu: mọi node, intent, điều kiện hệ thống, cạnh, option nhân viên đều nhân bản từ --base.
  Kind chỉ sinh được khi base có ít nhất một mẫu cùng loại, hoặc references/templates/<TYPE>.json có _meta.verified=true.
  Thiếu mẫu → exit 2: '<TYPE> chưa kiểm chứng → dựng 1 nút trên editor, GET, extract_template'.
- PUSH_NOTIFICATION, SEND_WEBHOOK, START_OTHER_CAMPAIGN, Ring_group/Outer_group, nối ACTION→ACTION: luôn exit 2.
- --new xoá id/uuid/public_key, version, created_*/last_updated_* (server tự sinh) và đặt is_publish=false (chỉ lưu nháp;
  ngữ nghĩa is_publish còn 'Cần xác nhận'). --update bắt buộc base có cả id lẫn uuid, giữ nguyên is_publish/version của base.
- knowledge.apis: --update mà spec.knowledge.apis rỗng/vắng → GIỮ NGUYÊN apis của base (không xoá cấu hình API của khách);
  chỉ thay khi spec có apis khác rỗng, và in ref_id bị thay/bỏ. --new mà spec không có apis → không chép apis của base.
  knowledge.files giữ theo base. Bản gửi có ít api/file hơn base → WARN X12.
- Base hoặc payload còn giá trị đã che '***' (ví dụ bản lưu của script_outline --save/omi_save) → exit 2, không ghi '***'
  đè lên header thật.
- --out nằm trong thư mục skill → exit 2.
- id/handle, collapseObj, toạ độ sinh tất định theo tên kịch bản: cùng spec + base → cùng output từng byte.
- Cuối cùng tự chạy validate_smartagent (mode pre). Có FAIL → exit 1 (file vẫn ghi để soát).
- Chỗ thiếu ghi 'Cần xác nhận' (spec.pending + phát sinh khi dựng) in ra cuối, không đưa vào payload.
Spec mẫu: references/spec-smartagent.example.json. Không gọi mạng, không lưu, không xuất bản.
"""
import argparse
import copy
import hashlib
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

KINDS = ("handled", "collect", "classify", "transfer", "finish")
UNSUPPORTED = {
    "webhook": "SEND_WEBHOOK", "send_webhook": "SEND_WEBHOOK",
    "push_notification": "PUSH_NOTIFICATION", "notify": "PUSH_NOTIFICATION", "notification": "PUSH_NOTIFICATION",
    "start_other_campaign": "START_OTHER_CAMPAIGN", "other_campaign": "START_OTHER_CAMPAIGN",
    "ring_group": "Ring_group", "outer_group": "Outer_group",
    "action_chain": "ACTION→ACTION", "chain": "ACTION→ACTION",
}
SYSTEM_IDS = ("bot_can_not_answer", "customer_not_response")
MASK = "***"
NEW_DROP = ("id", "uuid", "public_key", "version", "created_date", "created_by", "last_updated_date", "last_updated_by")


class BuildError(Exception):
    def __init__(self, msg, code=2):
        Exception.__init__(self, msg)
        self.code = code


def unverified(type_name):
    return BuildError("%s chưa kiểm chứng → dựng 1 nút trên editor, GET, extract_template (xem references/node-status.json)" % type_name)


def unaccent(s):
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()


def load(path):
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and "nodes" not in obj and isinstance(obj.get("payload"), dict):
        obj = obj["payload"]
    return obj


def load_template(type_name):
    """Template đã duyệt ở references/templates/<TYPE>.json (_meta.verified=true). Trả về (runtime, editor) hoặc None."""
    p = os.path.join(SKILL, "references", "templates", "%s.json" % type_name)
    if not os.path.exists(p):
        return None
    try:
        t = load(p)
    except (OSError, ValueError):
        return None
    if not (isinstance(t, dict) and (t.get("_meta") or {}).get("verified") is True):
        return None
    rt = t.get("runtime") or t.get("node") or ((t.get("nodes") or [None])[0])
    ed = t.get("editor") or t.get("org_node") or ((t.get("org_nodes") or [None])[0])
    if isinstance(rt, dict) and isinstance(ed, dict):
        return rt, ed
    return None


class Ids:
    def __init__(self, seed):
        self.seed = seed

    def make(self, prefix, key, n=10):
        h = hashlib.sha256(("%s|%s" % (self.seed, key)).encode("utf-8")).hexdigest()
        return "%s%s" % (prefix, h[:n])

    def rand20(self, key):
        h = hashlib.sha256(("%s|rand|%s" % (self.seed, key)).encode("utf-8")).hexdigest()
        alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(alpha[int(h[i:i + 2], 16) % len(alpha)] for i in range(0, 40, 2))


class Base:
    """Tìm mẫu trong bản GET baseline."""

    def __init__(self, s):
        self.s = s
        self.nodes = [n for n in (s.get("nodes") or []) if isinstance(n, dict)]
        self.org = {o.get("id"): o for o in (s.get("org_nodes") or []) if isinstance(o, dict)}
        self.begin = next((n for n in self.nodes if n.get("node_type") == "BEGIN"), None)
        if self.begin is None or self.begin.get("id") not in self.org:
            raise BuildError("base không có BEGIN ở cả nodes và org_nodes → GET lại script baseline")
        self.org_begin = self.org[self.begin["id"]]
        an = ((self.begin.get("ai_agent_config") or {}).get("ai_analyze")) or {}
        self.rt_conds = [c for c in (an.get("conditions") or []) if isinstance(c, dict)]
        self.ed_conds = [c for c in ((self.org_begin.get("data") or {}).get("conditions") or []) if isinstance(c, dict)]
        self.conns = [c for c in (s.get("connections") or []) if isinstance(c, dict)]

    def node_with_action(self, typ):
        for n in self.nodes:
            for a in n.get("actions") or []:
                if isinstance(a, dict) and a.get("type") == typ and n.get("id") in self.org:
                    return n, self.org[n["id"]]
        return None

    def node_of_type(self, nt):
        for n in self.nodes:
            if n.get("node_type") == nt and n.get("id") in self.org:
                return n, self.org[n["id"]]
        return None

    def intent_pair(self, need_collect=False):
        eds = {c.get("id"): c for c in self.ed_conds if c.get("type") == "CUSTOM_INTENT"}
        for c in self.rt_conds:
            if c.get("type") != "CUSTOM_INTENT" or c.get("id") not in eds:
                continue
            if need_collect:
                rs = [x for x in (c.get("action_steps") or []) if isinstance(x, dict) and x.get("action") == "collect_variables"]
                es = [x for x in (eds[c["id"]].get("actionStep") or []) if isinstance(x, dict) and x.get("action") == "collect_variables"]
                if not (rs and es and es[0].get("variablesCode")):
                    continue
                return c, eds[c["id"]], rs[0], es[0]
            if c.get("data") and eds[c["id"]].get("data"):
                return c, eds[c["id"]]
        return None

    def system_pair(self, sid):
        rt = next((c for c in self.rt_conds if c.get("id") == sid), None)
        ed = next((c for c in self.ed_conds if c.get("id") == sid), None)
        return (rt, ed) if rt and ed else None

    def edge_sample(self, system=False):
        bid = self.begin["id"]
        for c in self.conns:
            if c.get("source") == bid and ((c.get("sourceHandle") in SYSTEM_IDS) == system):
                return c
        return next((c for c in self.conns if c.get("source") == bid), None)


def edge_id(sample, src, sh, tgt, th, pending):
    if sample:
        s, h, t, k = sample.get("source"), sample.get("sourceHandle"), sample.get("target"), str(sample.get("targetHandle"))
        sid = sample.get("id")
        if sid == "reactflow__edge-%s%s-%s%s" % (s, h, t, k):
            return "reactflow__edge-%s%s-%s%s" % (src, sh, tgt, th)
        if sid == "reactflow__edge-%s%s-%s%s1" % (s, h, t, k):
            return "reactflow__edge-%s%s-%s%s1" % (src, sh, tgt, th)
    msg = "Cần xác nhận: định dạng id cạnh (base không có mẫu cạnh khớp) — đang dùng reactflow__edge-<source><handle>-<target><targetHandle>"
    if msg not in pending:
        pending.append(msg)
    return "reactflow__edge-%s%s-%s%s" % (src, sh, tgt, th)


def masked_paths(obj, path="$"):
    """Đường dẫn các chuỗi chứa giá trị đã che '***'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for x in masked_paths(v, "%s.%s" % (path, k)):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in masked_paths(v, "%s[%d]" % (path, i)):
                yield x
    elif isinstance(obj, str) and MASK in obj:
        yield path


def kn_of(script):
    for n in script.get("nodes") or []:
        if isinstance(n, dict) and n.get("node_type") == "BEGIN":
            return ((n.get("ai_agent_config") or {}).get("knowledge")) or {}
    return {}


def ref_ids(apis):
    return [str(a.get("ref_id") or a.get("name")) for a in (apis or []) if isinstance(a, dict)]


def set_if(d, key, val):
    if isinstance(d, dict) and key in d:
        d[key] = val


def build(spec, base_obj, mode, context=None):
    pending = list(spec.get("pending") or [])
    name = (spec.get("name") or "").strip()
    if not name:
        raise BuildError("spec thiếu name")
    intents = spec.get("intents") or []
    if not intents:
        raise BuildError("spec thiếu intents[]")
    for it in intents:
        k = (it.get("kind") or "").strip().lower()
        if k in UNSUPPORTED:
            raise unverified(UNSUPPORTED[k])
        if k not in KINDS:
            raise BuildError("kind '%s' của intent '%s' không hỗ trợ (chỉ %s)" % (k, it.get("name"), ", ".join(KINDS)))
    tr = spec.get("transfer") or {}
    ttype = (tr.get("type") or "Extension").strip()
    if ttype.lower() in UNSUPPORTED:
        raise unverified(UNSUPPORTED[ttype.lower()])
    if ttype != "Extension":
        raise unverified("TRANSFER_CALL %s" % ttype)

    b = Base(base_obj)
    out = copy.deepcopy(base_obj)
    ids = Ids(name)
    if mode == "new":
        for k in NEW_DROP:
            out.pop(k, None)
        out["is_publish"] = False
        pending.append("Cần xác nhận: ngữ nghĩa is_publish (api-reference C11) — kịch bản mới gửi is_publish=false, chỉ lưu nháp; xuất bản chỉ khi user duyệt")
    else:
        if not base_obj.get("id") or not base_obj.get("uuid"):
            raise BuildError("--update cần base có cả id lẫn uuid (chỉ có id → server tạo script trùng)")
    out["name"] = name
    out.pop("_ghi_chu", None)

    kinds = [(it.get("kind") or "").lower() for it in intents]
    # --- mẫu bắt buộc
    ip = b.intent_pair()
    if ip is None:
        tpl = load_template("CUSTOM_INTENT")
        if not tpl:
            raise unverified("CUSTOM_INTENT")
        ip = tpl
    rt_int_s, ed_int_s = ip[0], ip[1]
    sys_pairs = {}
    for sid in SYSTEM_IDS:
        p = b.system_pair(sid)
        if not p:
            raise BuildError("base thiếu điều kiện hệ thống %s ở runtime hoặc editor → GET lại baseline" % sid)
        sys_pairs[sid] = p
    xfer_s = b.node_with_action("TRANSFER_CALL") or load_template("TRANSFER_CALL")
    if not xfer_s:
        raise unverified("TRANSFER_CALL")
    clf_s = None
    if "classify" in kinds or "collect" in kinds:
        clf_s = b.node_with_action("ADD_CLASSIFY") or load_template("ADD_CLASSIFY")
        if not clf_s:
            raise unverified("ADD_CLASSIFY")
    end_s = None
    if "finish" in kinds:
        end_s = b.node_of_type("END_CALL") or load_template("END_CALL")
        if not end_s:
            raise unverified("END_CALL")
    col_s = None
    if "collect" in kinds:
        col_s = b.intent_pair(need_collect=True)
        bcfg = b.begin.get("ai_agent_config") or {}
        cv = [x for x in (bcfg.get("collect_variables") or []) if isinstance(x, dict)]
        cd = [x for x in ((b.org_begin.get("data") or {}).get("collectData") or []) if isinstance(x, dict)]
        tv = [x for x in (base_obj.get("variables") or []) if isinstance(x, dict) and x.get("type") == "COLLECT_INFO"]
        civ = [x for x in (base_obj.get("collect_info_variables") or []) if isinstance(x, dict)]
        if not (col_s and cv and cd and tv and civ):
            raise unverified("collect_variables (intent thu biến)")
        col_s = col_s + (cv[0], cd[0], tv[0], civ[0])

    # --- biến
    var_defs = {}
    for v in spec.get("variables") or []:
        if isinstance(v, dict) and v.get("code"):
            var_defs[v["code"]] = v
    used_vars = []
    for it in intents:
        for v in it.get("collect_vars") or []:
            code = v.get("code") if isinstance(v, dict) else v
            if isinstance(v, dict):
                var_defs.setdefault(code, v)
            if code not in var_defs:
                raise BuildError("biến '%s' của intent '%s' chưa khai báo ở spec.variables" % (code, it.get("name")))
            if code not in used_vars:
                used_vars.append(code)

    bid = b.begin["id"]
    obx = (b.org_begin.get("position") or {}).get("x", 0) or 0
    oby = (b.org_begin.get("position") or {}).get("y", 0) or 0
    nodes, org_nodes, conns = [], [], []
    slot = [0]

    def place(org):
        x, y = obx + 450, oby + 260 * slot[0]
        slot[0] += 1
        set_if(org, "position", {"x": x, "y": y})
        d = org.get("data") or {}
        if isinstance(d.get("pos"), dict):
            d["pos"] = dict(d["pos"], x=float(x), y=float(y))

    # --- TRANSFER_CALL (bot_can_not_answer luôn nối tới đây)
    xr, xo = copy.deepcopy(xfer_s[0]), copy.deepcopy(xfer_s[1])
    xid = ids.make("xfer_", "transfer")
    xr["id"] = xid
    xo["id"] = xid
    ra = next(a for a in xr["actions"] if isinstance(a, dict) and a.get("type") == "TRANSFER_CALL")
    aid = ids.make("a_", "transfer_action")
    ra["id"] = aid
    agent, ext, agent_name = tr.get("agent"), tr.get("ext"), tr.get("agent_name")
    if not agent:
        base_ids = (ra.get("data") or {}).get("ids") or []
        pending.append("Cần xác nhận: nhân viên nhận chuyển máy (spec.transfer.agent trống%s)" % (", đang giữ nhân viên của baseline" if base_ids and any(base_ids) else ""))
    else:
        ra["data"]["ids"] = [str(agent)]
        if ext is not None:
            ra["data"]["sip_number"] = str(ext)
        pending.append("Cần xác nhận: option.value/ids của nhân viên là _id hay agent_id (theo GET thật)")
        if context is not None:
            known = {str(a.get(k)) for a in (context.get("agents") or []) if isinstance(a, dict) for k in ("_id", "agent_id", "contact_id") if a.get(k)}
            if str(agent) not in known:
                pending.append("Cần xác nhận: nhân viên %s không có trong tenant_context.agents" % agent)
    oa = next((a for a in ((xo.get("data") or {}).get("actions") or []) if isinstance(a, dict) and a.get("type") == "TRANSFER_CALL"), None)
    if oa is None:
        raise unverified("TRANSFER_CALL (editor)")
    oa["id"] = aid
    if agent:
        ds = oa.get("datas") or {}
        sel = copy.deepcopy(ds.get("selected") or {})
        if not sel:
            pending.append("Cần xác nhận: base không có option nhân viên để nhân bản")
        else:
            sel.update({"value": str(agent)})
            if ext is not None:
                set_if(sel, "sipNumber", str(ext))
            if agent_name:
                set_if(sel, "fullName", agent_name)
            if ext is not None and agent_name:
                set_if(sel, "label", "%s - %s" % (ext, agent_name))
            ds["selected"] = sel
            to = ds.get("typeOptions")
            if isinstance(to, dict) and "Extension" in to:
                to["Extension"] = [copy.deepcopy(sel)]
            for od in xo.get("orgDatas") or []:
                if isinstance(od, dict) and isinstance(od.get("datas"), dict) and "selected" in od["datas"]:
                    od["datas"]["selected"] = copy.deepcopy(sel)
    place(xo)
    nodes.append(xr)
    org_nodes.append(xo)

    # --- intents
    rt_list, ed_list = [], []
    end_id = None
    labels_all = []
    clf_var_sample = None
    for n in b.nodes:
        for v in n.get("variables") or []:
            if n.get("node_type") == "ACTION" and isinstance(v, dict) and v.get("field_code"):
                clf_var_sample = clf_var_sample or v
    clf_org_var_sample = None
    for o in b.org.values():
        for v in ((o.get("data") or {}).get("variables") or []):
            if isinstance(v, dict) and v.get("variable") and v.get("variable") != "var_" and (o.get("data") or {}).get("type") == "ACTION":
                clf_org_var_sample = clf_org_var_sample or v
    edge_s_int = b.edge_sample(system=False)
    edge_s_sys = b.edge_sample(system=True)

    for i, it in enumerate(intents):
        kind = it["kind"].lower()
        iname = (it.get("name") or "").strip()
        content = (it.get("content") or "").strip()
        if not iname or not content:
            raise BuildError("intent #%d thiếu name hoặc content" % (i + 1))
        h = ids.make("i_", "intent|%d|%s" % (i, iname))
        did = ids.make("d_", "intent_data|%d|%s" % (i, iname))
        rc = copy.deepcopy(rt_int_s)
        ec = copy.deepcopy(ed_int_s)
        rc["id"] = h
        rc["name"] = iname
        rd = copy.deepcopy((rt_int_s.get("data") or [{}])[0])
        rd.update({"id": did, "content": content})
        rc["data"] = [rd]
        rc["action_steps"] = None
        ec["id"] = h
        ec["name"] = iname
        ed = copy.deepcopy((ed_int_s.get("data") or [{}])[0])
        ed.update({"id": did, "content": content})
        ec["data"] = [ed]
        ec["actionStep"] = []
        wh = ec.get("webhookId")
        if isinstance(wh, str) and "-" in wh:
            ec["webhookId"] = wh.rsplit("-", 1)[0] + "-" + ids.rand20("webhook|%d" % i)
            if i == 0:
                pending.append("Cần xác nhận: cách sinh hậu tố webhookId (đang sinh 20 ký tự tất định)")
        target = None
        cvars = [v.get("code") if isinstance(v, dict) else v for v in (it.get("collect_vars") or [])]
        if kind == "collect":
            if not cvars:
                raise BuildError("intent '%s' kind collect cần collect_vars[]" % iname)
            if not it.get("classify_labels"):
                raise BuildError("intent '%s' kind collect cần classify_labels[] (sau khi thu phải phân loại hoặc xác nhận trước khi chuyển)" % iname)
            rs = copy.deepcopy(col_s[2])
            rs["variables_code"] = list(cvars)
            rc["action_steps"] = [rs]
            es = copy.deepcopy(col_s[3])
            vsample = (col_s[3].get("variablesCode") or [{}])[0]
            vc = []
            for code in cvars:
                vd = var_defs[code]
                x = copy.deepcopy(vsample)
                x.update({"id": code, "value": code})
                set_if(x, "label", vd.get("name") or code)
                set_if(x, "labelUnsigned", unaccent(vd.get("name") or code))
                set_if(x, "tooltipParent", vd.get("prompt") or "")
                vc.append(x)
            es["variablesCode"] = vc
            set_if(es, "id", ids.make("step_", "collect|%d" % i))
            ec["actionStep"] = [es]
        if kind in ("collect", "classify"):
            labels = [str(x) for x in (it.get("classify_labels") or [])]
            if not labels:
                raise BuildError("intent '%s' kind classify cần classify_labels[]" % iname)
            cr, co = copy.deepcopy(clf_s[0]), copy.deepcopy(clf_s[1])
            cid = ids.make("clf_", "classify|%d" % i)
            cr["id"] = cid
            co["id"] = cid
            caid = ids.make("u_", "classify_action|%d" % i)
            ca = next(a for a in cr["actions"] if isinstance(a, dict) and a.get("type") == "ADD_CLASSIFY")
            ca["id"] = caid
            csample = ((ca.get("data") or {}).get("classifies") or [{}])[0]
            cls = [dict(copy.deepcopy(csample), name=l) for l in labels]
            ca["data"] = {"ids": list(labels), "classifies": cls}
            set_if(cr, "description", "Phân loại khách: %s" % ", ".join(labels))
            oca = next((a for a in ((co.get("data") or {}).get("actions") or []) if isinstance(a, dict) and a.get("type") == "ADD_CLASSIFY"), None)
            if oca is None:
                raise unverified("ADD_CLASSIFY (editor)")
            set_if(oca, "id", "o_" + caid)
            oca["datas"] = {"ids": list(labels), "classifies": copy.deepcopy(cls)}
            od = co.get("data") or {}
            set_if(od, "description", "Phân loại: %s" % ", ".join(labels))
            set_if(od, "name", "Phân loại %s" % iname.lower())
            for x in co.get("orgDatas") or []:
                if isinstance(x, dict) and "datas" in x:
                    x["datas"] = {"ids": list(labels), "classifies": copy.deepcopy(cls)}
            rv, ov = [], []
            if cvars:
                if clf_var_sample is None or clf_org_var_sample is None:
                    pending.append("Cần xác nhận: biến ở node phân loại %s (base không có mẫu variables ở node ACTION)" % cid)
                else:
                    for code in cvars:
                        x = copy.deepcopy(clf_var_sample)
                        x.update({"field_code": code})
                        set_if(x, "field_name", var_defs[code].get("name") or code)
                        rv.append(x)
                        y = copy.deepcopy(clf_org_var_sample)
                        y["variable"] = code
                        ov.append(y)
            cr["variables"] = rv
            set_if(od, "variables", ov)
            place(co)
            nodes.append(cr)
            org_nodes.append(co)
            target = cid
            for l in labels:
                if l not in labels_all:
                    labels_all.append(l)
        elif kind == "transfer":
            target = xid
        elif kind == "finish":
            if end_id is None:
                er, eo = copy.deepcopy(end_s[0]), copy.deepcopy(end_s[1])
                end_id = ids.make("end_", "end")
                er["id"] = end_id
                eo["id"] = end_id
                edesc = spec.get("end_description") or "Kết thúc cuộc gọi: chỉ cúp sau khi khách đã xác nhận không còn nhu cầu. Bot cảm ơn khách, chúc sức khỏe, xin phép kết thúc, lịch sự tạm biệt rồi kết thúc cuộc gọi."
                er["description"] = edesc
                eod = eo.get("data") or {}
                set_if(eod, "id", end_id)
                eod["description"] = edesc
                if spec.get("end_text"):
                    eod["content"] = spec["end_text"]
                else:
                    pending.append("Cần xác nhận: câu kết thúc end_text trống")
                place(eo)
                nodes.append(er)
                org_nodes.append(eo)
            target = end_id
        rc["next_node"] = target
        rt_list.append(rc)
        ed_list.append(ec)
        if target:
            e = copy.deepcopy(edge_s_int) if edge_s_int else {"type": "custom"}
            e.update({"source": bid, "sourceHandle": h, "target": target, "targetHandle": "1"})
            e["id"] = edge_id(edge_s_int, bid, h, target, "1", pending)
            conns.append(e)

    # --- điều kiện hệ thống (luôn ở cuối)
    node_ids = {bid, xid} | {n["id"] for n in nodes}
    for sid in SYSTEM_IDS:
        r, e = copy.deepcopy(sys_pairs[sid][0]), copy.deepcopy(sys_pairs[sid][1])
        if sid == "bot_can_not_answer":
            r["next_node"] = xid
        elif r.get("next_node") not in node_ids:
            r["next_node"] = None
        rt_list.append(r)
        ed_list.append(e)
    e = copy.deepcopy(edge_s_sys) if edge_s_sys else {"type": "custom"}
    e.update({"source": bid, "sourceHandle": "bot_can_not_answer", "target": xid, "targetHandle": "1"})
    e["id"] = edge_id(edge_s_sys, bid, "bot_can_not_answer", xid, "1", pending)
    conns.append(e)

    # --- BEGIN
    br = copy.deepcopy(b.begin)
    bo = copy.deepcopy(b.org_begin)
    cfg = br.setdefault("ai_agent_config", {})
    if spec.get("prompt"):
        cfg["instruction"] = spec["prompt"]
    else:
        pending.append("Cần xác nhận: spec.prompt trống, đang giữ instruction của baseline")
    if spec.get("start_call"):
        cfg["start_call_instruction"] = spec["start_call"]
    an = cfg.setdefault("ai_analyze", {})
    an["conditions"] = rt_list
    if isinstance(an.get("bot_can_not_answer"), dict):
        an["bot_can_not_answer"]["next_node"] = xid
    else:
        raise BuildError("base thiếu ai_analyze.bot_can_not_answer → GET lại baseline")
    if isinstance(an.get("customer_not_response"), dict) and an["customer_not_response"].get("next_node") not in node_ids:
        an["customer_not_response"]["next_node"] = None
    kn = spec.get("knowledge") or {}
    spec_apis = kn.get("apis") if isinstance(kn.get("apis"), list) else []
    base_kn = cfg.get("knowledge") if isinstance(cfg.get("knowledge"), dict) else {}
    base_apis = [a for a in (base_kn.get("apis") or []) if isinstance(a, dict)]
    if spec_apis:
        old, new = ref_ids(base_apis), ref_ids(spec_apis)
        cfg.setdefault("knowledge", {})["apis"] = copy.deepcopy(spec_apis)
        if mode == "update" and base_apis:
            pending.append("Cần xác nhận: knowledge.apis thay theo spec — giữ/thay ref_id %s, bỏ ref_id %s, thêm ref_id %s"
                           % ([x for x in old if x in new], [x for x in old if x not in new], [x for x in new if x not in old]))
    elif mode == "update":
        if base_apis:
            pending.append("Cần xác nhận: spec.knowledge.apis rỗng/vắng → giữ nguyên %d api của base (ref_id %s); muốn xoá api thì sửa trên giao diện khi user duyệt"
                           % (len(base_apis), ref_ids(base_apis)))
    else:
        if base_apis:
            pending.append("Cần xác nhận: không chép %d api của base (ref_id %s) sang kịch bản mới; cần thì khai báo ở spec.knowledge.apis theo tài liệu API của khách"
                           % (len(base_apis), ref_ids(base_apis)))
        if isinstance(cfg.get("knowledge"), dict):
            cfg["knowledge"]["apis"] = []
    if mode == "new" and (base_kn.get("files") or []):
        pending.append("Cần xác nhận: kịch bản mới đang giữ %d file RAG (knowledge.files) của base" % len(base_kn.get("files") or []))
    bd = bo.setdefault("data", {})
    bd["conditions"] = ed_list
    if spec.get("start_call"):
        set_if(bd, "startCallInstruction", spec["start_call"])
    if spec.get("prompt"):
        set_if(bd, "personality", spec["prompt"])
    co = bd.get("collapseObj") or {}
    intent_shape = None
    base_int_ids = {c.get("id") for c in b.ed_conds if c.get("type") == "CUSTOM_INTENT"}
    for k, v in co.items():
        if k in base_int_ids:
            intent_shape = v
            break
    if intent_shape is None:
        intent_shape = {"isCollapsible": True, "isCollapse": False}
        pending.append("Cần xác nhận: base không có mẫu collapseObj của intent")
    nco = {k: v for k, v in co.items() if k not in base_int_ids}
    for c in ed_list:
        if c.get("type") == "CUSTOM_INTENT":
            nco[c["id"]] = copy.deepcopy(intent_shape)
    bd["collapseObj"] = nco
    if col_s:
        cv_s, cd_s, tv_s, civ_s = col_s[4], col_s[5], col_s[6], col_s[7]
        cvl, cdl, tvl, civl = [], [], [], []
        for code in used_vars:
            vd = var_defs[code]
            vname = vd.get("name") or code
            x = copy.deepcopy(cv_s)
            x.update({"variable_code": code, "variable_name": vname})
            set_if(x, "variable_value", vd.get("prompt") or "")
            cvl.append(x)
            y = copy.deepcopy(cd_s)
            y.update({"id": code, "name": vname})
            set_if(y, "uuid", code)
            set_if(y, "oldName", vname)
            set_if(y, "content", vd.get("prompt") or "")
            cdl.append(y)
            z = copy.deepcopy(tv_s)
            z.update({"field_code": code, "field_name": vname})
            tvl.append(z)
            w = copy.deepcopy(civ_s)
            w.update({"variable_code": code, "variable_name": vname})
            civl.append(w)
        cfg["collect_variables"] = cvl
        bd["collectData"] = cdl
        others = [v for v in (out.get("variables") or []) if not (isinstance(v, dict) and v.get("type") == "COLLECT_INFO")]
        out["variables"] = tvl + others
        out["collect_info_variables"] = civl
    nodes.insert(0, br)
    org_nodes.insert(0, bo)

    # --- top-level
    csample = ((base_obj.get("classifies") or [{"name": ""}])[0]) or {"name": ""}
    out["classifies"] = [dict(copy.deepcopy(csample), name=l) for l in labels_all] if labels_all else copy.deepcopy(base_obj.get("classifies") or [])
    out["nodes"] = nodes
    out["org_nodes"] = org_nodes
    out["connections"] = conns
    bad = list(masked_paths(out))
    if bad:
        raise BuildError("payload còn giá trị đã che '%s' tại %s — base là bản đã che (script_outline --save / file của omi_save). "
                         "Không dùng bản che làm --base cho phần này vì sẽ ghi '%s' đè lên giá trị thật (ví dụ header API). "
                         "Phần có khoá bí mật (header Authorization của API khách...) sửa trên giao diện khi user duyệt; ghi 'Cần xác nhận'."
                         % (MASK, ", ".join(bad[:5]), MASK))
    return out, pending


def shrink_warnings(base_obj, payload):
    """WARN X12: bản gửi có ít knowledge.apis/files hơn base."""
    lines = []
    bk, pk = kn_of(base_obj), kn_of(payload)
    for key in ("apis", "files"):
        b = [x for x in (bk.get(key) or []) if isinstance(x, dict)]
        p = [x for x in (pk.get(key) or []) if isinstance(x, dict)]
        if len(p) < len(b):
            lines.append("WARN X12 knowledge.%s của bản gửi (%d) ít hơn base (%d) — Cần xác nhận có chủ ý bỏ" % (key, len(p), len(b)))
    return lines


def _repo_root():
    """Repo nguồn chứa skill (thư mục cha trực tiếp có .git hoặc tools/sync_shared.py); None nếu là bản cài."""
    d = os.path.dirname(SKILL)
    if os.path.isdir(os.path.join(d, ".git")) or os.path.isfile(os.path.join(d, "tools", "sync_shared.py")):
        return d
    return None


def inside_skill(path):
    """True khi path nằm trong thư mục skill hoặc trong repo nguồn của skill (output không ghi vào repo)."""
    d = os.path.normcase(os.path.abspath(path))
    return any(r and d.startswith(os.path.normcase(r + os.sep)) for r in (SKILL, _repo_root()))


def main(argv=None):
    import tts_lint
    tts_lint.utf8_stdout()
    ap = argparse.ArgumentParser(description="Dựng payload SmartAgent bằng cách nhân bản mẫu từ bản GET thật. Không gọi mạng.")
    ap.add_argument("spec", help="spec JSON (xem references/spec-smartagent.example.json)")
    ap.add_argument("--base", help="bản GET thật của một script cùng tenant (bắt buộc)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--new", action="store_true", help="kịch bản mới: xoá id/uuid/public_key")
    g.add_argument("--update", action="store_true", help="cập nhật đúng script của base: cần id + uuid")
    ap.add_argument("--context", help="tenant_context.json")
    ap.add_argument("--out", required=True, help="file payload ra (đặt trong scratch, không trong thư mục skill)")
    a = ap.parse_args(argv)
    if not a.base:
        print("Thiếu --base: tạo 1 script rỗng trên editor (hoặc chọn script có sẵn), GET bằng `script_outline.py --id <id> --save`, rồi truyền file đó vào --base.", file=sys.stderr)
        return 2
    if not (a.new or a.update):
        print("Chọn --new (kịch bản mới) hoặc --update (sửa đúng script của base).", file=sys.stderr)
        return 2
    if inside_skill(a.out):
        print("Không ghi --out vào thư mục skill hay repo skill (%s). Đặt file trong OMI_SCRATCH hoặc thư mục tạm."
              % (_repo_root() or SKILL), file=sys.stderr)
        return 2
    try:
        spec = load(a.spec)
        base = load(a.base)
        ctx = load(a.context) if a.context else None
    except (OSError, ValueError) as e:
        print("Không đọc được JSON: %s" % e, file=sys.stderr)
        return 2
    try:
        payload, pending = build(spec, base, "new" if a.new else "update", ctx)
    except BuildError as e:
        print("LỖI: %s" % e, file=sys.stderr)
        return e.code
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("Đã ghi payload: %s" % a.out)
    for p in pending:
        print("PENDING %s" % p)
    import validate_smartagent as v
    r = v.check(v.Script(payload), "pre", None, ctx)
    for line in r.lines:
        print(line)
    if a.update:
        for line in shrink_warnings(base, payload):
            print(line)
    print("RESULT %s" % ("FAIL" if r.fail else "PASS"))
    return 1 if r.fail else 0


if __name__ == "__main__":
    sys.exit(main())
