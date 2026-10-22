"""Dựng payload kịch bản Callbot luồng cổ điển (type NORMAL) từ file spec JSON — dùng chung mọi dự án.

  python build_callflow.py spec_callflow.json --out payload.json [--base-id <id> --base-uuid <uuid>]

Tự động:
- Cấu trúc kép: runtime `nodes` (STAFF + từng CONDITION + ACTION + FROM_SYSTEM) và editor `org_nodes`
  (nhánh nằm trong STAFF, ô COLLECT_INFO riêng) + `connections`.
- Nhánh chung theo quy tắc mặc định (step có "common": true):
  hỏi đáp trả lời 1 lần → lần sau báo chuyển máy; khách đòi gặp nhân viên → báo chuyển; tức giận → xin lỗi kết thúc;
  lặp lại đọc lại 1 lần → lần sau báo chuyển; im lặng nhắc 1 lần → kết thúc; phản hồi sai nhắc 1 lần → báo chuyển.
- Xưng hô {{gender1_ai}} thay "anh/chị"; khai báo biến ở node + top-level + editor.
- Bố cục: cột theo đường đi dài nhất từ BEGIN, node kết thúc/chuyển máy dồn về cuối.
- Tự kiểm tra và cảnh báo lời thoại (chữ số, viết tắt, ký hiệu, "anh/chị" còn sót).
Cấu trúc spec: references/spec-callflow.example.json.
"""
import argparse
import json
import random
import re
import string
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("spec")
ap.add_argument("--out", required=True)
ap.add_argument("--base-id")
ap.add_argument("--base-uuid")
A = ap.parse_args()
S = json.load(open(A.spec, encoding="utf-8"))
random.seed(S.get("seed", 1))
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
        raise SystemExit(f"Đích '{key}' không có trong steps/actions/routes")
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
        raise SystemExit(f"Ý định {code} chưa có trong spec.intents (lấy id từ Kho tri thức)")
    return {"code": code, "label": it["name"], "name": it["name"], "isTenantIntent": True, "isSystem": bool(it.get("system_intent_id")),
            "systemIntentId": it.get("system_intent_id"), "tenantId": S["tenant_id"], "id": it["id"], "value": it["id"]}


def entity_obj(code):
    en = S["entities"].get(code)
    if not en:
        raise SystemExit(f"Thực thể {code} chưa có trong spec.entities")
    return {"isSystem": False, "code": code, "entityCode": code, "id": en["id"], "label": en["name"], "isTenantEntity": True,
            "value": en["id"], "desc": "{{" + code + "}}"}


def branches_for(st):
    """Nhánh khai báo + nhánh chung theo quy tắc mặc định."""
    br = [dict(b) for b in st.get("branches", [])]
    if not st.get("common"):
        return br, None, None
    rep = xh(st.get("reprompt", ""))
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
            raise SystemExit(f"{st['key']}: nhánh {b['intent']} có câu trả lời nhưng thiếu 'to' (kịch bản thật luôn có đích)")
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
        raise SystemExit(f"Hành động {ac['type']} chưa hỗ trợ trong builder (thêm thủ công theo api-reference)")
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
if A.base_id or A.base_uuid:
    if not (A.base_id and A.base_uuid):
        raise SystemExit("Cập nhật cần cả --base-id và --base-uuid của bản mới nhất (chỉ id sẽ sinh kịch bản trùng)")
    payload.update({"id": A.base_id, "uuid": A.base_uuid})

# ---------- tự kiểm tra ----------
ids = {n["id"] for n in nodes}
bad = [(n["id"], t) for n in nodes for t in n.get("next_nodes") or [] if t not in ids]
ret_no_next = [n["id"] for n in nodes if n["node_type"] == "CONDITION" and n.get("return_contents") and not n.get("next_nodes")]
left = len(re.findall(r"anh/chị", json.dumps(nodes, ensure_ascii=False), re.I)) if GENDER else 0
unreached = [k for k in KEYS if IDS[k] not in reach]
assert not bad, f"next_nodes trỏ node không tồn tại: {bad[:5]}"
assert not ret_no_next, f"nhánh có câu trả lời nhưng thiếu đích: {ret_no_next[:5]}"
json.dump(payload, open(A.out, "w", encoding="utf-8"), ensure_ascii=False)
print("nodes", len(nodes), dict(Counter(n["node_type"] for n in nodes)), "| org", len(org), "| connections", len(edges),
      "| bytes", len(json.dumps(payload, ensure_ascii=False).encode()))
print("còn 'anh/chị':", left, "| node không có đường vào:", unreached or "không")
for w in sorted(set(WARN)):
    print("CẢNH BÁO:", w)
