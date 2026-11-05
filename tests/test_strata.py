"""Strata config validation, host-derived placement, identity and admission contracts."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1] / "strata"
TAG = "qwen3.8-flash-next-nvfp4"
DS = "deepseek-v4.1-flash-q2"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load("strata_runtime", "runtime.py")
with mock.patch.dict(sys.modules, {"runtime": runtime}):
    bench = load("strata_bench", "bench.py")


class StrataTest(unittest.TestCase):
    def test_model_config_rejects_mutable_revision_paths_and_unknown_flags(self):
        for variable, value, message in (
                ("STRATA_MODEL_REVISION", "main", "immutable"),
                ("STRATA_MODEL_REPO", "not-a-repo", "Hugging Face"),
                ("STRATA_PLE_GGUF", "../../etc/passwd", "top level"),
                ("STRATA_PARALLEL", "16", "1..8"),
                ("STRATA_ENGINE_ARGS", "--spec", "pairs"),
                ("STRATA_ENGINE_ARGS", "--max-context 4096", "STRATA_ENGINE_ARGS"),
                ("STRATA_ENGINE_ARGS", "--kv fp32", "STRATA_ENGINE_ARGS")):
            with self.subTest(variable=variable, value=value):
                with mock.patch.dict(os.environ, {variable: value}):
                    with self.assertRaisesRegex(ValueError, message):
                        runtime.config(TAG)
        with self.assertRaises(ValueError):
            runtime.config("../kapitsa/models/clover-35b-a3b")

    def test_deepseek_config_rejects_unpinned_references_and_foreign_flags(self):
        for variable, value, message in (
                ("STRATA_ENGRAM", "ISTA-DASLab/x@main:engram.gguf", "owner/name@commit:path"),
                ("STRATA_DRAFTER", "unsloth/x@" + "0" * 40 + ":../drafter.gguf", "owner/name@commit:path"),
                ("STRATA_SHARDS", "a/one.gguf b/two.gguf", "one folder"),
                ("STRATA_EXPERT_PROFILE", "../profile.bin", "data/dsv41"),
                ("STRATA_ENGINE_ARGS", "--spec 4", "STRATA_ENGINE_ARGS"),
                ("STRATA_FAMILY", "glm", "STRATA_FAMILY"),
                ("STRATA_SERVED_NAME", "x/../../tmp/y", "plain model name")):
            with self.subTest(variable=variable, value=value):
                with mock.patch.dict(os.environ, {variable: value}):
                    with self.assertRaisesRegex(ValueError, message):
                        runtime.config(DS)

    def test_deepseek_launch_reads_the_shipped_profile_read_only(self):
        values = runtime.config(DS)
        config = runtime.run_config(values, {"cuda": "/usr/local/cuda"})
        args = config["args"]
        self.assertEqual((config["exe"], config["arch"]), (str(runtime.ENGINES["deepseek41"]), "deepseek41"))
        self.assertEqual(args[args.index("--max-context") + 1], values["STRATA_CTX"])
        self.assertEqual(Path(args[args.index("--expert-profile") + 1]).name, values["STRATA_EXPERT_PROFILE"])
        self.assertIn("--profile-readonly", args)
        self.assertEqual(args[args.index("--pack") + 1], str(runtime.dsv41_pack(values)))

    def test_placement_follows_available_memory_and_context(self):
        values = runtime.config(TAG)
        gib = 1024 ** 3
        kv = runtime.KV_HOST_BYTES * 262144
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(runtime, "MODELS", Path(temporary)):
                root = runtime.model_dir(values)
                (root / values["STRATA_PACK"]).mkdir(parents=True)
                (root / values["STRATA_PACK"] / "experts.bin").write_bytes(b"\0" * 1000)
                (root / values["STRATA_PLE_GGUF"]).write_bytes(b"\0" * 500)
                for available, flags in (
                        (16 * gib + kv + 1500, ["--kv-resident", "32768", "--ple-io", "ram"]),
                        (16 * gib + kv + 1000, ["--kv-resident", "32768"]),
                        (16 * gib + 1500, ["--ple-io", "ram"]),
                        (16 * gib, [])):
                    with self.subTest(available=available), \
                            mock.patch.object(runtime, "meminfo", return_value={"MemAvailable": available}):
                        self.assertEqual(runtime.placement(values), flags)
                with mock.patch.object(runtime, "meminfo", return_value={"MemAvailable": 64 * gib}):
                    self.assertEqual(runtime.placement({**values, "STRATA_CTX": "32768"}), ["--ple-io", "ram"])

    def test_no_ambient_strata_switch_reaches_the_server(self):
        with mock.patch.dict(os.environ, {"STRATA_PF_BATCH": "256", "STRATA_PORT": "9", "LANG": "C"}):
            environment = runtime.serve_environment()
        self.assertNotIn("STRATA_PF_BATCH", environment)
        self.assertNotIn("STRATA_PORT", environment)
        self.assertEqual(environment["LANG"], "C")

    def test_server_binds_loopback_offline_on_the_launcher_port(self):
        argv = runtime.command()
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertIn("--offline", argv)
        self.assertEqual(argv[argv.index("--port") + 1], "8025")

    def test_deepseek_identity_covers_shared_files_and_the_pack(self):
        values = runtime.config(DS)
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(runtime, "MODELS", Path(temporary)):
                for source in runtime.dsv41_sources(values):
                    runtime.source_path(source).parent.mkdir(parents=True, exist_ok=True)
                    runtime.source_path(source).write_bytes(source[2].encode())
                runtime.dsv41_pack(values).mkdir(parents=True)
                (runtime.dsv41_pack(values) / "tensors.txt").write_text("map")
                runtime.save(runtime.identity_path(values), runtime.identity_record(values))
                self.assertTrue(runtime.verify_model(values)["full_artifact_hash_verification"])
                engram = runtime.source_path(runtime.reference(values["STRATA_ENGRAM"], "STRATA_ENGRAM"))
                engram.write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError, "strata-pull"):
                    runtime.verify_model(values)

    def test_deepseek_pull_downloads_per_repository_and_packs_into_a_stage(self):
        values = runtime.config(DS)
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(runtime, "MODELS", Path(temporary)), \
                    mock.patch.object(runtime, "download") as download, \
                    mock.patch.object(runtime, "tool") as tool:
                pack = runtime.dsv41_pack(values)
                stage = pack.with_name(pack.name + ".partial")
                stage.mkdir(parents=True)
                tool.side_effect = lambda *argv: (stage.is_dir() and self.fail("stale stage kept"),
                                                  stage.mkdir())
                runtime.pull_dsv41(values)
                self.assertTrue(pack.is_dir() and not stage.exists())
                self.assertEqual(tool.call_args.args[tool.call_args.args.index("--out") + 1], str(stage))
                repositories = [call.args[:2] for call in download.call_args_list]
                self.assertEqual(len(repositories), len(set(repositories)))
                self.assertEqual(len(repositories), 2)
                runtime.pull_dsv41(values)
                self.assertEqual(tool.call_count, 1)
        with mock.patch.dict(os.environ, {"STRATA_DRAFTER": "unsloth/x@" + "1" * 40 + ":d.gguf"}):
            self.assertNotEqual(runtime.dsv41_pack(runtime.config(DS)), runtime.dsv41_pack(values))

    def test_bench_refuses_a_cpu_lane_server_that_capability_accepts(self):
        owner = {"residency": {"experts_in_vram": 8666, "experts": 15360}}
        with mock.patch.object(bench, "evidence", return_value=({}, owner, "", {}, {})), \
                mock.patch.object(sys, "argv", ["bench.py", DS]):
            with self.assertRaisesRegex(RuntimeError, "not all in VRAM"):
                bench.main()

    def test_identity_detects_changed_files(self):
        values = runtime.config(TAG)
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(runtime, "MODELS", Path(temporary) / "models"), \
                    mock.patch.object(runtime, "mtp_dir", return_value=Path(temporary) / "mtp"):
                root = runtime.model_dir(values)
                (root / values["STRATA_PACK"]).mkdir(parents=True)
                (Path(temporary) / "mtp" / "rt").mkdir(parents=True)
                (Path(temporary) / "mtp" / "rt" / "experts.bin").write_bytes(b"draft")
                for name in ("STRATA_DENSE_GGUF", "STRATA_PLE_GGUF", "STRATA_EMBD_GGUF"):
                    (root / values[name]).write_bytes(name.encode())
                (root / values["STRATA_PACK"] / "experts.bin").write_bytes(b"experts")
                (root / "llm-local-servers.json").write_text(json.dumps(runtime.identity_record(values)))
                self.assertTrue(runtime.verify_model(values)["full_artifact_hash_verification"])
                (root / values["STRATA_PACK"] / "experts.bin").write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError, "strata-pull"):
                    runtime.verify_model(values)

    def test_ownership_refuses_a_reused_pid(self):
        entry = {"pid": 4242, "started": 100}
        with mock.patch.object(runtime, "started", return_value=200):
            with self.assertRaisesRegex(RuntimeError, "reused"):
                runtime.owned(entry, "server.py")
        with mock.patch.object(runtime, "started", return_value=100), \
                mock.patch.object(runtime, "arguments", return_value=[b"python3", b"other.py"]):
            with self.assertRaisesRegex(RuntimeError, "unrecognized"):
                runtime.owned(entry, "server.py")
        with mock.patch.object(runtime, "started", return_value=None):
            self.assertFalse(runtime.owned(entry, "server.py"))
        with self.assertRaisesRegex(RuntimeError, "invalid"):
            runtime.owned({"pid": 1, "started": 0}, "server.py")

    def test_stop_keeps_evidence_when_nothing_ran_and_refuses_a_reused_pid(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            paths = {"STATE": state, "PIDFILE": state / "server.json", "LOG": state / "server.log",
                     "ENGINE_LOG": state / "engine.log", "RUN_CONFIG": state / "run.json",
                     "SLOTS": state / "ds4-slots"}
            with mock.patch.multiple(runtime, **paths), \
                    mock.patch.object(runtime, "gpu_processes", return_value=set()), \
                    mock.patch.object(runtime, "port_free"):
                owner = {"pid": 4242, "started": 100, "port": 8025, "engine": {"pid": 4243, "started": 101},
                         "run_config": {"exe": str(runtime.ENGINES["qwen"])}}
                for name in ("LOG", "ENGINE_LOG", "RUN_CONFIG"):
                    paths[name].write_text("evidence")
                paths["SLOTS"].mkdir()
                (paths["SLOTS"] / "conversation.bin").write_bytes(b"kv")
                runtime.save(paths["PIDFILE"], owner)
                with mock.patch.object(runtime, "started", return_value=None):
                    runtime.stop()
                self.assertFalse(paths["PIDFILE"].exists() or paths["SLOTS"].exists())
                self.assertTrue(paths["LOG"].exists() and paths["ENGINE_LOG"].exists())
                runtime.save(paths["PIDFILE"], owner)
                with mock.patch.object(runtime, "started", return_value=999):
                    with self.assertRaisesRegex(RuntimeError, "reused"):
                        runtime.stop()
                self.assertTrue(paths["PIDFILE"].exists())

    def test_capacity_is_one_full_context_session_per_slot(self):
        owner, health = {"run_config": {"parallel": 2}}, {"max_context": 262144}
        self.assertEqual(bench.capacity(owner, health), (2, 524288))
        with mock.patch.dict(os.environ, {"AUDIT_BENCH_ACTIVE_SLOTS": "3"}):
            with self.assertRaisesRegex(ValueError, "live capacity 2"):
                bench.capacity(owner, health)

    def test_residency_reads_the_engines_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "engine.log"
            with mock.patch.object(runtime, "ENGINE_LOG", log):
                log.write_text("strata serve: every expert is in the GPU cache (24576 of 24576): the CPU\n")
                self.assertEqual(runtime.residency(), {"experts_in_vram": 24576, "experts": 24576})
                log.write_text("strata generate: expert cache 8350 slots, 31.64 GiB of VRAM\n")
                self.assertEqual(runtime.residency(), {"experts_in_vram": 8350, "experts": None})
                log.write_text("ds4: CUDA0 layers [0, 39] + head: weights 5.86 GB, experts 74.84 GB "
                               "(8666 of 15360 in VRAM), caches 0.97 GB, 538 MiB free\n")
                self.assertEqual(runtime.residency(), {"experts_in_vram": 8666, "experts": 15360})


if __name__ == "__main__":
    unittest.main()
