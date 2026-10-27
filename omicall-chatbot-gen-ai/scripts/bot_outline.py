# -*- coding: utf-8 -*-
"""In dàn ý một bot OmiBot (đọc nhanh baseline trước khi sửa). Không in token, không in giá trị header.

    python bot_outline.py --file <bot.json> [--save] [--testcases-skeleton <testcases.json>]
    python bot_outline.py --id <bot_id> --domain <domain> [--save] [--testcases-skeleton ...]

--file : bot object hoặc phản hồi GET {"payload": {...}}.
--id   : GET qua omi_bot_lib (token từ omi_session; cần mạng).
--save : ghi bản GET (đã che Authorization) và dàn ý vào OMI_SCRATCH hoặc thư mục tạm.
--testcases-skeleton : sinh khung testcases.json theo 14 nhóm G1–G14 (references/livetalk-test-optimize.md mục 4);
                       phần kỳ vọng để "Cần xác nhận" — chỉ điền từ dữ liệu của bot, không tự nghĩ đáp án.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from validate_bot import find_begin, connections, load  # noqa: E402

GROUPS = [
    ("G1", "Mở đầu"), ("G2", "FAQ (RAG)"), ("G3", "Ý định"), ("G4", "Thu thập thông tin"),
    ("G5", "Truy vấn API"), ("G6", "Ngoài dữ liệu"), ("G7", "Ngoài phạm vi"), ("G8", "Gặp nhân viên"),
    ("G9", "Khiếu nại, bực tức"), ("G10", "Dữ liệu nhạy cảm"), ("G11", "Chống dẫn dắt"), ("G12", "Nhiều lượt"),
    ("G13", "Nhiều ý một tin"), ("G14", "Kết thúc"),
]
TBD = "Cần xác nhận"


def short(s, n=90):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def outline(bot):
    camp = bot.get("campaign") or {}
    nodes = [n for n in (camp.get("nodes") or []) if isinstance(n, dict)]
    maps = [m for m in (camp.get("name_mappings") or []) if isinstance(m, dict)]
    ni, mi = find_begin(bot)
    editor = {c.get("id"): c for c in ((maps[mi].get("conditions") or []) if mi is not None else []) if isinstance(c, dict)}
    cases = []
    if ni is not None:
        aa = nodes[ni].get("ai_analyze") or {}
        for c in aa.get("conditions") or []:
            e = editor.get(c.get("id")) or {}
            desc = c.get("intent_name") or e.get("personality") or e.get("name") or c.get("name") or ""
            cases.append({"id": c.get("id"), "type": c.get("type"), "mo_ta": short(desc), "next": c.get("next_node") or ""})
        for k in ("bot_can_not_answer", "customer_not_response"):
            v = aa.get(k) or {}
            cases.append({"id": k, "type": "system", "mo_ta": "", "next": v.get("next_node") or ""})
    node_rows = []
    collect = []
    for n in nodes:
        aa = n.get("ai_analyze") or {}
        acts = [a.get("type") for a in (n.get("actions") or []) if isinstance(a, dict)]
        node_rows.append({"id": n.get("id"), "node_type": n.get("node_type"), "name": n.get("name"),
                          "actions": acts, "next_nodes": n.get("next_nodes") or []})
        for v in aa.get("collect_variables") or []:
            collect.append({"node": n.get("id"), "variable_code": v.get("variable_code"),
                            "variable_name": v.get("variable_name"), "mo_ta": short(v.get("variable_value"), 60)})
    edges = [{"source": c.get("source"), "handle": c.get("sourceHandle"), "target": c.get("target")}
             for c in connections(bot) if isinstance(c, dict)]
    ak_on = set(((nodes[ni].get("ai_analyze") or {}).get("api_knowledge_ids") or []) if ni is not None else [])
    apis = []
    for a in bot.get("api_knowledge") or []:
        a = a or {}
        apis.append({"ref_id": a.get("ref_id"), "name": a.get("name"), "method": a.get("method"),
                     "url": (a.get("url") or "").split("?")[0],
                     "header_keys": [h.get("key") for h in a.get("headers") or [] if isinstance(h, dict) and h.get("key")],
                     "bat_o_begin": a.get("ref_id") in ak_on})
    vs = bot.get("vector_store") or {}
    rag = [{"ref_id": f.get("ref_id"), "file_training_status": f.get("file_training_status"), "language": f.get("language")}
           for f in (vs.get("vector_store_files") or []) if isinstance(f, dict)]
    return {
        "_id": bot.get("_id"), "uuid_co": bool(bot.get("uuid")), "assistant_name": bot.get("assistant_name"),
        "type": bot.get("type"), "model": bot.get("model"),
        "is_draft": bot.get("is_draft"), "is_publish": bot.get("is_publish"),
        "history_config": bot.get("history_config"), "max_characters_reply": bot.get("max_characters_reply"),
        "system_prompt_len": len(bot.get("system_prompt") or ""),
        "begin_content_len": len(((nodes[ni].get("ai_analyze") or {}).get("content") or "")) if ni is not None else 0,
        "cases": cases, "nodes": node_rows, "edges": edges, "collect_vars": collect,
        "api_knowledge": apis, "rag_files": rag, "question_answer": bool(bot.get("question_answer")),
    }


def render(o):
    L = ["Bot: %s | _id=%s | %s %s | is_draft=%s is_publish=%s" % (
        o["assistant_name"], o["_id"], o["type"], o["model"], o["is_draft"], o["is_publish"])]
    L.append("system_prompt: %d ký tự | BEGIN ai_analyze.content: %d ký tự | history_config=%s | max_characters_reply=%s"
             % (o["system_prompt_len"], o["begin_content_len"], json.dumps(o["history_config"], ensure_ascii=False),
                o["max_characters_reply"]))
    L.append("Trường hợp ở Ngữ cảnh bắt đầu (%d):" % len(o["cases"]))
    for c in o["cases"]:
        L.append("  - [%s] %s %s → %s" % (c["type"], c["id"], ("“%s”" % c["mo_ta"]) if c["mo_ta"] else "", c["next"] or "(không nối)"))
    L.append("Node (%d):" % len(o["nodes"]))
    for n in o["nodes"]:
        L.append("  - %s %s%s → %s" % (n["node_type"], n["id"], (" actions=" + ",".join(map(str, n["actions"]))) if n["actions"] else "",
                                       ", ".join(map(str, n["next_nodes"])) or "-"))
    L.append("Cạnh (%d):" % len(o["edges"]))
    for e in o["edges"]:
        L.append("  - %s [%s] → %s" % (e["source"], e["handle"], e["target"]))
    L.append("Biến thu (%d):" % len(o["collect_vars"]))
    for v in o["collect_vars"]:
        L.append("  - %s (%s) ở %s: %s" % (v["variable_code"], v["variable_name"], v["node"], v["mo_ta"]))
    L.append("Truy vấn api_knowledge (%d) — header chỉ in tên khoá:" % len(o["api_knowledge"]))
    for a in o["api_knowledge"]:
        L.append("  - %s “%s” %s %s headers=%s %s" % (a["ref_id"], a["name"], a["method"], a["url"], ",".join(a["header_keys"]),
                                                    "(bật ở BEGIN)" if a["bat_o_begin"] else "(chưa bật ở BEGIN)"))
    L.append("RAG Dữ liệu khác (%d):" % len(o["rag_files"]))
    for f in o["rag_files"]:
        L.append("  - ref_id=%s %s %s" % (f["ref_id"], f["file_training_status"], f["language"]))
    L.append("question_answer: %s" % ("có" if o["question_answer"] else "rỗng"))
    return "\n".join(L)


def skeleton(o):
    intents = [c for c in o["cases"] if c["type"] == "CUSTOM_INTENT"] or [{"id": None, "mo_ta": ""}]
    out = []
    for g, name in GROUPS:
        rows = intents if g == "G3" else [None]
        for i, it in enumerate(rows, 1):
            exp = {"intent": (it["id"] if it else None) if g == "G3" else None, "action": TBD,
                   "must": [], "must_not": [], "source": TBD}
            note = "%s — %s" % (name, it["mo_ta"]) if it and it.get("mo_ta") else name
            out.append({"id": "%s-%02d" % (g, i), "group": g, "ghi_chu": note, "turns": [TBD], "expected": exp})
    return out


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="In dàn ý bot OmiBot (không in token/giá trị header).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--id")
    ap.add_argument("--domain", default=os.environ.get("OMI_DOMAIN"))
    ap.add_argument("--save", action="store_true", help="ghi bản GET (đã che) + dàn ý vào scratch")
    ap.add_argument("--out-dir")
    ap.add_argument("--testcases-skeleton", metavar="FILE")
    ap.add_argument("--json", action="store_true", help="in dàn ý dạng JSON")
    a = ap.parse_args(argv)
    import omi_bot_lib
    if a.testcases_skeleton:  # khung testcases ghi theo dữ liệu bot: không ghi vào thư mục skill hay repo
        a.testcases_skeleton = omi_bot_lib.guard_out_path(a.testcases_skeleton)
    if a.file:
        try:
            bot = load(a.file)
        except (OSError, ValueError) as e:
            print("Không đọc được %s: %s" % (a.file, e), file=sys.stderr)
            return 2
    else:
        resp = omi_bot_lib.get_bot(a.id, a.domain)
        bot = resp.get("payload") if isinstance(resp, dict) else None
        if not isinstance(bot, dict):
            print("GET không trả payload bot (status_code=%s)" % (resp or {}).get("status_code"), file=sys.stderr)
            return 1
    o = outline(bot)
    print(json.dumps(o, ensure_ascii=False, indent=1) if a.json else render(o))
    if a.save:
        bid = str(bot.get("_id") or "bot")
        p1 = omi_bot_lib.save_json(bot, "bot_%s_get.json" % bid, a.out_dir)
        p2 = omi_bot_lib.save_json(o, "bot_%s_outline.json" % bid, a.out_dir)
        print("Đã lưu (đã che Authorization): %s ; %s" % (p1, p2))
    if a.testcases_skeleton:
        with open(a.testcases_skeleton, "w", encoding="utf-8") as f:
            json.dump(skeleton(o), f, ensure_ascii=False, indent=1)
        print("Đã ghi khung testcases: %s (điền turns/expected từ dữ liệu của bot; chỗ thiếu giữ 'Cần xác nhận')"
              % a.testcases_skeleton)
    return 0


if __name__ == "__main__":
    sys.exit(main())
