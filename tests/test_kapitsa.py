"""Kapitsa ownership, immutable identity and admission contracts."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1] / "kapitsa"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load("kapitsa_runtime", "runtime.py")
with mock.patch.dict(sys.modules, {"runtime": runtime}):
    bench = load("kapitsa_bench", "bench.py")


class KapitsaTest(unittest.TestCase):
    def test_model_config_rejects_mutable_revision_and_ambiguous_source(self):
        with mock.patch.dict(os.environ, {"KAPITSA_MODEL_REVISION": "main"}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                runtime.config("qwen3.8-27b")
        with mock.patch.dict(os.environ, {"KAPITSA_CONVERTER": "convert_clover.py"}):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                runtime.config("qwen3.8-27b")
        with mock.patch.dict(os.environ, {"KAPITSA_COMPANIONS": "dflash2=incoai/x@main"}):
            with self.assertRaisesRegex(ValueError, "kind"):
                runtime.config("qwen3.6-35b-a3b")
        with mock.patch.dict(os.environ, {"KAPITSA_ENGINE_ENV": "HOME=/tmp"}):
            with self.assertRaisesRegex(ValueError, "NI_"):
                runtime.config("clover-35b-a3b")
        with self.assertRaises(ValueError):
            runtime.config("../splash/models/qwen3.8-27b")

    def test_engine_environment_owns_home_and_drops_ambient_switches(self):
        values = runtime.config("clover-35b-a3b")
        with mock.patch.dict(os.environ, {"NI_CLOVER_ACCEPT": "exact", "KAPITSA_HOME": "/elsewhere"}):
            environment = runtime.engine_environment(values)
        self.assertEqual(environment["KAPITSA_HOME"], str(runtime.ENGINE_HOME))
        self.assertEqual(environment["KAPITSA_NO_AUTO_UPDATE"], "1")
        self.assertEqual(environment["NI_CLOVER_DECODE"], "spec")
        self.assertNotIn("NI_CLOVER_ACCEPT", environment)

    def test_command_binds_loopback_privately_and_serves_the_view(self):
        values = runtime.config("clover-35b-a3b")
        argv = runtime.command("clover-35b-a3b", values)
        self.assertIn("--private", argv)
        self.assertNotIn("--host", argv)
        self.assertEqual(argv[argv.index("--model") + 1], str(runtime.MODELS / "clover-35b-a3b-262144"))
        qwen = runtime.config("qwen3.6-35b-a3b")
        self.assertEqual(runtime.command("qwen3.6-35b-a3b", qwen)[3], "qwen3.6-35b-a3b:4bit")

    def test_pulled_catalog_model_must_match_configured_revisions(self):
        values = runtime.config("qwen3.6-35b-a3b")
        with tempfile.TemporaryDirectory() as directory:
            models = Path(directory)
            pack = models / "qwen3.6-35b-a3b-4bit"
            (pack / ".kapitsa").mkdir(parents=True)
            (pack / "model.safetensors").write_bytes(b"weights")
            manifest = {"repo": values["KAPITSA_MODEL_REPO"], "revision": "0" * 40,
                        "files": [{"path": "model.safetensors", "size": 7}],
                        "companions": [{"kind": "dflash2", "repo": "incoai/Qwen3.6-35B-A3B-DFlash2",
                                        "revision": "51ef7b6923ad6c14cb1bb41c37a9041446496ab6",
                                        "files": []}]}
            (pack / ".kapitsa/manifest.json").write_text(json.dumps(manifest))
            with mock.patch.object(runtime, "MODELS", models):
                with self.assertRaisesRegex(RuntimeError, "differs from the config"):
                    runtime.verify_model("qwen3.6-35b-a3b", values)
                manifest["revision"] = values["KAPITSA_MODEL_REVISION"]
                manifest["files"][0]["sha256"] = "0" * 64
                (pack / ".kapitsa/manifest.json").write_text(json.dumps(manifest))
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    runtime.verify_model("qwen3.6-35b-a3b", values)
                del manifest["files"][0]["sha256"]
                (pack / ".kapitsa/manifest.json").write_text(json.dumps(manifest))
                identity = runtime.verify_model("qwen3.6-35b-a3b", values)
        self.assertEqual(identity["revision"], values["KAPITSA_MODEL_REVISION"])

    def test_live_server_must_serve_the_configured_model_and_context(self):
        values = runtime.config("qwen3.8-27b")
        identity = {"source": values["KAPITSA_MODEL_REPO"]}
        owner = {"pid": 123, "port": 8024, "model_identity": identity,
                 "command": runtime.command("qwen3.8-27b", values)}
        entry = {"id": "qwen3.8-27b", "context_length": 131072, "slots": 2, "active": True}
        with mock.patch.object(runtime, "owned_group", return_value={123: {}}), \
                mock.patch.object(runtime, "live_model", return_value=entry):
            with self.assertRaisesRegex(RuntimeError, "context differs"):
                runtime.check_live("qwen3.8-27b", values, owner, identity)
            with self.assertRaisesRegex(RuntimeError, "differs from the managed launch"):
                runtime.check_live("qwen3.8-27b", values, owner, {"source": "other"})

    def test_capacity_needs_one_full_context_and_caps_overrides(self):
        entry = {"slots": 2, "context_length": 262144}
        with mock.patch.object(runtime, "kv_room", return_value=4_350_048):
            self.assertEqual(bench.capacity(entry), (2, 4_350_048))
            with mock.patch.dict(os.environ, {"AUDIT_BENCH_ACTIVE_SLOTS": "3"}):
                with self.assertRaisesRegex(ValueError, "live capacity 2"):
                    bench.capacity(entry)
        with mock.patch.object(runtime, "kv_room", return_value=100_000):
            with self.assertRaisesRegex(RuntimeError, "full-context"):
                bench.capacity(entry)

    def test_kv_room_reads_the_launch_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "server.log"
            log.write_text("[kapitsa] memory: 20.81 GB allocated, budget 110.8 GB: "
                           "KV room 90.02 GB = 4395325 tokens (20 KB per token)\n")
            with mock.patch.object(runtime, "LOG", log):
                self.assertEqual(runtime.kv_room(), 4395325)

    def test_occupied_port_refused(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            with self.assertRaises(OSError):
                runtime.port_free(listener.getsockname()[1])

    def test_stop_refuses_reused_pid_and_retains_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile = Path(directory) / "server.json"
            pidfile.write_text(json.dumps({"pid": 123, "started": "original", "port": 8024}))
            processes = {123: {"group": 123, "started": "replacement", "state": "S", "command": ""}}
            with mock.patch.object(runtime, "PIDFILE", pidfile), \
                    mock.patch.object(runtime, "processes", return_value=processes), \
                    mock.patch.object(runtime.os, "killpg") as kill:
                with self.assertRaisesRegex(RuntimeError, "reused"):
                    runtime.stop()
                kill.assert_not_called()
                self.assertTrue(pidfile.exists())


if __name__ == "__main__":
    unittest.main()
