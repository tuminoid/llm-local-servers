"""FreeToken config validation, launch command and admission contracts."""

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1] / "freetoken"
TAG = "ornith1.5-35b-a3b"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load("freetoken_runtime", "runtime.py")
with mock.patch.dict(sys.modules, {"runtime": runtime}):
    bench = load("freetoken_bench", "bench.py")


class FreeTokenTest(unittest.TestCase):
    def test_model_config_rejects_mutable_revision_paths_and_unknown_flags(self):
        for variable, value, message in (
                ("FREETOKEN_MODEL_REVISION", "main", "immutable"),
                ("FREETOKEN_MODEL_REPO", "not-a-repo", "Hugging Face"),
                ("FREETOKEN_MODEL_FILES", "../../etc/passwd.gguf", "GGUF"),
                ("FREETOKEN_MODEL_FILES", "model.safetensors", "GGUF"),
                ("FREETOKEN_PARALLEL", "16", "1..8"),
                ("FREETOKEN_MOE_STRATEGY", "cpu", "MOE_STRATEGY"),
                ("FREETOKEN_ENGINE_ARGS", "--kv-cache-dtype", "pairs"),
                ("FREETOKEN_ENGINE_ARGS", "--host 0.0.0.0", "FREETOKEN_ENGINE_ARGS"),
                ("FREETOKEN_SERVED_NAME", "x/../../tmp/y", "plain model name")):
            with self.subTest(variable=variable, value=value):
                with mock.patch.dict(os.environ, {variable: value}):
                    with self.assertRaisesRegex(ValueError, message):
                        runtime.config(TAG)
        with self.assertRaises(ValueError):
            runtime.config("../strata/models/qwen3.8-flash-next-nvfp4")

    def test_command_binds_loopback_and_serves_the_configs_context(self):
        values = runtime.config(TAG)
        argv = runtime.command(values)
        self.assertEqual(argv[:2], [str(runtime.FT), "serve"])
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--max-seq-len-override") + 1], values["FREETOKEN_CTX"])
        self.assertEqual(argv[argv.index("--moe-strategy") + 1], "fused")
        self.assertIn("--enable-cache-report", argv)
        self.assertTrue(argv[argv.index("--model") + 1].endswith("Ornith-1.5-35B-Q4_K_M.gguf"))
        self.assertNotIn("--kv-reserve-tokens", argv)
        offload = dict(values, FREETOKEN_MOE_STRATEGY="offload", FREETOKEN_PARALLEL="2")
        argv = runtime.command(offload)
        self.assertEqual(argv[argv.index("--kv-reserve-tokens") + 1], str(2 * int(values["FREETOKEN_CTX"])))

    def test_caller_freetoken_variables_never_reach_the_server(self):
        with mock.patch.dict(os.environ, {"FREETOKEN_PORT": "1", "PATH": "/usr/bin"}):
            environment = runtime.serve_environment({"cuda": "/usr/local/cuda-13.2"})
        self.assertFalse([key for key in environment if key.startswith("FREETOKEN_")])
        self.assertTrue(environment["PATH"].startswith(str(runtime.VENV / "bin")))
        self.assertEqual(environment["HF_HUB_OFFLINE"], "1")

    def test_capacity_is_live_admission_and_reported_pool(self):
        owner = {"parallel": 4, "engine": {"kv_pool_tokens": 2_601_468, "moe_strategy": "fused"}}
        self.assertEqual(bench.capacity(owner), (4, 2_601_468))
        with mock.patch.dict(os.environ, {"AUDIT_BENCH_ACTIVE_SLOTS": "8"}):
            with self.assertRaisesRegex(ValueError, "live capacity"):
                bench.capacity(owner)
        with self.assertRaisesRegex(RuntimeError, "KV pool"):
            bench.capacity({"parallel": 4, "engine": {"kv_pool_tokens": None}})


if __name__ == "__main__":
    unittest.main()
