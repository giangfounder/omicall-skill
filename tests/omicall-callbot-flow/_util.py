"""Tiện ích chung cho test omicall-callbot-flow (offline, không gọi mạng).

Fixture lấy từ chính references/ của skill (spec-callflow.example.json, spec-training.example.json) và context.json
giả trong thư mục này: chỉ chứng minh nhất quán nội bộ giữa builder, validator và tài liệu, KHÔNG chứng minh hợp lệ
với nền tảng OMI.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SKILL = ROOT / "omicall-callbot-flow"
SCRIPTS = SKILL / "scripts"
REFS = SKILL / "references"
CONTEXT = HERE / "context.json"
SPEC_FLOW = REFS / "spec-callflow.example.json"
SPEC_TRAIN = REFS / "spec-training.example.json"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return str(p)


def run(script, *args, home=None, env_extra=None):
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "NO_NETWORK": "1", "PYTHONIOENCODING": "utf-8"})
    if home:
        env.update({"HOME": str(home), "USERPROFILE": str(home)})
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *map(str, args)], capture_output=True,
                       env=env, encoding="utf-8", errors="replace", timeout=300)
    return p.returncode, p.stdout, p.stderr


def survey_context(training_status="SUCCESS"):
    """Context theo khuôn tenant_survey.py / tenant_context.template.json: khối `kho_tri_thuc` (intents không có
    system_intent_id, entity_types, training_history) — chuyển từ context.json giả, không phải dữ liệu thật."""
    c = load(CONTEXT)
    kb = c.pop("callbot_kb")
    c["kho_tri_thuc"] = {
        "intents": [{k: i[k] for k in ("id", "code", "name", "is_system")} for i in kb["intents"]],
        "entity_types": [{k: e[k] for k in ("id", "code", "name", "entity_data_types")} for e in kb["entities"]],
        "training_history": [{"status": training_status, "total_trainings": 1, "created_date": 2},
                             {"status": "FAILED", "total_trainings": 1, "created_date": 1}],
    }
    return c


def tmpdir(testcase):
    d = tempfile.TemporaryDirectory()
    testcase.addCleanup(d.cleanup)
    return Path(d.name)
