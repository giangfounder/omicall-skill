"""Dựng payload kịch bản Callbot luồng cổ điển (type NORMAL) từ file spec JSON — dùng chung mọi dự án.

  python build_callflow.py spec_callflow.json --out payload.json --context tenant_context.json
         [--allow-pending] [--base-id <id> --base-uuid <uuid>]

Tự động:
- Kiểm spec trước khi dựng (validate_spec): 'next' và 'branches' loại trừ nhau; STAFF có nhánh phải có im lặng (NR)
  + phản hồi sai (RW) qua "common": true hoặc nr_to/wrong_to; routes[].var phải khai báo; key trong layout,
  đích ('to', 'next'...) và mã ý định/thực thể phải tồn tại. Lỗi → in danh sách, exit 1, không ghi file.
- --context: điền tenant_id, id/system_intent_id/name ý định theo mã, id thực thể theo mã, nhân viên chuyển máy
  theo ext/email từ tenant_context.json (khảo sát tenant). Mã dùng trong spec mà context không có → exit 1.
  Kho tri thức đọc ở khối `kho_tri_thuc` (khuôn tenant_survey.py: intents, entity_types); khối cũ `callbot_kb` vẫn đọc.
  system_intent_id: context có thì dùng, không có thì giữ giá trị spec; ý định is_system=true mà cả hai đều thiếu → exit 1.
- Payload còn chuỗi placeholder '<...>' → exit 1 (nêu số lượng). --allow-pending cho phép dựng trước khi nhập
  Kho tri thức (id ý định/thực thể chưa có), in CẢNH BÁO; payload đó KHÔNG được lưu lên tenant.
- Cấu trúc kép: runtime `nodes` (STAFF + từng CONDITION + ACTION + FROM_SYSTEM) và editor `org_nodes`
  (nhánh nằm trong STAFF, ô COLLECT_INFO riêng) + `connections`.
- Nhánh chung theo quy tắc mặc định (step có "common": true):
  hỏi đáp trả lời 1 lần → lần sau báo chuyển máy; khách đòi gặp nhân viên → báo chuyển; tức giận → xin lỗi kết thúc;
  lặp lại đọc lại 1 lần → lần sau báo chuyển; im lặng nhắc 1 lần → kết thúc; phản hồi sai nhắc 1 lần → báo chuyển.
- Xưng hô {{gender1_ai}} thay "anh/chị"; khai báo biến ở node + top-level + editor.
- Bố cục: cột theo đường đi dài nhất từ BEGIN, node kết thúc/chuyển máy dồn về cuối.
- Id node: seed mặc định tính theo tên kịch bản (hai kịch bản khác tên không trùng id); spec để "seed" cố định → CẢNH BÁO.
- Tự kiểm tra và cảnh báo lời thoại (chữ số, viết tắt, ký hiệu, "anh/chị" còn sót).
Cấu trúc spec: references/spec-callflow.example.json. Kiểm payload/bản GET: scripts/verify_callflow.py.
"""
import argparse
import hashlib
import json
import random
import re
import string
import sys
from collections import Counter

PLACEHOLDER = re.compile(r"<[^<>\n]{1,80}>")
SUPPORTED_ACTIONS = ("ADD_CLASSIFY", "TRANSFER_CALL", "PUSH_NOTIFICATION")


class SpecError(Exception):
    """Lỗi spec/context: in thông báo rõ, không traceback."""


def is_ph(v):
    return isinstance(v, str) and bool(PLACEHOLDER.fullmatch(v.strip()))


def default_seed(name):
    return int(hashlib.sha256((name or "").encode("utf-8")).hexdigest()[:16], 16)


