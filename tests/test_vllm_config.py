import importlib.util
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock


REPO_DIR = pathlib.Path(__file__).resolve().parent.parent
VLLM_DIR = REPO_DIR / "vllm"
MODELS_DIR = VLLM_DIR / "models"

SPEC = importlib.util.spec_from_file_location(
    "vllm_bench_adapter", VLLM_DIR / "bench.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load vLLM benchmark adapter")
VLLM_BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VLLM_BENCH)

METAL_SPEC = importlib.util.spec_from_file_location(
    "vllm_metal_bench_adapter", REPO_DIR / "vllm-metal" / "bench.py"
)
if METAL_SPEC is None or METAL_SPEC.loader is None:
    raise RuntimeError("could not load vLLM-Metal benchmark adapter")
VLLM_METAL_BENCH = importlib.util.module_from_spec(METAL_SPEC)
METAL_SPEC.loader.exec_module(VLLM_METAL_BENCH)


class VllmConfigTest(unittest.TestCase):
    def test_every_model_repo_has_an_immutable_revision(self):
        direct_configs = 0
        revision_pattern = re.compile(
            r'^VLLM_MODEL_REVISION="\$\{VLLM_MODEL_REVISION:-([0-9a-f]{40})\}"$',
            re.MULTILINE,
        )
        for conf in sorted(MODELS_DIR.glob("*.conf")):
            text = conf.read_text(encoding="utf-8")
            if not re.search(r"^VLLM_MODEL=", text, re.MULTILINE):
                continue
            direct_configs += 1
            self.assertRegex(text, revision_pattern, str(conf))
        self.assertGreater(direct_configs, 0)

    def test_launcher_passes_revision_to_vllm(self):
        launcher = (VLLM_DIR / "start.sh").read_text(encoding="utf-8")
        self.assertIn('--revision "${VLLM_MODEL_REVISION}"', launcher)

    def test_non_commit_revision_is_rejected(self):
        with self.assertRaises(SystemExit):
            VLLM_BENCH._require_revision(
                "main", MODELS_DIR / "qwen3.8-27b.conf"
            )

    def test_cuda_runtime_profile_comes_from_managed_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = pathlib.Path(directory) / "server.log"
            log.write_text(
                'starting repo/model@' + "a" * 40
                + ' as "served" on 127.0.0.1:8000\n'
                "host: sm_80, 81920 MiB VRAM -> backend FLASH_ATTN, "
                "kv auto, util 0.98, seqs 8, batched 8192\n"
                "Using AttentionBackendEnum.FLASH_ATTN backend.\n"
                "GPU KV cache size: 746,553 tokens\n"
                "Maximum concurrency for 262,144 tokens per request: 2.84x\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"VLLM_LOG": str(log)}, clear=False):
                profile = VLLM_BENCH._runtime_profile(
                    context=262144,
                    active_slots=8,
                    kv_pool_tokens=746553,
                    capacity_source="managed log",
                    model_source="repo/model",
                    model_revision="a" * 40,
                    model="served",
                    model_settings={},
                    dry_run=False,
                )
        self.assertTrue(profile["checked"])
        self.assertEqual(profile["actual_attention_backends"], ["FLASH_ATTN"])
        self.assertEqual(profile["maximum_concurrency"], 2.84)

    def test_metal_runtime_profile_comes_from_managed_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = pathlib.Path(directory) / "server.log"
            log.write_text(
                'starting /models/demo as "served" on 127.0.0.1:8021\n'
                "host: 128 GiB unified memory -> util 0.91, seqs 5, "
                "batched 8192, max-len 262144, NAX auto, "
                "prefix-caching default\n"
                "NAX prefill attention kernels loaded\n"
                "GPU KV cache size: 1,264,961 tokens\n"
                "Maximum concurrency for 262,144 tokens per request: 4.82x\n",
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ, {"VLLM_METAL_LOG": str(log)}, clear=False
            ):
                profile = VLLM_METAL_BENCH._runtime_profile(
                    context=262144,
                    active_slots=5,
                    kv_pool_tokens=1264961,
                    capacity_source="managed log",
                    model="served",
                    model_dir=pathlib.Path("/models/demo"),
                    model_settings={},
                    dry_run=False,
                )
        self.assertTrue(profile["checked"])
        self.assertEqual(profile["prefix_caching"], "default")
        self.assertEqual(
            profile["nax_evidence"], ["NAX prefill attention kernels loaded"]
        )

    def test_metal_download_identity_requires_one_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = pathlib.Path(directory)
            metadata = model_dir / ".cache" / "huggingface" / "download"
            metadata.mkdir(parents=True)
            for name in (
                "config.json",
                "tokenizer_config.json",
                "model-00001-of-00001.safetensors",
            ):
                (model_dir / name).write_text("fixture", encoding="utf-8")
                (metadata / f"{name}.metadata").write_text(
                    "a" * 40 + "\nblob\n0\n", encoding="utf-8"
                )
            identity = VLLM_METAL_BENCH._download_identity(model_dir)
        self.assertEqual(identity["downloaded_revision"], "a" * 40)
        self.assertEqual(identity["verified_files"], 3)


if __name__ == "__main__":
    unittest.main()
