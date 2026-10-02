"""The committed opencode configs are the generator's output from the model configs."""

import importlib.util
import os
from pathlib import Path
import re
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("opencode_generate", REPO / "opencode/generate.py")
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)

# Where each provider's port is the launcher's default.
PORTS = {
    "vllm": ("vllm/start.sh", 'VLLM_PORT="${VLLM_PORT:-8000}"'),
    "vllm-remote": ("Makefile", "VLLM_TUNNEL_PORT ?= 8001"),
    "vllm-metal": ("vllm-metal/start.sh", 'VLLM_PORT="${VLLM_PORT:-8021}"'),
    "splash": ("splash/runtime.py", 'os.environ.get("SPLASH_PORT", "8022")'),
    "lmstudio": ("lmstudio/runtime.py", 'os.environ.get("LMSTUDIO_PORT", "1234")'),
    "ollama": ("ollama/start.sh", 'OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"'),
    "ollama-remote": ("Makefile", "OLLAMA_TUNNEL_PORT ?= 11436"),
    "ds4": ("ds4/lib.sh", 'DS4_PORT="${DS4_PORT:-8023}"'),
}

ENTRY = {"name": "Qwen3.8 27B", "tool_call": True,
         "limit": {"context": 262144, "output": 65536}}


class OpencodeConfigTest(unittest.TestCase):
    def test_committed_files_are_current(self):
        # An exported model variable must not reach the output.
        with mock.patch.dict(os.environ, {"VLLM_MAX_LEN": "4096"}):
            expected = generate.files()
        committed = {path.relative_to(generate.OUT).as_posix(): path.read_text()
                     for path in generate.OUT.rglob("*.json")}
        self.assertEqual(sorted(committed), sorted(expected))
        for name, text in expected.items():
            with self.subTest(file=name):
                self.assertEqual(committed[name], text, "run make opencode-config")

    def test_ports_are_the_launcher_defaults(self):
        self.assertEqual(sorted(PORTS), sorted(generate.PROVIDERS))
        for provider, (_, _, url) in generate.PROVIDERS.items():
            file, default = PORTS[provider]
            with self.subTest(provider=provider):
                self.assertIn(default, (REPO / file).read_text())
                port = re.search(r"(\d+)\D*$", default).group(1)
                self.assertEqual(url, f"http://127.0.0.1:{port}/v1")

    def test_shared_ids_take_the_smallest_context_and_shortest_name(self):
        # The shorter name carries the larger context, so the two choices
        # cannot come from one config; both orders must agree.
        short = ("qwen3.8-27b", ENTRY)
        long = ("qwen3.8-27b-native", {**ENTRY, "name": "Qwen3.8 27B Native",
                                       "limit": {"context": 131072, "output": 32768}})
        for first, second in ((short, long), (long, short)):
            models = {}
            generate.add(models, "qwen3.8:27b", *first)
            generate.add(models, "qwen3.8:27b", *second)
            name, entry = models["qwen3.8:27b"]
            self.assertEqual(name, "qwen3.8-27b")
            self.assertEqual(entry["name"], "Qwen3.8 27B")
            self.assertEqual(entry["limit"], {"context": 131072, "output": 32768})

    def test_shared_ids_must_agree_on_capabilities(self):
        models = {}
        generate.add(models, "qwen3.8-27b", "qwen3.8-27b", ENTRY)
        with self.assertRaisesRegex(RuntimeError, "different capabilities"):
            generate.add(models, "qwen3.8-27b", "qwen3.8-27b-dflash2",
                         {**ENTRY, "tool_call": False})

    def test_display_names(self):
        for name, shown in (("qwen3.6-35b-a3b-coding-mlx-nvfp4", "Qwen3.6 35B A3B Coding MLX NVFP4"),
                            ("qwen3.8-flash-next-gguf-iq4xs", "Qwen3.8 Flash Next GGUF IQ4XS"),
                            ("mimo-v2.6-9b-4bit", "MiMo V2.6 9B 4bit"),
                            ("gemma4-e2b-awq", "Gemma4 E2B AWQ")):
            with self.subTest(name=name):
                self.assertEqual(generate.display(name), shown)


if __name__ == "__main__":
    unittest.main()
