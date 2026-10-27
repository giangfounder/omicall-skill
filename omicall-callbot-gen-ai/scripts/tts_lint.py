# -*- coding: utf-8 -*-
"""Kiểm lời thoại cho giọng đọc tiếng Việt của kịch bản SmartAgent (AI_AGENT).

Quét các câu khách nghe theo references/voice-rules.md:
- start_call_instruction (runtime BEGIN và org BEGIN startCallInstruction);
- END_CALL description (runtime) và data.content / data.description (org);
- content của intent (runtime data[].content, editor data[].content);
- instruction: chỉ bắt cụm "anh hoặc chị" không nằm trong câu cấm
  (khối mẫu XƯNG HÔ bắt buộc có câu "Tuyệt đối không nói anh hoặc chị").

Lỗi bắt được: chữ số, ký hiệu, chữ viết tắt in hoa, cụm "anh hoặc chị".
Biến {{var}} được bỏ qua; "anh/chị" là cách gọi hợp lệ (voice-rules.md).

Dùng như module:  from tts_lint import lint_script, lint_text
Dùng như lệnh:    python tts_lint.py <file.json>      (exit 1 khi có lỗi)
                  python tts_lint.py --text "câu cần kiểm"
"""
import argparse
import json
import re
import sys

VAR_RE = re.compile(r"\{\{\s*[\w.]+\s*\}\}")
ANH_CHI_RE = re.compile(r"\banh\s*/\s*chị\b", re.IGNORECASE)
ANH_HOAC_CHI_RE = re.compile(r"anh\s+hoặc\s+chị", re.IGNORECASE)
DIGIT_RE = re.compile(r"\d")
SYMBOL_RE = re.compile(r"[/*#()\[\]<>{}@%&+=_~|\\^$→←••]")
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
NEGATION_RE = re.compile(r"(không|đừng|cấm|chớ)\b[^.\n]{0,40}$", re.IGNORECASE)


def _snippet(text, start, width=30):
    a = max(0, start - width)
    b = min(len(text), start + width)
    return text[a:b].replace("\n", " ")


def lint_text(text, where, check_symbols=True, check_digits=True, check_abbrev=True):
    """Trả về list dict {where, kind, pos, snippet, msg}. Không ném lỗi với text rỗng."""
    issues = []
    if not isinstance(text, str) or not text.strip():
        return issues
    plain = VAR_RE.sub(lambda m: " " * len(m.group(0)), text)
    for m in ANH_HOAC_CHI_RE.finditer(plain):
        issues.append({"where": where, "kind": "anh_hoac_chi", "pos": m.start(),
                       "snippet": _snippet(plain, m.start()),
                       "msg": "có cụm 'anh hoặc chị' (voice-rules.md: dùng 'anh/chị' hoặc chỉ 'anh'/'chị')"})
    if check_digits:
        m = DIGIT_RE.search(plain)
        if m:
            issues.append({"where": where, "kind": "chu_so", "pos": m.start(),
                           "snippet": _snippet(plain, m.start()),
                           "msg": "còn chữ số, phải viết số bằng chữ"})
    if check_symbols:
        no_ac = ANH_CHI_RE.sub(lambda m: " " * len(m.group(0)), plain)
        m = SYMBOL_RE.search(no_ac)
        if m:
            issues.append({"where": where, "kind": "ky_hieu", "pos": m.start(),
                           "snippet": _snippet(plain, m.start()),
                           "msg": "có ký hiệu '%s' trong câu khách nghe" % m.group(0)})
    if check_abbrev:
        for m in WORD_RE.finditer(plain):
            w = m.group(0)
            if len(w) >= 2 and w.isupper():
                issues.append({"where": where, "kind": "viet_tat", "pos": m.start(),
                               "snippet": _snippet(plain, m.start()),
                               "msg": "có chữ in hoa hoặc viết tắt '%s'" % w})
                break
    return issues


