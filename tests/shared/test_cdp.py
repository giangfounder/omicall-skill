"""Test cdp.py: CDP.call() không lặp vô hạn khi websocket đóng hoặc không trả lời (sửa vòng lặp cũ).

Dùng websocket giả (không mở kết nối). Thiếu websocket-client thì nạp module giả để kiểm logic call().
"""
import importlib.util
import json
import sys
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "shared" / "scripts"


class Closed(Exception):
    pass


class TimedOut(Exception):
    pass


def load_cdp():
    if importlib.util.find_spec("websocket") is None:
        fake = types.ModuleType("websocket")
        fake.WebSocketTimeoutException = TimedOut
        fake.WebSocketConnectionClosedException = Closed
        fake.create_connection = lambda *a, **k: None
        sys.modules["websocket"] = fake
    spec = importlib.util.spec_from_file_location("cdp_under_test", SCRIPTS / "cdp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cdp = load_cdp()
ws_mod = sys.modules["websocket"]
CLOSED = getattr(ws_mod, "WebSocketConnectionClosedException", Closed)


class FakeWS:
    def __init__(self, recv):
        self._recv = recv
        self.sent = []
        self.recv_calls = 0

    def send(self, s):
        self.sent.append(s)

    def settimeout(self, t):
        self.t = t

    def recv(self):
        self.recv_calls += 1
        return self._recv(self)

    def close(self):
        pass


def make(recv, timeout=1):
    c = cdp.CDP.__new__(cdp.CDP)
    c.ws = FakeWS(recv)
    c.next_id = 1
    c.timeout = timeout
    return c


class TestCdpCall(unittest.TestCase):
    def test_closed_socket_raises_fast(self):
        def recv(ws):
            raise CLOSED("closed")
        c = make(recv, timeout=30)
        t0 = time.monotonic()
        with self.assertRaises(ConnectionError):
            c.call("Runtime.evaluate", {"expression": "1"})
        self.assertLess(time.monotonic() - t0, 2)
        self.assertEqual(c.ws.recv_calls, 1)

    def test_empty_frame_means_closed(self):
        c = make(lambda ws: "", timeout=30)
        t0 = time.monotonic()
        with self.assertRaises(ConnectionError):
            c.call("Page.navigate", {"url": "about:blank"})
        self.assertLess(time.monotonic() - t0, 2)

    def test_other_error_not_swallowed(self):
        def recv(ws):
            raise OSError("broken pipe")
        c = make(recv, timeout=30)
        with self.assertRaises(OSError):
            c.call("X")
        self.assertEqual(c.ws.recv_calls, 1)

    def test_garbage_until_deadline(self):
        def recv(ws):
            time.sleep(0.01)
            return "không phải json"
        c = make(recv, timeout=0.3)
        t0 = time.monotonic()
        with self.assertRaises(TimeoutError):
            c.call("X")
        self.assertLess(time.monotonic() - t0, 2)

    def test_skips_non_json_and_other_ids(self):
        msgs = iter(["rác", json.dumps({"method": "Page.loadEventFired"}), json.dumps({"id": 99}),
                     json.dumps({"id": 1, "result": {"ok": True}})])
        c = make(lambda ws: next(msgs), timeout=5)
        self.assertEqual(c.call("X"), {"ok": True})

    def test_error_reply_raises(self):
        c = make(lambda ws: json.dumps({"id": 1, "error": {"message": "x"}}), timeout=5)
        with self.assertRaises(RuntimeError):
            c.call("X")


if __name__ == "__main__":
    unittest.main()
