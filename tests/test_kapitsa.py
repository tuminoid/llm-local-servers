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
    def test_model_config_rejects_mutable_revision_and_unknown_converter(self):
        with mock.patch.dict(os.environ, {"KAPITSA_MODEL_REVISION": "main"}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                runtime.config("clover-35b-a3b")
        with mock.patch.dict(os.environ, {"KAPITSA_CONVERTER": "../../evil.py"}):
            with self.assertRaisesRegex(ValueError, "KAPITSA_CONVERTER"):
                runtime.config("clover-35b-a3b")
        with mock.patch.dict(os.environ, {"KAPITSA_MAX_POSITIONS": "131072"}):
            with self.assertRaisesRegex(ValueError, "cover KAPITSA_CTX"):
                runtime.config("clover-35b-a3b")
        with mock.patch.dict(os.environ, {"KAPITSA_ENGINE_ENV": "HOME=/tmp"}):
            with self.assertRaisesRegex(ValueError, "NI_"):
                runtime.config("clover-35b-a3b")
        with mock.patch.dict(os.environ, {"KAPITSA_GENERATION": "dllm_length_penalty=off"}):
            with self.assertRaisesRegex(ValueError, "KAPITSA_GENERATION"):
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
        self.assertEqual(argv[argv.index("--model") + 1], str(runtime.MODELS / "clover-35b-a3b-view"))

    def test_converted_pack_and_view_must_match_the_config(self):
        values = runtime.config("clover-35b-a3b")
        with tempfile.TemporaryDirectory() as directory:
            models = Path(directory)
            pack = models / "clover-35b-a3b"
            pack.mkdir()
            (pack / "model.safetensors").write_bytes(b"weights")
            (pack / "config.json").write_text(json.dumps({"max_position_embeddings": 131072}))
            controls = {"dllm_length_penalty": 10.0, "dllm_think_end_bias": 10.0, "dllm_think_end_start": 4096,
                        "dllm_think_end_window": 4096}
            (pack / "generation_config.json").write_text(json.dumps(controls))
            files = {name: {"sha256": runtime.digest(pack / name)}
                     for name in ("model.safetensors", "config.json", "generation_config.json")}
            (pack / "conversion.json").write_text(json.dumps({"recipe": {"bits": 4}, "files": files}))
            record = {"source": values["KAPITSA_MODEL_REPO"], "revision": "0" * 40,
                      "converter": "convert_clover.py", "converter_commit": runtime.COMMIT}
            (pack / "llm-local-servers.json").write_text(json.dumps(record))
            with mock.patch.object(runtime, "MODELS", models):
                with self.assertRaisesRegex(RuntimeError, "differs from the config"):
                    runtime.verify_model("clover-35b-a3b", values)
                record["revision"] = values["KAPITSA_MODEL_REVISION"]
                (pack / "llm-local-servers.json").write_text(json.dumps(record))
                runtime.write_view("clover-35b-a3b", values)
                identity = runtime.verify_model("clover-35b-a3b", values)
                self.assertEqual(identity["max_position_embeddings"], 262144)
                self.assertEqual(identity["generation_overrides"], {"dllm_length_penalty": 0, "dllm_think_end_start": 16384,
                                                                   "dllm_think_end_window": 16384, "dllm_think_end_bias": 20})
                view = runtime.serve_dir("clover-35b-a3b", values)
                self.assertEqual(json.loads((view / "generation_config.json").read_text()),
                                 {"dllm_length_penalty": 0, "dllm_think_end_bias": 20, "dllm_think_end_start": 16384,
                                  "dllm_think_end_window": 16384})
                self.assertEqual(json.loads((pack / "config.json").read_text())["max_position_embeddings"], 131072)
                self.assertEqual(json.loads((pack / "generation_config.json").read_text()), controls)
                with self.assertRaisesRegex(RuntimeError, "serving view differs"):
                    runtime.verify_model("clover-35b-a3b", {**values, "KAPITSA_GENERATION": ""})
                with self.assertRaisesRegex(ValueError, "not in the pack"):
                    runtime.write_view("clover-35b-a3b", {**values, "KAPITSA_GENERATION": "top_k=20"})
                (pack / "model.safetensors").write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    runtime.verify_model("clover-35b-a3b", values)

    def test_live_server_must_serve_the_configured_model_and_context(self):
        values = runtime.config("clover-35b-a3b")
        identity = {"source": values["KAPITSA_MODEL_REPO"]}
        owner = {"pid": 123, "port": 8024, "model_identity": identity,
                 "command": runtime.command("clover-35b-a3b", values)}
        entry = {"id": "clover-35b-a3b", "context_length": 131072, "slots": 2, "active": True}
        with mock.patch.object(runtime, "owned_group", return_value={123: {}}), \
                mock.patch.object(runtime, "live_model", return_value=entry):
            with self.assertRaisesRegex(RuntimeError, "context differs"):
                runtime.check_live("clover-35b-a3b", values, owner, identity)
            with self.assertRaisesRegex(RuntimeError, "differs from the managed launch"):
                runtime.check_live("clover-35b-a3b", values, owner, {"source": "other"})

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