def lint_instruction(text, where):
    """Prompt hệ thống: chỉ bắt 'anh hoặc chị' không nằm sau từ phủ định trong cùng câu."""
    issues = []
    if not isinstance(text, str):
        return issues
    for m in ANH_HOAC_CHI_RE.finditer(text):
        before = text[max(0, m.start() - 60):m.start()]
        if NEGATION_RE.search(before):
            continue
        issues.append({"where": where, "kind": "anh_hoac_chi", "pos": m.start(),
                       "snippet": _snippet(text, m.start()),
                       "msg": "prompt dùng 'anh hoặc chị' ngoài câu cấm (voice-rules.md)"})
    return issues


def _unwrap(obj):
    if isinstance(obj, dict) and "nodes" not in obj and isinstance(obj.get("payload"), dict):
        return obj["payload"]
    return obj


def lint_script(script):
    """Quét toàn bộ câu khách nghe trong một script (GET hoặc payload)."""
    script = _unwrap(script)
    issues = []
    for i, n in enumerate(script.get("nodes") or []):
        if not isinstance(n, dict):
            continue
        nt = n.get("node_type")
        base = "nodes[%d]" % i
        if nt == "BEGIN":
            cfg = n.get("ai_agent_config") or {}
            issues += lint_text(cfg.get("start_call_instruction"), base + ".ai_agent_config.start_call_instruction")
            issues += lint_instruction(cfg.get("instruction"), base + ".ai_agent_config.instruction")
            conds = ((cfg.get("ai_analyze") or {}).get("conditions")) or []
            for j, c in enumerate(conds):
                if not isinstance(c, dict) or c.get("type") != "CUSTOM_INTENT":
                    continue
                for k, d in enumerate(c.get("data") or []):
                    if isinstance(d, dict):
                        issues += lint_text(d.get("content"), "%s.ai_agent_config.ai_analyze.conditions[%d].data[%d].content" % (base, j, k))
        elif nt == "END_CALL":
            issues += lint_text(n.get("description"), base + ".description")
    for i, o in enumerate(script.get("org_nodes") or []):
        if not isinstance(o, dict):
            continue
        data = o.get("data") or {}
        t = data.get("type") or o.get("type")
        base = "org_nodes[%d].data" % i
        if t == "BEGIN":
            issues += lint_text(data.get("startCallInstruction"), base + ".startCallInstruction")
            issues += lint_instruction(data.get("personality"), base + ".personality")
            for j, c in enumerate(data.get("conditions") or []):
                if not isinstance(c, dict) or c.get("type") != "CUSTOM_INTENT":
                    continue
                for k, d in enumerate(c.get("data") or []):
                    if isinstance(d, dict):
                        issues += lint_text(d.get("content"), "%s.conditions[%d].data[%d].content" % (base, j, k))
        elif t == "END_CALL":
            issues += lint_text(data.get("content"), base + ".content")
            issues += lint_text(data.get("description"), base + ".description")
    return issues


def utf8_stdout():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    utf8_stdout()
    ap = argparse.ArgumentParser(description="Kiểm lời thoại cho giọng đọc tiếng Việt (SmartAgent).")
    ap.add_argument("file", nargs="?", help="script JSON (GET hoặc payload)")
    ap.add_argument("--text", help="kiểm một câu thay cho file")
    a = ap.parse_args(argv)
    if not a.file and a.text is None:
        ap.print_usage(sys.stderr)
        print("Cần <file.json> hoặc --text", file=sys.stderr)
        return 2
    if a.text is not None:
        issues = lint_text(a.text, "--text")
    else:
        try:
            with open(a.file, encoding="utf-8") as f:
                script = json.load(f)
        except (OSError, ValueError) as e:
            print("Không đọc được %s: %s" % (a.file, e), file=sys.stderr)
            return 2
        issues = lint_script(script)
    for it in issues:
        print("FAIL X9 %s: %s | ...%s... [%s]" % (it["kind"], it["msg"], it["snippet"], it["where"]))
    print("RESULT %s" % ("FAIL" if issues else "PASS"))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