# ---------- kiểm spec ----------
def validate_spec(S):
    """Trả (errors, warnings). Không sửa spec."""
    errs, warns = [], []
    steps = S.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["spec thiếu 'steps' (mảng khác rỗng)"], warns
    for f in ("name", "tenant_id"):
        if not S.get(f):
            errs.append(f"spec thiếu '{f}'")
    keys = []
    for i, st in enumerate(steps):
        if not st.get("key"):
            errs.append(f"steps[{i}] thiếu 'key'")
        if not st.get("text"):
            errs.append(f"steps[{i}] ({st.get('key')}) thiếu 'text'")
        keys.append(st.get("key"))
    for grp in ("actions", "routes"):
        for i, x in enumerate(S.get(grp, [])):
            if not x.get("key"):
                errs.append(f"{grp}[{i}] thiếu 'key'")
            keys.append(x.get("key"))
    dup = [k for k, n in Counter(keys).items() if k and n > 1]
    if dup:
        errs.append(f"key bị trùng: {dup}")
    kset = set(k for k in keys if k)

    def need_key(where, k):
        if k is not None and k not in kset:
            errs.append(f"{where}: đích '{k}' không có trong steps/actions/routes")

    intents, entities = S.get("intents", {}), S.get("entities", {})

    def need_intent(where, code):
        if code not in intents:
            errs.append(f"{where}: ý định '{code}' chưa có trong spec.intents")

    def need_entity(where, code):
        if code not in entities:
            errs.append(f"{where}: thực thể '{code}' chưa có trong spec.entities")

    C = S.get("common", {})
    FAQ = S.get("faq", {})
    need_key("start", S.get("start", steps[0].get("key")))
    any_common = any(st.get("common") for st in steps)
    any_faq = any(st.get("common") and st.get("faq", True) for st in steps) and FAQ.get("answers")
    if any_common:
        if not C.get("transfer_step"):
            errs.append("có step 'common': true nhưng common.transfer_step chưa khai báo")
        need_key("common.transfer_step", C.get("transfer_step"))
        if C.get("angry_intent"):
            need_intent("common.angry_intent", C["angry_intent"])
            if not C.get("angry_step"):
                errs.append("common.angry_intent có nhưng thiếu common.angry_step")
            need_key("common.angry_step", C.get("angry_step"))
        if C.get("repeat_intent"):
            need_intent("common.repeat_intent", C["repeat_intent"])
        for ic in C.get("transfer_intents", []):
            need_intent("common.transfer_intents", ic)
        if any(st.get("common") and not st.get("nr_to") for st in steps):
            if not C.get("no_response_end"):
                errs.append("có step 'common': true không khai nr_to nhưng common.no_response_end chưa khai báo")
            need_key("common.no_response_end", C.get("no_response_end"))
    if any_faq:
        if not FAQ.get("question_intent"):
            errs.append("faq.answers có nhưng thiếu faq.question_intent")
        else:
            need_intent("faq.question_intent", FAQ["question_intent"])
        for ec in FAQ.get("answers", {}):
            need_entity("faq.answers", ec)
    for st in steps:
        k = st.get("key")
        br = st.get("branches") or []
        if st.get("next") and (br or st.get("common")):
            errs.append(f"step {k}: có cả 'next' lẫn 'branches'/'common' — 'next' sẽ ghi đè các nhánh; chọn MỘT "
                        f"(bước chờ khách trả lời dùng branches, bước nói xong đi tiếp dùng next)")
        need_key(f"step {k}.next", st.get("next"))
        if st.get("end") and (br or st.get("next") or st.get("common")):
            errs.append(f"step {k}: 'end': true nhưng vẫn có branches/next/common")
        if br and not st.get("common"):
            if not st.get("nr_to"):
                errs.append(f"step {k}: có branches, 'common' không bật nhưng thiếu nr_to (nhánh im lặng "
                            f"CUSTOMER_NOT_RESPONSE bắt buộc — checklist C3)")
            if not st.get("wrong_to"):
                errs.append(f"step {k}: có branches, 'common' không bật nhưng thiếu wrong_to (nhánh phản hồi sai "
                            f"CUSTOMER_RESPONSE_WRONG bắt buộc — checklist C3)")
        need_key(f"step {k}.nr_to", st.get("nr_to"))
        need_key(f"step {k}.wrong_to", st.get("wrong_to"))
        for j, b in enumerate(br):
            where = f"step {k}.branches[{j}]"
            if not b.get("intent"):
                errs.append(f"{where}: thiếu 'intent'")
            else:
                need_intent(where, b["intent"])
            if b.get("entity"):
                need_entity(where, b["entity"])
            if b.get("say") and not b.get("to"):
                errs.append(f"{where}: có câu trả lời ('say') nhưng thiếu 'to' (kịch bản thật luôn có đích)")
            need_key(where, b.get("to"))
    camp = set(S.get("campaign_vars", [])) | {c.get("code") for c in S.get("collect", [])} | set(S.get("contact_vars", []))
    for i, ro in enumerate(S.get("routes", [])):
        where = f"routes[{i}] ({ro.get('key')})"
        if ro.get("var") not in camp:
            errs.append(f"{where}: var '{ro.get('var')}' không có trong campaign_vars/collect/contact_vars")
        if not ro.get("cases"):
            errs.append(f"{where}: thiếu 'cases'")
        for j, case in enumerate(ro.get("cases", [])):
            if not case.get("values"):
                errs.append(f"{where}.cases[{j}]: thiếu 'values'")
            if case.get("operator", "EQUAL") != "EQUAL":
                warns.append(f"{where}.cases[{j}]: toán tử {case['operator']} chưa kiểm chứng (node-status: enum) — GET lại và soát trên editor")
            need_key(f"{where}.cases[{j}]", case.get("to"))
        need_key(f"{where}.else", ro.get("else"))
    for i, ac in enumerate(S.get("actions", [])):
        where = f"actions[{i}] ({ac.get('key')})"
        t = ac.get("type")
        if t not in SUPPORTED_ACTIONS:
            errs.append(f"{where}: hành động '{t}' chưa hỗ trợ trong builder (hỗ trợ: {', '.join(SUPPORTED_ACTIONS)}); "
                        f"loại khác dựng trên UI rồi GET lại")
        if t == "ADD_CLASSIFY" and not ac.get("label"):
            errs.append(f"{where}: ADD_CLASSIFY thiếu 'label'")
        if t == "TRANSFER_CALL":
            ag = S.get("agent") or {}
            if not ag.get("ext") and not ag.get("email"):
                errs.append(f"{where}: TRANSFER_CALL cần spec.agent có 'ext' hoặc 'email'")
        if t == "PUSH_NOTIFICATION":
            for f in ("title", "content", "contact_ids"):
                if not ac.get(f):
                    errs.append(f"{where}: PUSH_NOTIFICATION thiếu '{f}'")
            warns.append(f"{where}: PUSH_NOTIFICATION — dữ liệu editor (org) chưa kiểm chứng, soát trên editor sau khi lưu")
        need_key(f"{where}.next", ac.get("next"))
    lay = S.get("layout", {})
    for col in ("last_column", "final_column"):
        for k in lay.get(col, []):
            if k not in kset:
                errs.append(f"layout.{col}: key '{k}' không có trong steps/actions/routes")
    if "seed" in S:
        warns.append("spec để 'seed' cố định — các kịch bản dùng cùng seed sẽ trùng id node; bỏ 'seed' để tính theo tên kịch bản")
    return errs, warns


# ---------- context (tenant_context.json) ----------
def _as_map(v):
    if isinstance(v, dict):
        return {k: (x if isinstance(x, dict) else {}) for k, x in v.items()}
    out = {}
    for x in v or []:
        if isinstance(x, dict) and x.get("code"):
            out[x["code"]] = x
    return out


def _real(v):
    return v if (v not in (None, "") and not is_ph(v)) else None


def _merge_maps(*maps):
    """Gộp các map mã → bản ghi; bản sau bổ sung/ghi đè trường có giá trị, không xoá trường đã có bằng None/""."""
    out = {}
    for m in maps:
        for code, x in m.items():
            cur = out.setdefault(code, {})
            cur.update({k: v for k, v in x.items() if v not in (None, "") or k not in cur})
    return out


