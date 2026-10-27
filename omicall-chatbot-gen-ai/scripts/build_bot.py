# -*- coding: utf-8 -*-
"""Vá spec nghiệp vụ lên bản GET thật của bot OmiBot → payload cho save_draft_v2. Không gọi mạng.

    python build_bot.py spec.json --base <GET.json> --out payload.json

- Chỉ vá trên baseline: giữ nguyên `_id`, `uuid`, `is_publish` và mọi trường không có trong spec.
- Phần được vá (đều là loại đã kiểm chứng, xem references/node-status.json):
  system_prompt; BEGIN ai_analyze.content; Trường hợp CUSTOM_INTENT ngôn ngữ tự nhiên ở CẢ editor lẫn runtime
  (api-reference.md mục "Trường hợp mô tả bằng ngôn ngữ tự nhiên"); OMI_BOT_COLLECT_INFO + case COMPARE NOT_EQUAL;
  ACTION SEND_WEBHOOK; ACTION START_OTHER_CAMPAIGN; api_knowledge + api_knowledge_ids (mục "API Knowledge").
- SEND_WEBHOOK mới: header = spec.headers, không khai thì Content-Type: application/json; KHÔNG kế thừa header
  của webhook mẫu. Editor của loại này chưa kiểm chứng → không chép mẫu editor, WARN dựng/kiểm trên UI.
- --out nằm trong thư mục skill hoặc repo → exit 2 (payload chưa che, có thể chứa bí mật; ghi vào scratch).
- Node mới, cạnh mới chép theo MẪU có sẵn trong base (cùng node_type / cùng loại hành động); base thiếu mẫu → exit 2,
  dựng 1 nút loại đó trên UI rồi GET lại làm base. Không tự bịa cấu trúc.
- Loại chưa có JSON (send_message, end, handoff/chuyển nhân viên, kick_off_context) hoặc ý định hệ thống → exit 2.
- Id sinh tất định từ _id của bot + khoá trong spec → chạy lại cho output giống từng byte.
- Cuối cùng tự chạy validate_bot.py --mode pre; có FAIL → exit 1.
Mẫu spec: references/spec-bot.example.json.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SYSTEM_TAIL = ["bot_can_not_answer", "customer_not_response"]
TOP_KEYS = {"_ghi_chu", "system_prompt", "begin_content", "intents", "api_knowledge"}
STEP_TYPES = {"collect_info", "send_webhook", "start_other_campaign"}
UI_ONLY = {"send_message": "Gửi tin nhắn chung", "end": "Kết thúc trò chuyện", "handoff": "chuyển nhân viên",
           "transfer": "chuyển nhân viên", "chuyen_nhan_vien": "chuyển nhân viên",
           "kick_off_context": "Kích hoạt ngữ cảnh"}
DEFAULT_WEBHOOK_HEADERS = [{"key": "Content-Type", "value": "application/json"}]
UI_MSG = ("chưa có JSON kiểm chứng (references/api-reference.md mục 'Kịch bản' — palette và 'Quy trình build "
          "Kịch bản bằng API' bước 3; references/node-status.json) → làm UI: điền → đóng hết ngăn kéo → Lưu lại → GET")


class SpecError(Exception):
    pass


def unaccent(s):
    s = str(s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", unaccent(s).lower()).strip("_")


def var_code(name):
    """api-reference.md: mã biến = var_<tên bỏ dấu, bỏ _>."""
    return "var_" + re.sub(r"[^a-z0-9]", "", unaccent(name).lower())


class Builder:
    def __init__(self, base, spec):
        self.bot = copy.deepcopy(base)
        self.spec = spec
        self.warn = []
        self.seed = str(self.bot.get("_id") or "")
        camp = self.bot.get("campaign")
        if not isinstance(camp, dict):
            raise SpecError("base thiếu campaign — không phải GET bot SCENARIO_HANDLER")
        self.nodes = camp.setdefault("nodes", [])
        self.maps = camp.setdefault("name_mappings", [])
        edges = camp.get("edges")
        if not isinstance(edges, dict):
            edges = camp["edges"] = {"connections": []}
        self.conns = edges.setdefault("connections", [])
        self.begin = next((n for n in self.nodes if n.get("node_type") == "BEGIN_CONTEXT"), None)
        self.begin_ed = next((m for m in self.maps if m.get("type") == "BEGIN_CONTEXT"), None)
        if self.begin is None or self.begin_ed is None:
            raise SpecError("base không có BEGIN_CONTEXT ở campaign.nodes và campaign.name_mappings")
        # mẫu lấy từ base TRƯỚC khi vá
        self.tpl_nodes = copy.deepcopy(self.nodes)
        self.tpl_maps = {m.get("id"): copy.deepcopy(m) for m in self.maps if isinstance(m, dict)}
        self.tpl_edge = copy.deepcopy(self.conns[0]) if self.conns else None

    # ---- tiện ích ----
    def hid(self, *parts):
        return hashlib.sha1("|".join([self.seed] + [str(p) for p in parts]).encode("utf-8")).hexdigest()[:10]

    def node_by_id(self, nid):
        return next((n for n in self.nodes if n.get("id") == nid), None)

    def template(self, node_type, action_type=None):
        for n in self.tpl_nodes:
            if n.get("node_type") != node_type:
                continue
            if action_type and not any(isinstance(a, dict) and a.get("type") == action_type for a in n.get("actions") or []):
                continue
            return n
        what = node_type + (" " + action_type if action_type else "")
        raise SpecError("base chưa có mẫu node %s → dựng 1 nút loại này trên UI (điền → đóng hết ngăn kéo → Lưu lại), "
                        "GET lại làm --base rồi chạy lại" % what)

    def position(self, parent, dx, dy):
        pos = (parent or {}).get("position") or {}
        out = {}
        for k, d in (("x", dx), ("y", dy)):
            v = pos.get(k, 0)
            try:
                num = float(v) + d
            except (TypeError, ValueError):
                num = d
            num = int(num) if float(num).is_integer() else num
            out[k] = str(num) if isinstance(v, str) else num
        return out

    def add_edge(self, src, handle, tgt):
        if self.tpl_edge is None:
            raise SpecError("base chưa có cạnh mẫu trong campaign.edges.connections → nối 1 cạnh trên UI, GET lại làm --base")
        self.conns[:] = [c for c in self.conns if not (c.get("source") == src and c.get("sourceHandle") == handle)]
        e = copy.deepcopy(self.tpl_edge)
        e["id"] = "reactflow__edge-%s%s-%s1" % (src, handle, tgt)
        e["source"], e["sourceHandle"], e["target"] = src, handle, tgt
        e.setdefault("targetHandle", "1")
        self.conns.append(e)

    def put_node(self, node):
        for i, n in enumerate(self.nodes):
            if n.get("id") == node["id"]:
                self.nodes[i] = node
                return
        self.nodes.append(node)

    def put_map(self, entry):
        for i, m in enumerate(self.maps):
            if m.get("id") == entry["id"]:
                self.maps[i] = entry
                return
        self.maps.append(entry)

    def clone(self, tpl, new_id, parent, dx, dy):
        n = copy.deepcopy(tpl)
        old = n.get("id")
        n["id"] = new_id
        n["is_first_node"] = False
        n["next_nodes"] = []
        n["position"] = self.position(parent, dx, dy)
        aa = n.get("ai_analyze")
        if isinstance(aa, dict) and isinstance(aa.get("assistant_id"), str) and old:
            aa["assistant_id"] = aa["assistant_id"].replace(str(old), new_id)
        ed = copy.deepcopy(self.tpl_maps.get(old)) if old in self.tpl_maps else None
        if ed is not None:
            ed["id"] = new_id
        return n, ed

    # ---- các bước ----
    def build_step(self, step, key, parent, depth, row):
        t = step.get("type")
        nid = self.hid(key, "node", depth, t)
        dy = 360 * row if depth == 0 else 0
        if t == "collect_info":
            n, ed = self.clone(self.template("OMI_BOT_COLLECT_INFO"), nid, parent, 440, dy)
            aa = n.setdefault("ai_analyze", {})
            aa["content"] = step.get("instruction") or ""
            vars_ = step.get("variables") or []
            if not vars_:
                raise SpecError("intent %s: collect_info cần ít nhất 1 biến" % key)
            cv = []
            for v in vars_:
                if not v.get("name"):
                    raise SpecError("intent %s: biến thiếu name" % key)
                cv.append({"variable_code": var_code(v["name"]), "variable_name": v["name"],
                           "variable_value": v.get("description") or "", "option": "ENTITY", "save_to_conv": False})
            aa["collect_variables"] = cv
            aa["conditions"] = []
            if ed is not None:
                ed["collect_data"] = [{k: c[k] for k in ("variable_code", "variable_name", "variable_value", "save_to_conv")}
                                      for c in cv]
            else:
                self.warn.append("base không có mẫu editor cho OMI_BOT_COLLECT_INFO — mở editor kiểm sau khi lưu")
            self.put_node(n)
            if ed is not None:
                self.put_map(ed)
            wc = step.get("when_collected")
            if wc:
                vname = wc.get("variable")
                codes = {c["variable_name"]: c["variable_code"] for c in cv}
                if vname not in codes:
                    raise SpecError("intent %s: when_collected.variable '%s' không có trong variables" % (key, vname))
                child = self.build_step(wc.get("then") or {}, key, n, depth + 1, row)
                case_id = self.hid(key, "collect_case", depth)
                aa["conditions"] = [{"id": case_id, "type": "CUSTOM_INTENT", "next_node": child,
                                     "data": [{"type": "COMPARE", "compare_conditions": [
                                         {"operator": "NOT_EQUAL", "values": [{"start_value": "", "end_value": ""}],
                                          "target_type": "COLLECT_INFO", "is_dynamic_field": True,
                                          "field_code": codes[vname]}]}],
                                     "operator_type": "AND"}]
                n["next_nodes"] = [child]
                self.add_edge(nid, case_id, child)
            return nid
        if t == "send_webhook":
            if not step.get("url") or step.get("body_json") is None:
                raise SpecError("intent %s: send_webhook cần url và body_json" % key)
            n, ed = self.clone(self.template("ACTION", "SEND_WEBHOOK"), nid, parent, 440, dy)
            act = copy.deepcopy(next(a for a in n["actions"] if a.get("type") == "SEND_WEBHOOK"))
            data = act.setdefault("data", {})
            data["url"] = step["url"]
            data["method"] = step.get("method") or "POST"
            # KHÔNG kế thừa header của webhook mẫu (có thể chứa khoá bí mật của URL khác):
            # spec không khai → mặc định tài liệu api-reference.md mục "Bot thu SĐT rồi gọi webhook OMIFlow".
            hdrs = step.get("headers")
            if hdrs is None:
                data["headers"] = copy.deepcopy(DEFAULT_WEBHOOK_HEADERS)
            else:
                data["headers"] = [{"key": h["key"], "value": h["value"]} for h in hdrs]
            data["body_json"] = step["body_json"]
            n["actions"] = [act]
            # Editor (name_mappings) của SEND_WEBHOOK chưa kiểm chứng (node-status.json): không chép mẫu editor,
            # tránh để URL/header của webhook mẫu nằm lại trong editor rồi bị UI ghi ngược khi lưu.
            self.maps[:] = [m for m in self.maps if m.get("id") != nid]
            self.put_node(n)
            self.warn.append("intent %s: SEND_WEBHOOK mới chỉ vá runtime; editor (name_mappings) của loại này chưa "
                             "kiểm chứng nên không chép mẫu → dựng/kiểm nút trên UI (URL, header, body) rồi GET lại "
                             "kiểm trước khi lưu từ UI" % key)
            self.warn.append("intent %s: ACTION không có 'Bước tiếp theo' → bot không trả lời tin đã kích hoạt; "
                             "SEND_WEBHOOK chưa chạy khi bot được giao qua OMI_BOT_AI trên kênh thật — test đúng kênh" % key)
            return nid
        if t == "start_other_campaign":
            flow = step.get("flow") or {}
            if not (flow.get("value") and flow.get("_id")):
                raise SpecError("intent %s: start_other_campaign cần flow.value (uuid) và flow._id" % key)
            n, ed = self.clone(self.template("ACTION", "START_OTHER_CAMPAIGN"), nid, parent, 440, dy)
            act = copy.deepcopy(next(a for a in n["actions"] if a.get("type") == "START_OTHER_CAMPAIGN"))
            sel = {"value": flow["value"], "_id": flow["_id"], "label": flow.get("label") or "", "isDependent": True}
            act.setdefault("datas", {})["selected"] = sel
            n["actions"] = [act]
            def set_sel(d):
                d["selected"] = copy.deepcopy(sel)
                return True
            self.patch_editor(ed, "START_OTHER_CAMPAIGN", set_sel)
            self.put_node(n)
            if ed is not None:
                self.put_map(ed)
            self.warn.append("intent %s: flow phụ thuộc phải dependent_config.is_dependent:true và đã xuất bản; "
                             "không nhận biến hội thoại" % key)
            return nid
        raise SpecError("loại bước không hỗ trợ: %s" % t)

    def patch_editor(self, ed, action_type, fn):
        if ed is None:
            self.warn.append("base không có mẫu editor (name_mappings) cho ACTION %s — runtime đã vá; "
                             "mở editor kiểm hiển thị sau khi lưu" % action_type)
            return
        for a in ed.get("actions") or []:
            if isinstance(a, dict) and a.get("type") == action_type and isinstance(a.get("datas"), dict):
                if fn(a["datas"]):
                    return
        self.warn.append("mẫu editor của ACTION %s không có datas như mong đợi — mở editor kiểm sau khi lưu" % action_type)

    def apply_intent(self, it, row):
        key = it["key"]
        desc = it["description"]
        cid = it.get("id") or self.hid(key, "case")
        aa = self.begin.setdefault("ai_analyze", {})
        rt = aa.setdefault("conditions", [])
        ed = self.begin_ed.setdefault("conditions", [])
        old_rt = next((c for c in rt if c.get("id") == cid), None)
        old_target = (old_rt or {}).get("next_node") or ""
        target = self.build_step(it["then"], key, self.begin, 0, row) if it.get("then") else ""
        new_rt = {"id": cid, "type": "CUSTOM_INTENT", "intent_code": None, "intent_name": desc, "percent": 40,
                  "next_node": target}
        new_ed = {"id": cid, "type": "CUSTOM_INTENT", "name": "", "personality": desc, "data": []}
        if old_rt is not None:
            rt[rt.index(old_rt)] = new_rt
        else:
            rt.append(new_rt)
        old_ed = next((c for c in ed if c.get("id") == cid), None)
        if old_ed is not None:
            ed[ed.index(old_ed)] = new_ed
        else:
            ed.append(new_ed)
        bid = self.begin.get("id")
        self.conns[:] = [c for c in self.conns if not (c.get("source") == bid and c.get("sourceHandle") == cid)]
        nn = self.begin.get("next_nodes") or []
        still = {c.get("next_node") for c in rt if c is not new_rt} | {
            (aa.get(k) or {}).get("next_node") for k in SYSTEM_TAIL if isinstance(aa.get(k), dict)}
        if old_target and old_target != target and old_target not in still:
            nn = [x for x in nn if x != old_target]
        if target:
            if target not in nn:
                nn.append(target)
            self.add_edge(bid, cid, target)
        self.begin["next_nodes"] = nn

    def order_system_tail(self):
        ed = self.begin_ed.get("conditions") or []
        rest = [c for c in ed if c.get("type") not in SYSTEM_TAIL]
        tail = []
        for t in SYSTEM_TAIL:
            found = [c for c in ed if c.get("type") == t]
            if not found:
                raise SpecError("base thiếu điều kiện hệ thống %s ở name_mappings BEGIN_CONTEXT" % t)
            tail.append(found[0])
        self.begin_ed["conditions"] = rest + tail
        rt = self.begin["ai_analyze"].get("conditions") or []
        self.begin["ai_analyze"]["conditions"] = ([c for c in rt if c.get("type") == "CUSTOM_INTENT"]
                                                  + [c for c in rt if c.get("type") != "CUSTOM_INTENT"])

    def apply_api_knowledge(self, items):
        aa = self.begin.setdefault("ai_analyze", {})
        ids = aa.setdefault("api_knowledge_ids", [])
        lst = self.bot.get("api_knowledge")
        if not isinstance(lst, list):
            lst = self.bot["api_knowledge"] = []
        for q in items:
            for f in ("name", "url", "method", "prompt", "query_prompt"):
                if not q.get(f):
                    raise SpecError("api_knowledge thiếu %s" % f)
            ref = q.get("ref_id") or ("request_" + slug(q["name"]))
            hdrs = q.get("headers") or []
            headers = [{"id": self.hid(ref, "h", i), "key": h.get("key", ""), "value": h.get("value", "")}
                       for i, h in enumerate(hdrs)] or [{"id": self.hid(ref, "h", 0), "key": "", "value": ""}]
            if any(str(h["key"]).lower() == "authorization" and h["value"] for h in headers):
                self.warn.append("Truy vấn %s có header Authorization tĩnh: token đổi từ apiKey hết hạn sau 24 giờ "
                                 "(Cần xác nhận cách làm mới); spec/payload chứa bí mật → để ở scratch, không đưa vào repo" % ref)
            entry = {"ref_id": ref, "name": q["name"], "url": q["url"], "method": q["method"], "headers": headers,
                     "body_type": "raw", "body_json": q.get("body_json") or "", "variables": None,
                     "prompt": q["prompt"], "query_prompt": q["query_prompt"], "param_type": "json",
                     "time_out": q.get("time_out", 60), "api_response_guide": [], "retrieve_data": None}
            old = next((i for i, a in enumerate(lst) if isinstance(a, dict) and a.get("ref_id") == ref), None)
            if old is None:
                lst.append(entry)
            else:
                lst[old] = entry
            if ref not in ids:
                ids.append(ref)

    def run(self):
        sp = self.spec
        if sp.get("system_prompt") is not None:
            self.bot["system_prompt"] = sp["system_prompt"]
        if sp.get("begin_content") is not None:
            self.begin.setdefault("ai_analyze", {})["content"] = sp["begin_content"]
        for row, it in enumerate(sp.get("intents") or []):
            self.apply_intent(it, row)
        self.order_system_tail()
        if sp.get("api_knowledge"):
            self.apply_api_knowledge(sp["api_knowledge"])
        return self.bot


def check_spec(spec):
    """Từ chối loại chưa kiểm chứng trước khi vá. Ném SpecError (exit 2)."""
    if not isinstance(spec, dict):
        raise SpecError("spec phải là JSON object")
    extra = set(spec) - TOP_KEYS
    if extra:
        raise SpecError("khoá spec không hỗ trợ: %s (cho phép: %s)" % (", ".join(sorted(extra)), ", ".join(sorted(TOP_KEYS))))

    def walk(step, key):
        if step is None:
            return
        t = str(step.get("type", "")).lower()
        if t in UI_ONLY:
            raise SpecError("intent %s: loại '%s' (%s) %s" % (key, t, UI_ONLY[t], UI_MSG))
        if t not in STEP_TYPES:
            raise SpecError("intent %s: loại bước '%s' không hỗ trợ (hỗ trợ: %s)" % (key, t, ", ".join(sorted(STEP_TYPES))))
        if t == "collect_info" and step.get("when_collected"):
            walk(step["when_collected"].get("then"), key)

    keys = set()
    for it in spec.get("intents") or []:
        key = it.get("key")
        if it.get("type") not in (None, "CUSTOM_INTENT") or it.get("intent_code") or it.get("system_intent") or it.get("intent"):
            raise SpecError("intent %s: ý định hệ thống không dùng — quy ước chỉ dùng CUSTOM_INTENT mô tả tự nhiên "
                            "(SKILL.md Gotchas 'Trường hợp trong Ngữ cảnh bắt đầu')" % key)
        if not key or not re.fullmatch(r"[a-z0-9_]+", str(key)):
            raise SpecError("intent thiếu key hoặc key không phải [a-z0-9_]: %r" % key)
        if key in keys:
            raise SpecError("intent key trùng: %s" % key)
        keys.add(key)
        if not str(it.get("description") or "").strip():
            raise SpecError("intent %s thiếu description (khi nào chọn / khi nào không chọn / câu ví dụ)" % key)
        walk(it.get("then"), key)


def load_base(path):
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and isinstance(obj.get("payload"), dict) and "campaign" not in obj:
        obj = obj["payload"]
    return obj


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Vá spec lên GET bot thật → payload save_draft_v2 (không gọi mạng).")
    ap.add_argument("spec")
    ap.add_argument("--base", required=True, help="bản GET thật của bot (payload hoặc phản hồi GET)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-validate", action="store_true", help="bỏ bước validate_bot --mode pre (chỉ dùng khi gỡ lỗi)")
    a = ap.parse_args(argv)
    sys.path.insert(0, HERE)
    import omi_bot_lib
    try:
        omi_bot_lib.guard_out_path(a.out)
    except SystemExit as e:
        return e.code
    try:
        with open(a.spec, encoding="utf-8") as f:
            spec = json.load(f)
        base = load_base(a.base)
        check_spec(spec)
        b = Builder(base, spec)
        bot = b.run()
    except SpecError as e:
        print("LỖI: %s" % e, file=sys.stderr)
        return 2
    except (OSError, ValueError) as e:
        print("LỖI đọc file: %s" % e, file=sys.stderr)
        return 2
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(bot, ensure_ascii=False, indent=1) + "\n")
    print("Đã ghi %s (_id=%s giữ nguyên, is_publish=%s không đổi)" % (a.out, bot.get("_id"), json.dumps(bot.get("is_publish"))))
    for w in b.warn:
        print("WARN build %s" % w)
    if a.no_validate:
        return 0
    p = subprocess.run([sys.executable, "-B", os.path.join(HERE, "validate_bot.py"), a.out, "--mode", "pre"],
                       capture_output=True)
    sys.stdout.write(p.stdout.decode("utf-8", "replace"))
    sys.stdout.flush()
    if p.returncode != 0:
        print("validate_bot --mode pre FAIL → sửa spec/base trước khi omi_save", file=sys.stderr)
        return 1
    print("Tiếp: python <thư mục skill>/scripts/omi_save.py bot %s --domain <domain>" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
