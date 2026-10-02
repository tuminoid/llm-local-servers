"""Every model config must declare its Capability Check expectations.

The capability gate reads the reasoning/tools expectations and the
documented thinking controls from the model config; a config missing
them fails only at check time against a live server. This inventory
test catches the omission offline, for every runtime, and fails loudly
when an inventory directory is missing or empty rather than passing
vacuously over nothing.
"""

import os
import pathlib
import unittest
from unittest import mock

from audit_bench import parse_sampling
from capability_check import resolve_shell_config


REPO_DIR = pathlib.Path(__file__).resolve().parent.parent


class ModelConfigInventoryTest(unittest.TestCase):
    def test_every_model_declares_capability_expectations(self):
        inventories = (
            (
                REPO_DIR / "lmstudio" / "models",
                (
                    "LMSTUDIO_CAP_REASONING",
                    "LMSTUDIO_CAP_TOOLS",
                    "LMSTUDIO_CAP_REASONING_MODE",
                    "LMSTUDIO_CAP_DISABLE_MODE",
                    "LMSTUDIO_CAP_SYSTEM_PROMPT",
                ),
            ),
            (
                REPO_DIR / "splash" / "models",
                (
                    "SPLASH_CAP_REASONING",
                    "SPLASH_CAP_TOOLS",
                    "SPLASH_CAP_REASONING_MODE",
                    "SPLASH_CAP_DISABLE_MODE",
                    "SPLASH_CAP_SYSTEM_PROMPT",
                ),
            ),
            (
                REPO_DIR / "vllm" / "models",
                (
                    "VLLM_CAP_REASONING",
                    "VLLM_CAP_TOOLS",
                    "VLLM_CAP_REASONING_MODE",
                    "VLLM_CAP_DISABLE_MODE",
                    "VLLM_CAP_SYSTEM_PROMPT",
                ),
            ),
            (
                REPO_DIR / "vllm-metal" / "models",
                (
                    "VLLM_CAP_REASONING",
                    "VLLM_CAP_TOOLS",
                    "VLLM_CAP_REASONING_MODE",
                    "VLLM_CAP_DISABLE_MODE",
                    "VLLM_CAP_SYSTEM_PROMPT",
                ),
            ),
            (
                REPO_DIR / "ollama" / "models",
                (
                    "OLLAMA_CAP_REASONING",
                    "OLLAMA_CAP_TOOLS",
                    "OLLAMA_CAP_REASONING_MODE",
                    "OLLAMA_CAP_DISABLE_MODE",
                    "OLLAMA_CAP_SYSTEM_PROMPT",
                ),
            ),
            (
                REPO_DIR / "ds4" / "models",
                (
                    "DS4_CAP_REASONING",
                    "DS4_CAP_TOOLS",
                    "DS4_CAP_REASONING_MODE",
                    "DS4_CAP_DISABLE_MODE",
                    "DS4_CAP_SYSTEM_PROMPT",
                ),
            ),
        )
        for directory, names in inventories:
            configs = sorted(directory.glob("*.conf"))
            self.assertTrue(configs, f"no model configs found in {directory}")
            for conf in configs:
                with self.subTest(conf=conf):
                    with mock.patch.dict(
                        os.environ,
                        {name: "" for name in names},
                        clear=False,
                    ):
                        values = resolve_shell_config(conf, names)
                    self.assertIn(values[names[0]], {"required", "absent"})
                    self.assertIn(values[names[1]], {"required", "absent"})
                    self.assertTrue(values[names[2]])
                    self.assertTrue(values[names[3]])

    def test_every_model_declares_its_sampling(self):
        # AuditBench decodes at the checkpoint's own sampling, and a run
        # without a declared temperature is not canonical.
        for directory, name in (
            (REPO_DIR / "lmstudio" / "models", "LMSTUDIO_SAMPLING"),
            (REPO_DIR / "splash" / "models", "SPLASH_SAMPLING"),
            (REPO_DIR / "vllm" / "models", "VLLM_SAMPLING"),
            (REPO_DIR / "vllm-metal" / "models", "VLLM_SAMPLING"),
            (REPO_DIR / "ollama" / "models", "OLLAMA_SAMPLING"),
            (REPO_DIR / "ds4" / "models", "DS4_SAMPLING"),
        ):
            configs = sorted(directory.glob("*.conf"))
            self.assertTrue(configs, f"no model configs found in {directory}")
            for conf in configs:
                with self.subTest(conf=conf):
                    with mock.patch.dict(os.environ, {name: ""}, clear=False):
                        value = resolve_shell_config(conf, (name,))[name]
                    self.assertIn("temperature", parse_sampling(value))


if __name__ == "__main__":
    unittest.main()