def load_context(path):
    """Đọc tenant_context.json. Kho tri thức nằm ở khối `kho_tri_thuc` (khuôn tenant_survey.py: intents,
    entity_types); khối cũ `callbot_kb` (intents, entities) và top-level intents/entities vẫn đọc, có cả thì gộp theo mã."""
    try:
        ctx = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"không đọc được context {path}: {e}")
    if not isinstance(ctx, dict):
        raise SpecError(f"context {path} không phải object JSON")
    new = ctx.get("kho_tri_thuc") if isinstance(ctx.get("kho_tri_thuc"), dict) else {}
    kb = ctx.get("callbot_kb") if isinstance(ctx.get("callbot_kb"), dict) else {}
    tenant = ctx.get("tenant") or {}
    conflicts = []
    # khối cũ callbot_kb trước, kho_tri_thuc (khảo sát mới) sau -> khảo sát mới thắng; id lệch thì CẢNH BÁO
    old_i, new_i = _as_map(kb.get("intents") or ctx.get("intents")), _as_map(new.get("intents"))
    old_e = _as_map(kb.get("entities") or kb.get("entity_types") or ctx.get("entities"))
    new_e = _as_map(new.get("entity_types") or new.get("entities"))
    for label, o, n in (("ý định", old_i, new_i), ("thực thể", old_e, new_e)):
        for code in sorted(set(o) & set(n)):
            if _real(o[code].get("id")) and _real(n[code].get("id")) and o[code]["id"] != n[code]["id"]:
                conflicts.append(f"context: {label} '{code}' có id khác nhau giữa callbot_kb và kho_tri_thuc — dùng "
                                 "kho_tri_thuc (khảo sát mới); xoá khối cũ nếu đã lỗi thời")
    return {
        "tenant_id": _real(tenant.get("tenant_id")) or _real(ctx.get("tenant_id")),
        "intents": _merge_maps(old_i, new_i),
        "entities": _merge_maps(old_e, new_e),
        "agents": [a for a in ctx.get("agents") or [] if isinstance(a, dict)],
        "conflicts": conflicts,
    }


def _agent_field(a, *names):
    for n in names:
        if _real(a.get(n)):
            return str(a[n])
    return None


def used_codes(S):
    ints, ents = set(), set()
    C, FAQ = S.get("common", {}), S.get("faq", {})
    for st in S["steps"]:
        for b in st.get("branches") or []:
            ints.add(b.get("intent"))
            if b.get("entity"):
                ents.add(b["entity"])
        if st.get("common"):
            ints.update(C.get("transfer_intents", []))
            for k in ("angry_intent", "repeat_intent"):
                if C.get(k):
                    ints.add(C[k])
            if st.get("faq", True) and FAQ.get("answers"):
                ints.add(FAQ.get("question_intent"))
                ents.update(FAQ["answers"])
    return ints - {None}, ents


def apply_context(S, ctx, allow_pending, warns):
    """Điền id thật từ context vào spec (bản sao). Mã thiếu → lỗi (hoặc CẢNH BÁO khi --allow-pending)."""
    errs = []
    S = json.loads(json.dumps(S))
    warns.extend(ctx.get("conflicts") or [])
    if ctx["tenant_id"]:
        if _real(S.get("tenant_id")) and S["tenant_id"] != ctx["tenant_id"]:
            warns.append("tenant_id trong spec khác context — dùng giá trị của context")
        S["tenant_id"] = ctx["tenant_id"]
    ints, ents = used_codes(S)
    for code in sorted(ints):
        c = ctx["intents"].get(code)
        if not c or not _real(c.get("id")):
            (warns if allow_pending else errs).append(f"ý định '{code}' không có trong context (Kho tri thức) — nhập dữ liệu huấn luyện rồi khảo sát lại")
            continue
        it = S["intents"].setdefault(code, {})
        it["id"] = c["id"]
        if _real(c.get("name")):
            it["name"] = c["name"]
        sid_ctx, sid_spec = _real(c.get("system_intent_id")), _real(it.get("system_intent_id"))
        if sid_ctx:
            if sid_spec and sid_spec != sid_ctx:
                warns.append(f"ý định '{code}': system_intent_id trong spec ({sid_spec}) khác context ({sid_ctx}) — dùng giá trị của context")
            it["system_intent_id"] = sid_ctx
        elif c.get("is_system") is True and not sid_spec:
            (warns if allow_pending else errs).append(
                f"ý định hệ thống '{code}' thiếu system_intent_id (cả context lẫn spec) — lấy từ intent/list-by-tenant; "
                "để trống thì editor nhận systemIntentId null")
        elif c.get("is_system") is True:
            warns.append(f"ý định hệ thống '{code}': context không có system_intent_id — giữ giá trị trong spec ({sid_spec}), "
                         "Cần xác nhận với intent/list-by-tenant")
        elif c.get("is_system") is None and not sid_spec and str(code).startswith("omi_intent_"):
            warns.append(f"ý định '{code}': context không ghi is_system và không có system_intent_id (spec lẫn context) — "
                         "mã omi_intent_* thường là ý định hệ thống: Cần xác nhận system_intent_id (intent/list-by-tenant)")
        elif c.get("is_system") is False and sid_spec:
            warns.append(f"ý định '{code}': context ghi is_system=false nhưng spec có system_intent_id ({sid_spec}) — giữ giá trị spec, Cần xác nhận")
        if not sid_ctx:
            it["system_intent_id"] = sid_spec  # placeholder '<...>' trong spec → None (ý định của tenant)
    for code in sorted(ents):
        c = ctx["entities"].get(code)
        if not c or not _real(c.get("id")):
            (warns if allow_pending else errs).append(f"thực thể '{code}' không có trong context (Kho tri thức)")
            continue
        en = S["entities"].setdefault(code, {})
        en["id"] = c["id"]
        if _real(c.get("name")):
            en["name"] = c["name"]
    if any(a.get("type") == "TRANSFER_CALL" for a in S.get("actions", [])):
        ag = S.get("agent") or {}
        ext, email = _real(ag.get("ext")), _real(ag.get("email"))
        hit = [a for a in ctx["agents"]
               if (ext and _agent_field(a, "ext", "sip_number", "sipNumber", "extension", "sip_user") == str(ext))
               or (email and (_agent_field(a, "email") or "").lower() == email.lower())]
        if len(hit) != 1:
            errs.append(f"nhân viên chuyển máy (ext={ext}, email={email}): tìm thấy {len(hit)} bản ghi trong context.agents — cần đúng 1")
        else:
            a = hit[0]
            aid = _agent_field(a, "agent_id", "id")
            if not aid:
                errs.append("context.agents: bản ghi khớp chỉ có '_id' (chưa rõ là agent_id hay contact_id) — Cần xác nhận; "
                            "điền 'agent_id' rõ ràng (MCP list_agents)")
            else:
                ag.update({"id": aid, "contact_id": _agent_field(a, "contact_id", "contactId") or ag.get("contact_id", ""),
                           "name": _agent_field(a, "full_name", "fullName", "name") or ag.get("name"),
                           "ext": _agent_field(a, "ext", "sip_number", "sipNumber", "extension", "sip_user") or ext,
                           "email": _agent_field(a, "email") or ag.get("email", "")})
                S["agent"] = ag
    return S, errs


