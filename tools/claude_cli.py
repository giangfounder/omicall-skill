"""Gọi `claude -p` an toàn cho bộ đánh giá (eval) của repo skill OMI.

An toàn mặc định:
  - `--strict-mcp-config` + cấu hình MCP rỗng: không server OMICall nào được nạp, eval không thể ghi lên tenant.
  - `--tools <danh sách>`: chỉ các công cụ được liệt kê (eval kích hoạt chỉ cần `Skill`).
  - cwd là thư mục tạm có `.claude/` rỗng: không nạp CLAUDE.md hay hook của dự án đang làm.
  - `OMI_SUBAGENT=1`: self_update.py bỏ qua git/mạng nếu lỡ chạy.
Tìm `claude`: tham số --claude, biến CLAUDE_BIN, PATH, rồi bản kèm ứng dụng desktop (%LOCALAPPDATA%/Claude-Data/*/claude-code/*/*/claude.exe, bản mới nhất).
"""
import glob
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

EMPTY_MCP = json.dumps({"mcpServers": {}})


def _ver_key(p):
    parts = Path(p).parts
    for x in reversed(parts):
        if x[:1].isdigit() and "." in x:
            return tuple(int(n) if n.isdigit() else 0 for n in x.split("."))
    return (0,)


def find_claude(explicit=None):
    for c in (explicit, os.environ.get("CLAUDE_BIN")):
        if c and Path(c).is_file():
            return str(c)
    w = shutil.which("claude")
    if w:
        return w
    base = os.environ.get("LOCALAPPDATA")
    if base:
        hits = glob.glob(os.path.join(base, "Claude-Data", "*", "claude-code", "*", "*", "claude.exe"))
        if hits:
            return max(hits, key=_ver_key)
    return None


HOST_ENV_PREFIXES = ("CLAUDE_CODE_", "CLAUDE_AGENT_SDK_", "ANTHROPIC_BASE_URL")
HOST_ENV_NAMES = {"CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT", "USE_LOCAL_OAUTH", "USE_STAGING_OAUTH"}


def clean_env():
    """Bỏ biến môi trường của phiên Claude đang chạy (desktop/SDK) để `claude -p` con dùng đăng nhập riêng của CLI.
    Giữ ANTHROPIC_API_KEY nếu user tự đặt. Lỗi 'Credit balance is too low' = CLI đang đăng nhập bằng tài khoản API
    hết credit: chạy `claude` rồi `/login` bằng gói Claude, hoặc nạp credit."""
    env = {k: v for k, v in os.environ.items() if not (k.startswith(HOST_ENV_PREFIXES) or k in HOST_ENV_NAMES)}
    env["OMI_SUBAGENT"] = "1"
    return env


def sandbox_dir(prefix="omi_eval_"):
    d = Path(tempfile.mkdtemp(prefix=prefix))
    (d / ".claude").mkdir()
    return d


def run_stream(claude, prompt, model=None, tools=("Skill",), cwd=None, timeout=120, stop=None, extra_args=()):
    """Chạy một lượt `claude -p`, đọc stream-json từng dòng.

    stop(event) -> True thì dừng sớm (kill tiến trình). Trả về dict:
      events (list), stopped_early (bool), timed_out (bool), result (event 'result' nếu có), returncode.
    """
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--strict-mcp-config", "--mcp-config", EMPTY_MCP, "--no-session-persistence",
           "--tools", ",".join(tools)]
    if model:
        cmd += ["--model", model]
    cmd += list(extra_args)
    env = clean_env()
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace")
    out = {"events": [], "stopped_early": False, "timed_out": False, "result": None, "returncode": None}
    timer = threading.Timer(timeout, lambda: (out.__setitem__("timed_out", True), proc.kill()))
    timer.start()
    t0 = time.time()
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            out["events"].append(ev)
            if ev.get("type") == "result":
                out["result"] = ev
            if stop and stop(ev):
                out["stopped_early"] = True
                proc.kill()
                break
    finally:
        timer.cancel()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        out["returncode"] = proc.returncode
        out["stderr"] = (proc.stderr.read() if proc.stderr else "")[-2000:]
        out["seconds"] = round(time.time() - t0, 1)
    return out


def tool_uses(ev):
    """Các khối tool_use trong một event assistant."""
    if ev.get("type") != "assistant":
        return []
    content = (ev.get("message") or {}).get("content") or []
    return [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]


def skill_name_of(tu):
    """Tên skill trong lời gọi công cụ Skill (bỏ tiền tố plugin:)."""
    if tu.get("name") != "Skill":
        return None
    inp = tu.get("input") or {}
    n = inp.get("skill") or inp.get("command") or inp.get("name") or ""
    n = n.lstrip("/").split(":")[-1].strip()
    return n or None
