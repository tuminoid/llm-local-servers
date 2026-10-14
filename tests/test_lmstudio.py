"""LM Studio ownership, pinned identity and live-load contracts."""

import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1] / "lmstudio"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load("lmstudio_runtime", "runtime.py")
with mock.patch.dict(sys.modules, {"runtime": runtime}):
    bench = load("lmstudio_bench", "bench.py")
with mock.patch.dict(sys.modules, {"bench": bench}):
    capability = load("lmstudio_capability", "capability.py")

OWNER = {"identifier": "qwen3.8-27b-mlx", "parallel": 4}
ENTRY = {"identifier": "qwen3.8-27b-mlx", "path": "llm-local-servers/qwen3.8-27b-mlx",
         "format": "safetensors", "contextLength": 262144, "architecture": "qwen3_5",
         "parallel": 4, "quantization": {"name": "4bit", "bits": 4}}


class LMStudioTest(unittest.TestCase):
    def test_model_config_rejects_mutable_revision(self):
        self.assertEqual(runtime.config("qwen3.8-27b-mlx")["LMSTUDIO_FORMAT"], "mlx")
        with mock.patch.dict(os.environ, {"LMSTUDIO_MODEL_REVISION": "main"}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                runtime.config("qwen3.8-27b-mlx")

    def test_live_load_must_be_the_pulled_copy(self):
        values = runtime.config("qwen3.8-27b-mlx")
        served = io.BytesIO(json.dumps({"data": [{"id": OWNER["identifier"]}]}).encode())
        with mock.patch.object(runtime, "loaded", return_value=[ENTRY]), \
                mock.patch("urllib.request.urlopen", return_value=served):
            base, entry = runtime.check_live("qwen3.8-27b-mlx", values, OWNER)
        self.assertEqual((base, entry), ("http://127.0.0.1:1234", ENTRY))
        # The operator's own download of the same repository is not ours.
        other = {**ENTRY, "path": "mlx-community/Qwen3.8-27B-4bit"}
        with mock.patch.object(runtime, "loaded", return_value=[other]):
            with self.assertRaisesRegex(RuntimeError, "differs from the record"):
                runtime.check_live("qwen3.8-27b-mlx", values, OWNER)

    def test_every_file_must_name_the_pinned_revision(self):
        values = runtime.config("qwen3.8-27b-mlx")
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(runtime, "models_root", return_value=Path(directory)):
            path = runtime.model_path("qwen3.8-27b-mlx")
            metadata = path / ".cache/huggingface/download"
            metadata.mkdir(parents=True)
            (path / "config.json").write_text("{}")
            (metadata / "config.json.metadata").write_text(
                values["LMSTUDIO_MODEL_REVISION"] + "\netag\n")
            self.assertEqual(runtime.verify_model("qwen3.8-27b-mlx", values)["verified_files"], 1)
            (path / "model.safetensors").write_text("unverified")
            with self.assertRaisesRegex(RuntimeError, "pinned revision"):
                runtime.verify_model("qwen3.8-27b-mlx", values)

    def test_stop_without_record_touches_nothing(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(runtime, "RECORD", Path(directory) / "server.json"), \
                mock.patch.object(runtime, "lms") as lms, \
                mock.patch("sys.stdout", io.StringIO()):
            runtime.stop()
        lms.assert_not_called()

    def test_measurements_record_pin_drift(self):
        pins = {"LMSTUDIO_VERSION": "0.4.25+1", "LMSTUDIO_MLX_ENGINE_VERSION": "1.11.0"}
        owner = {**OWNER, "format": "mlx", "app": "0.4.26+1", "engine": "mlx-llm@1.12.0",
                 "context": 262144}
        prefs = [{"model_format": "safetensors", "name": "mlx-llm", "version": "1.12.0"},
                 {"model_format": "splash", "name": "splash", "version": "0.0.6"}]
        with mock.patch.dict(os.environ, pins), \
                mock.patch.object(runtime, "internal", return_value=prefs), \
                mock.patch("shutil.which", return_value="/bin/hf"):
            runtime.verify_install()  # every verb accepts an updated LM Studio
            self.assertEqual(runtime.pin_drift("0.4.25+1", {"mlx": "mlx-llm@1.11.0"}), [])
            with tempfile.TemporaryDirectory() as directory:
                record = Path(directory) / "server.json"
                record.write_text(json.dumps(owner))
                with mock.patch.object(runtime, "RECORD", record), \
                        mock.patch.object(runtime, "verify_install",
                                          return_value={"mlx": owner["engine"]}), \
                        mock.patch.object(runtime, "app_version", return_value=owner["app"]), \
                        mock.patch.object(runtime, "loaded", return_value=[ENTRY]), \
                        mock.patch.object(runtime, "verify_model", return_value={}), \
                        mock.patch.object(runtime, "check_live",
                                          return_value=("http://127.0.0.1:1234", ENTRY)), \
                        mock.patch("sys.stderr", io.StringIO()):
                    identity = bench.evidence("qwen3.8-27b-mlx")[3]
        self.assertEqual(identity["pin_drift"], [
            "LM Studio 0.4.26+1, pinned LMSTUDIO_VERSION=0.4.25+1",
            "mlx-llm@1.12.0, pinned LMSTUDIO_MLX_ENGINE_VERSION=1.11.0"])

    def test_stop_leaves_the_operators_server(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "server.json"
            record.write_text(json.dumps({**OWNER, "started_server": False}))
            with mock.patch.object(runtime, "RECORD", record), \
                    mock.patch.object(runtime, "LOG", Path(directory) / "server.log"), \
                    mock.patch.object(runtime, "loaded", side_effect=[[ENTRY], []]), \
                    mock.patch.object(runtime, "lms") as lms, \
                    mock.patch("sys.stdout", io.StringIO()):
                runtime.stop()
            self.assertFalse(record.exists())
        lms.assert_called_once_with("unload", OWNER["identifier"])

    def test_measurements_need_the_model_alone(self):
        pins = {"LMSTUDIO_VERSION": "0.4.25+1", "LMSTUDIO_MLX_ENGINE_VERSION": "1.11.0"}
        owner = {**OWNER, "format": "mlx", "app": "0.4.25+1", "engine": "mlx-llm@1.11.0"}
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, pins):
            record = Path(directory) / "server.json"
            record.write_text(json.dumps(owner))
            with mock.patch.object(runtime, "RECORD", record), \
                    mock.patch.object(runtime, "verify_install",
                                      return_value={"mlx": owner["engine"]}), \
                    mock.patch.object(runtime, "app_version", return_value=owner["app"]), \
                    mock.patch.object(runtime, "loaded",
                                      return_value=[ENTRY, {**ENTRY, "identifier": "gui-chat"}]):
                with self.assertRaisesRegex(RuntimeError, "also loaded: gui-chat"):
                    bench.evidence("qwen3.8-27b-mlx")

    def test_thinking_control_is_top_level(self):
        self.assertEqual(capability.control("reasoning-effort-none"), {"reasoning_effort": "none"})
        self.assertIsNone(capability.control("none"))


if __name__ == "__main__":
    unittest.main()