def find_placeholders(obj):
    cnt = Counter()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(k)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            cnt.update(PLACEHOLDER.findall(o))
    walk(obj)
    return cnt


def build(S, base_id=None, base_uuid=None):
    """Dựng payload từ spec đã kiểm. Trả (payload, nodes, report_lines, warnings)."""
    random.seed(S["seed"] if "seed" in S else default_seed(S.get("name")))
    GENDER = S.get("use_gender_var", True)
    COMMON = {"no_response_text": "Dạ {{gender1_ai}} còn nghe em nói không ạ?",
              "wrong_prefix": "Dạ em chưa nghe rõ ý {{gender1_ai}}. ", **S.get("common", {})}
    FAQ = S.get("faq", {})
    G_ORG = {"attributeType": "CONTACT", "showTooltip": "c_config/ai.genderAiTip", "label": [["gender1"], " (?)"],
             "value": "gender1_ai", "desc": "{{gender1_ai}}"}
    WARN = []


    def nid():
        return "".join(random.choices(string.ascii_letters + string.digits, k=10))


    def xh(t):
        return re.sub(r"anh/chị", "{{gender1_ai}}", t, flags=re.IGNORECASE) if GENDER and t else t


    ALL_VARS = (["gender1_ai"] if GENDER else []) + S.get("campaign_vars", []) + [c["code"] for c in S.get("collect", [])]


    def used_vars(*texts):
        found = []
        for t in texts:
            for v in re.findall(r"\{\{(\w+)\}\}", t or ""):
                if v not in found:
                    found.append(v)
                if v not in ALL_VARS and v not in S.get("contact_vars", []):
                    WARN.append(f"biến {{{{{v}}}}} chưa khai báo (campaign_vars/collect/contact_vars)")
        return found


    def rt_vars(vs):
        return [{"field_name": "", "field_code": v, "field_value": "", "field_type": "", "type": "OTHER", "is_dynamic_attribute": False} for v in vs]


    def check_tts(where, t):
        if not t:
            return
        plain = re.sub(r"\{\{\w+\}\}", "", t)
        if re.search(r"\d", plain):
            WARN.append(f"{where}: còn chữ số — viết số bằng chữ: {plain[:60]}")
        if re.search(r"\b[A-ZĐ]{2,}\b", plain):
            WARN.append(f"{where}: có chữ in hoa/viết tắt: {plain[:60]}")
        if re.search(r"[/*#()\[\]<>]", plain):
            WARN.append(f"{where}: có ký hiệu: {plain[:60]}")


    IDS = {}
    KEYS = [st["key"] for st in S["steps"]] + [a["key"] for a in S.get("actions", [])] + [r["key"] for r in S.get("routes", [])]
    for k in ["__BEGIN__"] + KEYS:
        IDS[k] = nid()
    nodes, org, edges = [], [], []
    # id hệ thống (dùng chung mọi tenant) của thực thể hệ thống — editor COLLECT_INFO cần làm "value"
    SYSTEM_ENTITY = {
        "omi_entity_datetime": ("634d6c3042d14f7ec2df05e4", "Thời gian ngày tháng"), "omi_entity_name": ("634d6c3042d14f7ec2df05e3", "Tên, họ tên"),
        "omi_entity_age": ("634d6c3042d14f7ec2df05e2", "Tuổi"), "omi_entity_duration": ("634d6c3042d14f7ec2df05e5", "Khoảng thời gian bao lâu"),
        "omi_entity_address": ("634d6c3042d14f7ec2df05e6", "Địa chỉ nhà công ty"), "omi_entity_phone": ("634d6c3042d14f7ec2df05e7", "Số điện thoại"),
        "omi_entity_email": ("634d6c3042d14f7ec2df05e8", "Email"), "omi_entity_number": ("635607554a4e5504b6731deb", "Số, chữ số"),
        "omi_entity_money": ("6356073f4a4e5504b6731dea", "Số tiền"), "omi_entity_person_id": ("635607794a4e5504b6731dec", "Số định danh cá nhân"),
    }
    COLLECT_CFG = S.get("collect", [])
    for c in COLLECT_CFG:
        if c.get("entity") in SYSTEM_ENTITY:
            c.setdefault("entity_system_id", SYSTEM_ENTITY[c["entity"]][0])
            c.setdefault("entity_label", SYSTEM_ENTITY[c["entity"]][1])
    COLLECT_RT = [({"entity_type_code": c["entity"], "variable_code": c["code"], "variable_name": c["name"]} if c.get("entity")
                   else {"variable_code": c["code"], "variable_name": c["name"], "option": "ENTIRE_USER_SENTENCE"}) for c in COLLECT_CFG]
    COLLECT_ORG = [({"entityCode": c["entity"], "variableName": c["name"], "variableCode": c["code"], "label": c.get("entity_label", c["entity"]),
                     "value": c.get("entity_system_id", "")} if c.get("entity") else
                    {"variableName": c["name"], "variableCode": c["code"], "keyIcon": "communicate", "label": "c_config/ai.allCustomersSay",
                     "value": "ENTIRE_USER_SENTENCE"}) for c in COLLECT_CFG]


    def target(key):
        if key not in IDS:
            raise SpecError(f"Đích '{key}' không có trong steps/actions/routes")
        return IDS[key]


    def edge(src, handle, tgt, extra=None, color="#1e3150", animated=False):
        e = {"sourceHandle": handle, "animated": animated, "style": {"strokeWidth": 3, "stroke": color},
             "id": f"reactflow__edge-{src}{handle}-{tgt}1", "source": src, "type": "custom", "targetHandle": "1", "target": tgt}
        if extra:
            e.update(extra)
        edges.append(e)


    def intent_obj(code):
        it = S["intents"].get(code)
        if not it:
            raise SpecError(f"Ý định {code} chưa có trong spec.intents (lấy id từ Kho tri thức)")
        return {"code": code, "label": it["name"], "name": it["name"], "isTenantIntent": True, "isSystem": bool(it.get("system_intent_id")),
                "systemIntentId": it.get("system_intent_id"), "tenantId": S["tenant_id"], "id": it["id"], "value": it["id"]}


    def entity_obj(code):
        en = S["entities"].get(code)
        if not en:
            raise SpecError(f"Thực thể {code} chưa có trong spec.entities")
        return {"isSystem": False, "code": code, "entityCode": code, "id": en["id"], "label": en["name"], "isTenantEntity": True,
                "value": en["id"], "desc": "{{" + code + "}}"}


    def branches_for(st):
        """Nhánh khai báo + nhánh chung theo quy tắc mặc định."""
        br = [dict(b) for b in st.get("branches", [])]
        rep = xh(st.get("reprompt", ""))
        if not st.get("common"):
            # bước tự khai nhánh: NR/RW lấy câu mặc định, đích theo nr_to/wrong_to (validate_spec bắt buộc khi có branches)
            nr = (xh(COMMON["no_response_text"]), st["nr_to"]) if st.get("nr_to") else None
            wrong = (xh(COMMON["wrong_prefix"]) + rep, st["wrong_to"]) if st.get("wrong_to") else None
            return br, nr, wrong
        tstep = COMMON["transfer_step"]
        if st.get("faq", True):
            for ecode, ans in FAQ.get("answers", {}).items():
                br.append({"intent": FAQ["question_intent"], "entity": ecode, "say": (xh(ans) + " " + rep).strip(), "to": tstep})
        for ic in COMMON.get("transfer_intents", []):
            br.append({"intent": ic, "to": tstep})
        if COMMON.get("angry_intent"):
            br.append({"intent": COMMON["angry_intent"], "to": COMMON["angry_step"]})
        if COMMON.get("repeat_intent"):
            br.append({"intent": COMMON["repeat_intent"], "say": xh(st["text"]), "to": tstep})
        nr = (xh(COMMON["no_response_text"]), st.get("nr_to", COMMON["no_response_end"]))
        wrong = (xh(COMMON["wrong_prefix"]) + rep, st.get("wrong_to", tstep))
        return br, nr, wrong


    def build_staff(st):
        sid = IDS[st["key"]]
        text = xh(st["text"])
        check_tts(st["key"], text)
        br, nr, wrong = branches_for(st)
        rt_next, org_conds, collapse = [], [], {"NEXT_STEP": {"isCollapse": False}}
        for b in br:
            say, to = xh(b.get("say")), b.get("to")
            if say and not to:
                raise SpecError(f"{st['key']}: nhánh {b['intent']} có câu trả lời nhưng thiếu 'to' (kịch bản thật luôn có đích)")
            check_tts(f"{st['key']}/{b['intent']}", say)
            cid = nid()
            rc = {"id": cid, "node_type": "CONDITION", "intent_code": b["intent"], "condition_type": "INTENT",
                  "return_contents": [{"type": "TEXT", "content": say}] if say else [], "variables": rt_vars(used_vars(say)),
                  "return_template_contents": [], "is_collapse": False}
            if b.get("entity"):
                rc["entity_code"] = b["entity"]
            if to:
                rc["next_nodes"] = [target(to)]
                edge(sid, cid, target(to))
            nodes.append(rc)
            rt_next.append(cid)
            oc = {"isErrorAudio": False, "keywords": [], "returnContents": [{"type": "text", "content": say}] if say else [], "entities": [],
                  "id": cid, "type": "INTENT", "intent": intent_obj(b["intent"]),
                  "repeat": {"label": ["times", {"t": "l", "n": 0}], "value": "1"} if say else {"label": "notRepeat", "value": "0"}}
            if b.get("entity"):
                oc["responseWrongCollectionInfo"] = entity_obj(b["entity"])
                oc["applyEntity"] = True
            org_conds.append(oc)
            collapse[cid] = {"isCollapsible": True, "isCollapse": False}
        for kind, spec in (("CUSTOMER_NOT_RESPONSE", nr), ("CUSTOMER_RESPONSE_WRONG", wrong)):
            if not spec:
                continue
            say, to = spec
            cid = nid()
            rc = {"id": cid, "node_type": "CONDITION", "condition_type": kind, "return_contents": [{"type": "TEXT", "content": say}],
                  "variables": rt_vars(used_vars(say)), "return_template_contents": [], "is_collapse": False, "next_nodes": [target(to)]}
            if kind == "CUSTOMER_NOT_RESPONSE":
                rc["customer_not_response_delay"] = 10000
                oc = {"isErrorAudio": False, "conditionId": cid, "returnContents": [{"type": "text", "content": say}],
                      "repeat": {"label": ["times", {"t": "l", "n": 0}], "value": "1"}, "id": kind, "type": kind, "customerNotResponseDelay": 10000}
            else:
                oc = {"isErrorAudio": False, "conditionId": cid, "returnContents": [{"type": "text", "content": say}],
                      "repeat": 0, "id": kind, "type": kind, "textSayRespWrong": ""}
            edge(sid, kind, target(to), {"conditionId": cid}, "#fea220")
            nodes.append(rc)
            rt_next.append(cid)
            org_conds.append(oc)
            collapse[kind] = {"isCollapse": False}
        vs = used_vars(text)
        rn = {"id": sid, "node_type": "STAFF", "name": st.get("name", st["key"]), "template_content": text, "return_template_content": "",
              "wrong_response_content": "", "customer_response_delay": 10000, "variables": rt_vars(vs), "is_collapse": False, "speed": 1}
        if st.get("next"):
            rt_next = [target(st["next"])]
            edge(sid, "2", target(st["next"]))
        if rt_next:
            rn["next_nodes"] = rt_next
        data = {"variables": [{"variable": v, "selected": G_ORG if v == "gender1_ai" else {}} for v in vs],
                "objVariables": {v: ([["gender1"], " (?)"] if v == "gender1_ai" else "") for v in vs},
                "notResponseTime": 10000, "responseTime": 10000, "count": 1, "collectionInfo": [], "type": "STAFF", "content": text,
                "subContent": text, "speed": {"label": "speedRead.normal", "value": 1}, "collapseObj": collapse, "oldIdIem": {},
                "audio_file": None, "typeSay": "text", "activeIdx": 0, "id": sid, "name": st.get("name", st["key"]), "isCallBot": True,
                "dataRpNumStep": [], "conditions": org_conds}
        if st.get("collect"):
            coll_cid = nid()
            rn["actions"] = [{"id": nid(), "type": "COLLECT_INFO", "data": {"variables": COLLECT_RT}}]
            data["collectionInfo"] = COLLECT_ORG
            data["objVariables"].update({c["variableCode"]: c["variableName"] for c in COLLECT_ORG})
            data["conditions"].insert(0, {"conditionId": coll_cid, "id": "COLLECT_INFO", "type": "COLLECT_INFO"})
            collapse["COLLECT_INFO"] = {"isCollapsible": True, "isCollapse": False}
            org.append({"data": {"variables": [], "objVariables": {c["variableCode"]: c["variableName"] for c in COLLECT_ORG},
                                 "collectionInfo": COLLECT_ORG, "count": 1, "type": "COLLECT_INFO", "collapseObj": {"NEXT_STEP": {"isCollapse": False}}},
                        "width": 332, "id": sid + "COLLECT_INFO", "position": {"x": "0", "y": "0"}, "type": "COLLECT_INFO", "height": 240})
            edge(sid, "COLLECT_INFO", sid + "COLLECT_INFO", {"conditionId": coll_cid}, "#6c63ff", True)
        nodes.append(rn)
        org.append({"data": data, "width": 332, "id": sid, "position": {"x": "0", "y": "0"}, "type": "STAFF", "height": 120 + 90 * len(org_conds)})


    def build_action(ac):
        aid, key = nid(), ac["key"]
        rn = {"id": IDS[key], "node_type": "ACTION", "variables": [], "is_collapse": False}
        if ac["type"] == "ADD_CLASSIFY":
            if ac["label"] not in S.get("classifies", []):
                WARN.append(f"nhãn '{ac['label']}' chưa có trong classifies")
            rn["actions"] = [{"id": aid, "type": "ADD_CLASSIFY", "data": {"ids": [ac["label"]]}}]
            act = {"datas": {"ids": [ac["label"]]}, "id": aid, "type": "ADD_CLASSIFY"}
            org_acts, org_datas, name = [act], [act], ac.get("name", "Phân loại: " + ac["label"])
        elif ac["type"] == "TRANSFER_CALL":
            ag = S["agent"]
            rn["actions"] = [{"id": aid, "type": "TRANSFER_CALL", "data": {"actionType": "Extension", "transfer_customize_info": False,
                                                                            "sip_number": ag["ext"], "ids": [ag["id"]], "transfer_collected_info": True}}]
            cust = [{"fieldName": "", "contentVar": "", "id": nid(), "key": ""}]
            sel = {"sipNumber": ag["ext"], "gender": "male", "fullName": ag["name"], "avatar": "", "label": f"{ag['ext']} - {ag['name']}",
                   "contact_id": ag.get("contact_id", ""), "value": ag["id"], "email": ag.get("email", "")}
            org_acts = [{"datas": {"actionType": "Extension", "customizeInfo": cust, "isTransferCollectedInfo": True,
                                   "isTransferCustomizeInfo": False, "selected": ag["id"]}, "id": aid, "type": "TRANSFER_CALL"}]
            org_datas = [{"datas": {"transferType": "Extension", "customizeInfo": cust, "isTransferCustomizeInfo": False,
                                    "isTransferCollectedInfo": True, "type": "TRANSFER_CALL", "selected": sel}, "type": "TRANSFER_CALL"}]
            name = ac.get("name", f"Chuyển máy {ag['ext']}")
        elif ac["type"] == "PUSH_NOTIFICATION":
            data = {"title": ac["title"], "content": ac["content"], "agent_contact_ids": ac["contact_ids"], "agent_contact_group_ids": [],
                    "enable_platforms": ["web"], "send_to_agent_contact": True, "send_to_agent_contact_make_call": False,
                    "send_to_agent_in_session": False, "send_to_ticket_assignee": False, "send_to_user_owner_of_contact": False,
                    "send_to_agent_contact_receive_conversation": False, "sound_noti_config": None}
            rn["actions"] = [{"id": aid, "type": "PUSH_NOTIFICATION", "data": data}]
            org_acts = org_datas = [{"datas": data, "id": aid, "type": "PUSH_NOTIFICATION"}]
            name = ac.get("name", "Thông báo nhân viên")
        else:
            raise SpecError(f"Hành động {ac['type']} chưa hỗ trợ trong builder (thêm thủ công theo api-reference)")
        if ac.get("next"):
            rn["next_nodes"] = [target(ac["next"])]
            edge(IDS[key], "2", target(ac["next"]))
        nodes.append(rn)
        org.append({"data": {"variables": [], "oldIdIem": {}, "count": 1, "name": name, "description": "", "id": IDS[key], "type": "ACTION",
                             "actions": org_acts, "content": "", "collapseObj": {"NEXT_STEP": {"isCollapsible": True, "isCollapse": False}}},
                    "width": 332, "id": IDS[key], "position": {"x": "0", "y": "0"}, "type": "ACTION", "orgDatas": org_datas, "height": 205})


    def build_route(ro):
        key = ro["key"]
        rt_conds, org_conds, org_datas, collapse = [], [], [], {"NEXT_STEP": {"isCollapsible": True, "isCollapse": False}}
        for case in ro["cases"]:
            cid, fc = nid(), nid()
            vals = [{"end_value": "", "start_value": v} for v in case["values"]]
            cmp = {"pos": None, "is_dynamic_field": False, "values": vals, "target_type": "CUSTOM_COMPARE", "field_code": fc,
                   "operator": case.get("operator", "EQUAL"), "content": "{{" + ro["var"] + "}}", "operator_type": "OR"}
            rt_conds.append({"id": cid, "name": case["name"], "type": None, "operator_type": "AND",
                             "data": [{"type": "COMPARE", "compare_conditions": [cmp]}], "data_random": None,
                             "next_nodes": [target(case["to"])], "allocation": None, "iteration_config": None, "execute_for_exist": False})
            org_conds.append({"data": [{"compare_conditions": [cmp], "type": "COMPARE"}], "name": case["name"],
                              "next_nodes": [target(case["to"])], "id": cid, "operator_type": "AND"})
            org_datas.append({"datas": [{"isComparison": True, "fieldCode": fc, "values": vals, "count": 1, "targetType": "CUSTOM_COMPARE",
                                         "label": "custom", "value": "custom", "content": "{{" + ro["var"] + "}}",
                                         "operator": {"EQUAL": "=", "NOT_EQUAL": "!=", "GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}.get(case.get("operator", "EQUAL"), "="),
                                         "operator_type": "OR"}], "id": cid, "operatorType": "AND"})
            collapse[cid] = {"isCollapsible": True, "isCollapse": False}
            edge(IDS[key], cid, target(case["to"]))
        rn = {"id": IDS[key], "node_type": "CONDITION", "condition_type": "FROM_SYSTEM", "conditions": rt_conds, "variables": [], "is_collapse": False}
        if ro.get("else"):
            rn["next_nodes"] = [target(ro["else"])]
            edge(IDS[key], "2", target(ro["else"]))
        nodes.append(rn)
        org.append({"data": {"variables": [], "description": ro.get("name", ""), "stepNode": 0, "type": "CONDITION", "content": "",
                             "collapseObj": collapse, "actionType": "CONDITION", "oldIdIem": {}, "name": ro.get("name", key), "id": IDS[key],
                             "isCallBot": True, "dataRpNumStep": [], "conditions": org_conds},
                    "width": 332, "id": IDS[key], "position": {"x": "0", "y": "0"}, "type": "CONDITION", "orgDatas": org_datas,
                    "height": 120 + 60 * len(rt_conds)})


    # ---------- dựng ----------
    start = S.get("start", S["steps"][0]["key"])
    nodes.append({"id": IDS["__BEGIN__"], "node_type": "BEGIN", "next_nodes": [target(start)], "is_collapse": False})
    org.append({"data": {"type": "BEGIN", "collapseObj": {"NEXT_STEP": {"isCollapse": False}}}, "width": 332, "id": IDS["__BEGIN__"],
                "position": {"x": "0", "y": "0"}, "type": "BEGIN", "height": 120})
    edge(IDS["__BEGIN__"], "1", target(start), color="#00B1FF")
    for st in S["steps"]:
        build_staff(st)
    for ac in S.get("actions", []):
        build_action(ac)
    for ro in S.get("routes", []):
        build_route(ro)

    # ---------- bố cục: cột = đường đi dài nhất từ BEGIN ----------
    main = [o for o in org if o["type"] != "COLLECT_INFO"]
    out, inn = {o["id"]: set() for o in main}, {o["id"]: set() for o in main}
    for e in edges:
        if e["sourceHandle"] != "COLLECT_INFO" and e["source"] in out and e["target"] in inn and e["source"] != e["target"]:
            out[e["source"]].add(e["target"])
            inn[e["target"]].add(e["source"])
    # bỏ cạnh quay vòng (DFS), rồi đường đi dài nhất theo thứ tự topo
    back, state, order = set(), {}, []


    def dfs(u):
        state[u] = 1
        for v in sorted(out[u]):
            if state.get(v) == 1:
                back.add((u, v))
            elif v not in state:
                dfs(v)
        state[u] = 2
        order.append(u)


    dfs(IDS["__BEGIN__"])
    reach = set(state)
    lvl = {u: 0 for u in reach}
    for u in reversed(order):
        for v in out[u]:
            if (u, v) not in back:
                lvl[v] = max(lvl[v], lvl[u] + 1)
    for o in main:
        lvl.setdefault(o["id"], 1)
    maxl = max(lvl.values())
    lay = S.get("layout", {})
    for k in lay.get("last_column", []):
        lvl[IDS[k]] = maxl - 1 if lay.get("final_column") else maxl
    for k in lay.get("final_column", []):
        lvl[IDS[k]] = maxl
    H = {o["id"]: o["height"] for o in org}
    pos, GAP, COLW = {}, 120, lay.get("column_width", 850)
    for l in range(max(lvl.values()) + 1):
        col = [o for o in main if lvl[o["id"]] == l]
        if not col:
            continue
        def bc(o):
            ps = [p for p in inn[o["id"]] if p in pos]
            return sum(pos[p][1] + H[p] / 2 for p in ps) / len(ps) if ps else 0
        col.sort(key=bc)
        y = -(sum(H[o["id"]] for o in col) + GAP * (len(col) - 1)) / 2
        for o in col:
            pos[o["id"]] = (l * COLW, round(y))
            y += H[o["id"]] + GAP
    for o in org:
        x, y = pos[o["id"]] if o["type"] != "COLLECT_INFO" else (pos[o["id"][:-12]][0] + 380, pos[o["id"][:-12]][1])
        o["position"] = {"x": str(x), "y": str(y)}
        if "data" in o and o["type"] != "COLLECT_INFO":
            o["data"]["pos"] = {"x": str(x), "y": str(y), "h": o["height"]}

    # ---------- payload ----------
    variables = []
    if GENDER:
        variables.append({"field_name": "Anh/Chị", "field_code": "gender1_ai", "field_value": "", "field_type": "", "type": "CONTACT", "is_dynamic_attribute": True})
    variables += [{"field_name": v, "field_code": v, "field_value": "", "field_type": "", "type": "", "is_dynamic_attribute": True} for v in S.get("campaign_vars", [])]
    variables += [{"field_name": c["name"], "field_code": c["code"], "field_value": "", "field_type": "", "type": "COLLECT_INFO", "is_dynamic_attribute": True} for c in COLLECT_CFG]
    payload = {
        "tenant_id": S["tenant_id"], "name": S["name"], "type": "NORMAL", "variables": variables,
        "collect_info_variables": [{k: v for k, v in c.items() if k != "option"} for c in COLLECT_RT],
        "connections": edges, "nodes": nodes, "org_nodes": org, "is_draft": False, "collect_authentication_data": "NONE",
        "system_intent_ids": [], "system_entity_type_ids": [],
        "layouts": [{"field_code": c["code"], "field_name": c["name"], "view_option": "ONLY_VALUE", "index": i + 1} for i, c in enumerate(COLLECT_CFG)],
        "is_publish": False, "custom_variables": [], "classifies": [{"name": c} for c in S.get("classifies", [])], "variables_with_order": [],
        "variable_list": {"contact": [], "ticket": []}, "speed": S.get("speed", 1.0), "voice": S.get("voice", "northern_female_ngocanh"),
        "is_interrupt": False, "parse_datetime": False,
    }
    if base_id or base_uuid:
        if not (base_id and base_uuid):
            raise SpecError("Cập nhật cần cả --base-id và --base-uuid của bản mới nhất (chỉ id sẽ sinh kịch bản trùng)")
        payload.update({"id": base_id, "uuid": base_uuid})

    # ---------- tự kiểm tra ----------
    ids = {n["id"] for n in nodes}
    bad = [(n["id"], t) for n in nodes for t in n.get("next_nodes") or [] if t not in ids]
    ret_no_next = [n["id"] for n in nodes if n["node_type"] == "CONDITION" and n.get("return_contents") and not n.get("next_nodes")]
    left = len(re.findall(r"anh/chị", json.dumps(nodes, ensure_ascii=False), re.I)) if GENDER else 0
    unreached = [k for k in KEYS if IDS[k] not in reach]
    if bad:
        raise SpecError(f"next_nodes trỏ node không tồn tại: {bad[:5]}")
    if ret_no_next:
        raise SpecError(f"nhánh có câu trả lời nhưng thiếu đích: {ret_no_next[:5]}")
    report = [
        " ".join(map(str, ["nodes", len(nodes), dict(Counter(n["node_type"] for n in nodes)), "| org", len(org),
                           "| connections", len(edges), "| bytes", len(json.dumps(payload, ensure_ascii=False).encode())])),
        f"còn 'anh/chị': {left} | node không có đường vào: {unreached or 'không'}",
    ]
    return payload, report, sorted(set(WARN))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dựng payload kịch bản Callbot NORMAL từ spec JSON.")
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--context", help="tenant_context.json (khảo sát tenant): điền tenant_id, id ý định/thực thể, nhân viên")
    ap.add_argument("--allow-pending", action="store_true",
                    help="cho phép còn placeholder '<...>' (dựng trước khi nhập Kho tri thức); payload này KHÔNG được lưu")
    ap.add_argument("--base-id")
    ap.add_argument("--base-uuid")
    A = ap.parse_args(argv)
    try:
        try:
            S = json.load(open(A.spec, encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SpecError(f"không đọc được spec {A.spec}: {e}")
        errs, warns = validate_spec(S)
        if errs:
            raise SpecError("spec không hợp lệ:\n" + "\n".join("  - " + e for e in errs))
        if A.context:
            S, cerrs = apply_context(S, load_context(A.context), A.allow_pending, warns)
            if cerrs:
                raise SpecError("context không đủ:\n" + "\n".join("  - " + e for e in cerrs))
        payload, report, bwarn = build(S, A.base_id, A.base_uuid)
        ph = find_placeholders(payload)
        if ph:
            total = sum(ph.values())
            top = ", ".join(f"'{k}' x{v}" for k, v in ph.most_common(6))
            msg = f"payload còn {total} placeholder ({top})"
            if not A.allow_pending:
                hint = "" if A.context else " — chạy kèm --context tenant_context.json"
                raise SpecError(msg + hint + " (hoặc --allow-pending nếu Kho tri thức chưa nhập; payload đó không được lưu)")
            warns.append(msg + " — --allow-pending: CHƯA được lưu lên tenant, dựng lại với --context sau khi nhập Kho tri thức")
    except SpecError as e:
        print("LỖI:", e, file=sys.stderr)
        return 1
    with open(A.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    for line in report:
        print(line)
    for w in sorted(set(warns)) + bwarn:
        print("CẢNH BÁO:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
