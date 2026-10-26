import importlib.util
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock


REPO_DIR = pathlib.Path(__file__).resolve().parent.parent
OLLAMA_DIR = REPO_DIR / "ollama"
MODELS_DIR = OLLAMA_DIR / "models"

SPEC = importlib.util.spec_from_file_location(
    "ollama_bench_adapter", OLLAMA_DIR / "bench.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Ollama benchmark adapter")
OLLAMA_BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLLAMA_BENCH)


class OllamaIdentityTest(unittest.TestCase):
    def test_every_model_has_required_identity_expectations(self):
        digest_pattern = re.compile(
            r'^OLLAMA_EXPECTED_DIGEST="\$\{OLLAMA_EXPECTED_DIGEST:-([0-9a-f]{64})\}"$',
            re.MULTILINE,
        )
        required = (
            "OLLAMA_EXPECTED_FORMAT",
            "OLLAMA_EXPECTED_NATIVE_CONTEXT",
        )
        configs = sorted(MODELS_DIR.glob("*.conf"))
        self.assertTrue(configs)
        for conf in configs:
            text = conf.read_text(encoding="utf-8")
            self.assertRegex(text, digest_pattern, str(conf))
            for variable in required:
                self.assertIsNotNone(
                    re.search(
                        rf'^{variable}="\$\{{{variable}:-[^}}"]+\}}"$',
                        text,
                        re.MULTILINE,
                    ),
                    str(conf),
                )

    def test_latest_alias_matches_resolved_name(self):
        rows = [{"name": "glm-4.7-flash:latest"}]
        selected = OLLAMA_BENCH._select_model(
            rows, "glm-4.7-flash", "installed model"
        )
        self.assertEqual(selected["name"], "glm-4.7-flash:latest")

    def test_model_identity_combines_tags_and_show(self):
        responses = {
            OLLAMA_BENCH.TAGS_URL: {
                "models": [
                    {
                        "name": "qwen3.8:27b-nvfp4",
                        "digest": "a" * 64,
                        "size": 123,
                        "details": {
                            "format": "safetensors",
                            "quantization_level": "nvfp4",
                        },
                    }
                ]
            },
            OLLAMA_BENCH.SHOW_URL: {
                "capabilities": ["tools", "completion"],
                "model_info": {
                    "general.architecture": "qwen3_5",
                    "general.parameter_count": 27,
                    "qwen3_5.context_length": 262144,
                },
            },
        }

        def request(url, payload=None):
            del payload
            return responses[url]

        with mock.patch.object(OLLAMA_BENCH, "_request", side_effect=request):
            identity = OLLAMA_BENCH._model_identity("qwen3.8:27b-nvfp4")
        self.assertEqual(identity["digest"], "a" * 64)
        self.assertEqual(identity["architecture"], "qwen3_5")
        self.assertEqual(identity["native_context"], 262144)
        self.assertEqual(identity["capabilities"], ["completion", "tools"])

    def test_identity_mismatch_is_rejected(self):
        identity = {
            "requested_tag": "demo:latest",
            "digest": "a" * 64,
            "format": "gguf",
            "native_context": 131072,
        }
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            OLLAMA_BENCH._validate_identity(
                identity,
                {
                    "digest": "b" * 64,
                    "format": "gguf",
                    "native_context": 131072,
                },
            )

    def test_unspecified_native_context_must_be_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = pathlib.Path(tmp) / "demo.conf"
            values = {
                "OLLAMA_EXPECTED_DIGEST": "a" * 64,
                "OLLAMA_EXPECTED_FORMAT": "safetensors",
                "OLLAMA_EXPECTED_NATIVE_CONTEXT": "unspecified",
            }
            conf.write_text(
                "".join(f'{k}="${{{k}:-{v}}}"\n' for k, v in values.items()),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ):
                for name in values:
                    os.environ.pop(name, None)
                expectations = OLLAMA_BENCH._identity_expectations(conf)
        self.assertIsNone(expectations["native_context"])
        identity = {
            "requested_tag": "demo:latest",
            "digest": "a" * 64,
            "format": "safetensors",
            "native_context": None,
        }
        self.assertTrue(
            OLLAMA_BENCH._validate_identity(identity, expectations)["matched"]
        )
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            OLLAMA_BENCH._validate_identity(
                {**identity, "native_context": 262144}, expectations
            )

    def test_mismatch_classification_gates_auto_recovery(self):
        # Registry still serves the pin: the local store is merely stale
        # and pulling lands the reviewed artifact.
        self.assertEqual(
            OLLAMA_BENCH.stale_or_drifted("a" * 64, "b" * 64, "b" * 64),
            "stale",
        )
        # Registry moved past the pin: repin is a human decision.
        self.assertEqual(
            OLLAMA_BENCH.stale_or_drifted("a" * 64, "b" * 64, "c" * 64),
            "drifted",
        )
        # Registry unreachable: the refusal stands.
        self.assertEqual(
            OLLAMA_BENCH.stale_or_drifted("a" * 64, "b" * 64, None),
            "unknown",
        )

    def test_verified_identity_pulls_only_when_registry_matches_pin(self):
        pulls = []
        identities = iter([
            {"requested_tag": "demo:latest", "digest": "a" * 64},
            {"requested_tag": "demo:latest", "digest": "b" * 64},
        ])
        with mock.patch.object(
            OLLAMA_BENCH, "_model_identity", side_effect=lambda _model: next(identities)
        ), mock.patch.object(
            OLLAMA_BENCH, "_registry_tag_digest", return_value="b" * 64
        ), mock.patch.object(
            OLLAMA_BENCH.urllib.request, "urlopen"
        ) as urlopen, mock.patch.object(
            OLLAMA_BENCH.json, "load", return_value={}
        ):
            urlopen.return_value.__enter__.return_value = mock.Mock()
            pulls.append(True)
            result = OLLAMA_BENCH.verified_identity(
                "demo:latest", {"digest": "b" * 64}
            )
        self.assertTrue(result["matched"])
        self.assertTrue(urlopen.called)

    def test_verified_identity_refuses_true_drift_without_pulling(self):
        with mock.patch.object(
            OLLAMA_BENCH, "_model_identity",
            return_value={"requested_tag": "demo:latest", "digest": "a" * 64},
        ), mock.patch.object(
            OLLAMA_BENCH, "_registry_tag_digest", return_value="c" * 64
        ), mock.patch.object(
            OLLAMA_BENCH.urllib.request, "urlopen"
        ) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "drifted past"):
                OLLAMA_BENCH.verified_identity(
                    "demo:latest", {"digest": "b" * 64}
                )
        self.assertFalse(urlopen.called)

    def test_loaded_digest_must_match_installed_identity(self):
        running = {
            "models": [
                {
                    "name": "demo:latest",
                    "digest": "b" * 64,
                    "size": 1,
                    "size_vram": 1,
                    "context_length": 131072,
                }
            ]
        }
        with mock.patch.object(OLLAMA_BENCH, "_request", return_value=running):
            with self.assertRaisesRegex(RuntimeError, "loaded model digest"):
                OLLAMA_BENCH._residency(
                    "demo",
                    {
                        "digest": "a" * 64,
                        "format": "gguf",
                        "family": None,
                        "quantization": None,
                    },
                )

    def test_config_environment_override_wins(self):
        conf = MODELS_DIR / "saluki-27b.conf"
        with mock.patch.dict(
            os.environ, {"OLLAMA_EXPECTED_DIGEST": "f" * 64}, clear=False
        ):
            expectations = OLLAMA_BENCH._identity_expectations(conf)
        self.assertEqual(expectations["digest"], "f" * 64)

    def test_unknown_live_quantization_requires_matching_digest(self):
        loaded = {
            "name": "demo:latest", "digest": "a" * 64,
            "details": {"format": "gguf", "quantization_level": "unknown"},
        }
        identity = {"digest": "a" * 64, "format": "gguf", "quantization": "Q6_K"}
        with mock.patch.object(OLLAMA_BENCH, "_request",
                               return_value={"models": [loaded]}):
            result = OLLAMA_BENCH._residency("demo", identity)
            self.assertEqual(result["digest"], identity["digest"])
            loaded["digest"] = "b" * 64
            with self.assertRaisesRegex(RuntimeError, "loaded model digest"):
                OLLAMA_BENCH._residency("demo", identity)
            loaded["digest"] = identity["digest"]
            loaded["details"]["quantization_level"] = "Q4_K_M"
            with self.assertRaisesRegex(RuntimeError, "loaded model quantization"):
                OLLAMA_BENCH._residency("demo", identity)

    def test_runtime_profile_comes_from_managed_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = pathlib.Path(directory) / "server.log"
            log.write_bytes(
                b"starting llama-server --model demo -np 2\n"
                b"config: model=demo:latest context=131072 parallel=2 "
                b"aggregate=262144 kv=q8_0\n"
                b"config: host=127.0.0.1:11434 flash_attention=1 "
                b"fit_target=1024MiB cache_ram=0 version=0.32.14\n"
                b"config: binary=/runtime/ollama models=default state=/state\n"
                b"tokenizer metadata: \xc4\n"
            )
            identity = {
                "digest": "a" * 64,
                "format": "gguf",
                "quantization": "Q4_K_M",
            }
            residency = {"allocated_context": 131072}
            with mock.patch.object(OLLAMA_BENCH, "SERVER_LOG", log):
                runner, slots = OLLAMA_BENCH._effective_runner()
                profile = OLLAMA_BENCH._runtime_profile(
                    model="demo:latest",
                    context=131072,
                    identity=identity,
                    residency=residency,
                    runner="llama.cpp",
                    effective_slots=2,
                )
        self.assertEqual((runner, slots), ("llama.cpp", 2))
        self.assertTrue(profile["checked"])
        self.assertEqual(profile["requested_slots"], 2)
        self.assertEqual(profile["prompt_cache_ram_mib"], 0)
        self.assertEqual(profile["model_digest"], "a" * 64)


if __name__ == "__main__":
    unittest.main()
