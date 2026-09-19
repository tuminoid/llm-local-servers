"""Splash ownership, immutable identity and conservative admission contracts."""

import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request


ROOT = Path(__file__).resolve().parents[1] / "splash"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load("splash_runtime", "runtime.py")
with mock.patch.dict(sys.modules, {"runtime": runtime}):
    bench = load("splash_bench", "bench.py")
with mock.patch.dict(sys.modules, {"bench": bench}):
    capability = load("splash_capability", "capability.py")


class SplashTest(unittest.TestCase):
    def test_model_config_respects_overrides_and_rejects_mutable_revision(self):
        with mock.patch.dict(os.environ, {"SPLASH_MAX_LEN": "131072"}):
            values = runtime.config("qwen3.6-35b-a3b")
        self.assertEqual(values["SPLASH_MAX_LEN"], "131072")
        with mock.patch.dict(os.environ, {"SPLASH_MODEL_REVISION": "main"}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                runtime.config("qwen3.6-35b-a3b")
        with self.assertRaises(ValueError):
            runtime.config("../vllm/models/qwen3.8-27b")

    def test_wrong_revision_rejected_before_package_verification(self):
        values = runtime.config("qwen3.8-27b")
        upstream = mock.Mock()
        upstream._snapshot_revision.return_value = "0" * 40
        with mock.patch.object(runtime, "upstream_models", return_value=upstream):
            with self.assertRaisesRegex(RuntimeError, "revision differs"):
                runtime.verify_model(values)
        upstream.verify_artifacts.assert_not_called()

    def test_bind_requires_auth_and_does_not_put_key_in_arguments(self):
        values = runtime.config("qwen3.6-35b-a3b")
        with mock.patch.dict(os.environ, {"SPLASH_HOST": "0.0.0.0", "SPLASH_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "requires SPLASH_API_KEY"):
                runtime.command(values)
            os.environ["SPLASH_API_KEY"] = "test-secret"
            self.assertNotIn("test-secret", " ".join(runtime.command(values)))

    def test_authorization_is_origin_scoped_and_not_redirected(self):
        handler = runtime.Authorization("http://127.0.0.1:8022", "test-secret")
        request = urllib.request.Request("http://127.0.0.1:8022/v1/chat/completions")
        handler.http_request(request)
        self.assertEqual(request.unredirected_hdrs["Authorization"], "Bearer test-secret")
        self.assertNotIn("Authorization", request.headers)
        for url in ("http://127.0.0.1:8023/", "https://127.0.0.1:8022/"):
            other = urllib.request.Request(url)
            handler.http_request(other)
            self.assertFalse(other.has_header("Authorization"))

    def test_occupied_port_refused(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            with self.assertRaises(OSError):
                runtime.port_free("127.0.0.1", listener.getsockname()[1])

    def test_stop_refuses_reused_pid_and_retains_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile = Path(directory) / "server.json"
            pidfile.write_text(json.dumps({"pid": 123, "started": "original"}))
            processes = {123: {"group": 123, "started": "replacement"}}
            with mock.patch.object(runtime, "PIDFILE", pidfile), \
                    mock.patch.object(runtime, "processes", return_value=processes), \
                    mock.patch.object(runtime.os, "killpg") as kill:
                with self.assertRaisesRegex(RuntimeError, "reused"):
                    runtime.stop()
                kill.assert_not_called()
                self.assertTrue(pidfile.exists())

    def test_failed_registration_closes_start_gate_and_reaps_child(self):
        values = runtime.config("qwen3.6-35b-a3b")
        process = mock.Mock(pid=123, stdin=io.BytesIO())
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            with mock.patch.object(runtime, "STATE", state), \
                    mock.patch.object(runtime, "PIDFILE", state / "server.json"), \
                    mock.patch.object(runtime, "LOG", state / "server.log"), \
                    mock.patch.object(runtime, "port_free"), \
                    mock.patch.object(runtime, "verify_release"), \
                    mock.patch.object(runtime, "verify_model"), \
                    mock.patch.object(runtime, "processes", return_value={123: {"started": "original"}}), \
                    mock.patch.object(runtime, "save", side_effect=OSError("disk full")), \
                    mock.patch.object(runtime.subprocess, "Popen", return_value=process):
                with self.assertRaisesRegex(OSError, "disk full"):
                    runtime.start("qwen3.6-35b-a3b", values)
                self.assertTrue(process.stdin.closed)
                process.wait.assert_called_once_with(timeout=10)

    def test_foreground_child_requires_parent_start_gate(self):
        with mock.patch.object(sys, "argv", ["runtime.py", "serve", "qwen3.6-35b-a3b"]), \
                mock.patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(b""))):
            with self.assertRaisesRegex(RuntimeError, "internal"):
                runtime.main()

    def test_stop_retains_state_if_port_was_not_released(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile = Path(directory) / "server.json"
            pidfile.write_text(json.dumps({"pid": 123, "host": "127.0.0.1", "port": 8022}))
            with mock.patch.object(runtime, "PIDFILE", pidfile), \
                    mock.patch.object(runtime, "owned_group", return_value={}), \
                    mock.patch.object(runtime, "group_alive", return_value=False), \
                    mock.patch.object(runtime, "port_free", side_effect=OSError("in use")):
                with self.assertRaises(OSError):
                    runtime.stop()
                self.assertTrue(pidfile.exists())

    def test_stop_checks_ownership_before_signal_and_waits_only_for_group_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile, log = Path(directory) / "server.json", Path(directory) / "server.log"
            pidfile.write_text(json.dumps({"pid": 123, "host": "127.0.0.1", "port": 8022}))
            log.write_text("server log")
            with mock.patch.object(runtime, "PIDFILE", pidfile), \
                    mock.patch.object(runtime, "LOG", log), \
                    mock.patch.object(runtime, "owned_group", return_value={123: {}}) as owned, \
                    mock.patch.object(runtime, "group_alive", side_effect=[True, False, False]), \
                    mock.patch.object(runtime, "port_free"), \
                    mock.patch.object(runtime.os, "killpg") as kill, \
                    mock.patch.object(runtime.time, "sleep"):
                runtime.stop()
                owned.assert_called_once()
                kill.assert_called_once_with(123, runtime.signal.SIGTERM)
                self.assertFalse(pidfile.exists())
                self.assertFalse(log.exists())

    def test_shutdown_waits_for_zombie_without_mistaking_it_for_foreign_process(self):
        owner = {"pid": 123, "started": "original",
                 "command": ["python", "-u", "/runtime/server.py", "--binary", "/runtime/splash"]}
        processes = {123: {"group": 123, "started": "original", "state": "Z",
                           "command": "<defunct>"}}
        with mock.patch.object(runtime, "processes", return_value=processes):
            self.assertEqual(runtime.owned_group(owner), processes)
            processes[123].update(state="S", command="unrelated server")
            with self.assertRaisesRegex(RuntimeError, "unrecognized"):
                runtime.owned_group(owner)

    def test_sparse_virtual_kv_cannot_overstate_physical_admission(self):
        # Four cells need 400 B. The remaining 624 B fit three 200 B
        # extents, regardless of the much larger virtual address space.
        status = {"maximum_context_tokens": 64, "memory_plan": {
            "valid": True, "budget": {
                "deficit_bytes": 0, "maximum_batch_width": 4,
                "dynamic_budget_bytes": 1024, "active_state_cell_bytes": 100,
                "kv_extent_pages": 2, "kv_page_bytes": 100,
                "kv_page_tokens": 32, "kv_virtual_tokens": 100000,
            },
        }}
        with mock.patch.dict(os.environ, {"AUDIT_BENCH_ACTIVE_SLOTS": "", "AUDIT_BENCH_KV_TOKENS": ""}):
            self.assertEqual(bench.capacity(status), (4, 192))
            os.environ["AUDIT_BENCH_KV_TOKENS"] = "193"
            with self.assertRaisesRegex(ValueError, "live capacity"):
                bench.capacity(status)
            os.environ["AUDIT_BENCH_KV_TOKENS"] = ""
            status["memory_plan"]["budget"]["dynamic_budget_bytes"] = 100
            with self.assertRaisesRegex(RuntimeError, "cannot admit"):
                bench.capacity(status)

    def test_thinking_control_uses_splash_wire_contract(self):
        self.assertEqual(capability.control("reasoning-effort-none"), {"reasoning_effort": "none"})
        with self.assertRaises(ValueError):
            capability.control("enable-thinking-false")


if __name__ == "__main__":
    unittest.main()
