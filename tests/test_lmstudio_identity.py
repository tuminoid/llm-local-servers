import importlib.util
import pathlib
import unittest
from unittest import mock


REPO_DIR = pathlib.Path(__file__).resolve().parent.parent
LMSTUDIO_DIR = REPO_DIR / "lmstudio"

SPEC = importlib.util.spec_from_file_location(
    "lmstudio_bench_adapter", LMSTUDIO_DIR / "bench.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load LM Studio benchmark adapter")
LMSTUDIO_BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LMSTUDIO_BENCH)


class LMStudioFormatMatchTest(unittest.TestCase):
    def test_mlx_config_matches_reported_safetensors(self):
        # lms reports an MLX artifact's on-disk container as "safetensors",
        # never "mlx"; the mlx config expectation must still match it.
        self.assertTrue(LMSTUDIO_BENCH._format_matches("mlx", "safetensors"))
        self.assertTrue(LMSTUDIO_BENCH._format_matches("mlx", "MLX"))

    def test_gguf_config_matches_reported_gguf_only(self):
        self.assertTrue(LMSTUDIO_BENCH._format_matches("gguf", "gguf"))
        self.assertTrue(LMSTUDIO_BENCH._format_matches("gguf", "GGUF"))
        self.assertFalse(LMSTUDIO_BENCH._format_matches("gguf", "safetensors"))

    def test_mlx_config_rejects_gguf_artifact(self):
        self.assertFalse(LMSTUDIO_BENCH._format_matches("mlx", "gguf"))


class LMStudioIdentityTest(unittest.TestCase):
    def _mlx_record(self):
        return {
            "identifier": "qwen3.6-27b-mlx",
            "modelKey": "qwen/qwen3.6-27b-mlx",
            "path": "qwen/qwen3.6-27b-mlx",
            "format": "safetensors",
            "architecture": "qwen3_6",
            "quantization": {"name": "4bit", "bits": 4},
            "sizeBytes": 1,
            "maxContextLength": 262144,
        }

    def test_mlx_identity_accepts_safetensors_format(self):
        with mock.patch.object(
            LMSTUDIO_BENCH, "_loaded_models", return_value=[self._mlx_record()]
        ):
            identity = LMSTUDIO_BENCH._model_identity(
                "qwen3.6-27b-mlx",
                {
                    "format": "mlx",
                    "quantization": "4bit",
                    "architecture": "qwen3_6",
                },
            )
        self.assertTrue(identity["matched"])
        self.assertEqual(identity["format"], "safetensors")
        self.assertEqual(identity["quantization"], "4bit")

    def test_mlx_config_against_loaded_gguf_is_rejected(self):
        gguf = dict(self._mlx_record())
        gguf["format"] = "gguf"
        gguf["architecture"] = "qwen35"
        gguf["quantization"] = {"name": "Q4_K_M", "bits": 4}
        with mock.patch.object(
            LMSTUDIO_BENCH, "_loaded_models", return_value=[gguf]
        ):
            with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                LMSTUDIO_BENCH._model_identity(
                    "qwen3.6-27b-mlx",
                    {
                        "format": "mlx",
                        "quantization": "4bit",
                        "architecture": "qwen3_6",
                    },
                )


if __name__ == "__main__":
    unittest.main()
