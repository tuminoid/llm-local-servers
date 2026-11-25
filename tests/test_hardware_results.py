"""The docs/hardware page tables are the renderer's output from their records."""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hardware_results", REPO / "docs/hardware/results.py")
results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(results)


def record(status="passed", publishable=True, optimal=1):
    return {
        "role": "audit", "tier": "MoE", "engine": "llama.cpp", "campaign": True,
        "note": None,
        "capability": {"status": status},
        "session": {"publishable": publishable, "optimal_streams": optimal},
    }


class HardwareResultsTest(unittest.TestCase):
    def test_committed_pages_are_current(self):
        for path, text in results.pages().items():
            with self.subTest(page=path.name):
                self.assertEqual(path.read_text(), text, "run make results")

    def test_every_record_names_a_model_config(self):
        for path in sorted(results.HERE.glob("*.json")):
            for key in results.load(path.stem)["profiles"]:
                runtime, profile = key.split("/", 1)
                with self.subTest(record=key):
                    self.assertTrue((REPO / runtime / "models" / f"{profile}.conf").exists())

    def test_only_a_gated_complete_publishable_session_ranks(self):
        self.assertTrue(results.ranked(record()))
        self.assertFalse(results.ranked(record(status="failed")))
        self.assertFalse(results.ranked(record(publishable=False)))
        self.assertFalse(results.ranked(record(optimal=None)))
        self.assertFalse(results.ranked({**record(), "capability": None}))



class ImportTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.here = Path(directory.name)
        (self.here / "hw.md").write_text("# hw\n")
        patcher = mock.patch.object(results, "HERE", self.here)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_import(self, part, identity, artifact):
        row = {"runtime": "ollama", "tag": "saluki-27b", "model_identity": identity,
               "artifact": artifact}
        with mock.patch.object(results, "project", return_value=(part, row)), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            results.import_row("hw", "file.json")
        return results.load("hw")["profiles"]["ollama/saluki-27b"], output.getvalue()

    def test_hand_fields_survive_a_reimport(self):
        record, _ = self.run_import("session", "a", "s1.json")
        record.update(role="audit", tier="dense")
        results.save("hw", {"profiles": {"ollama/saluki-27b": record}})
        record, _ = self.run_import("session", "a", "s2.json")
        self.assertEqual((record["role"], record["tier"]), ("audit", "dense"))
        self.assertEqual(record["session"]["artifact"], "s2.json")

    def test_a_new_identity_drops_the_stale_other_part(self):
        self.run_import("session", "a", "s1.json")
        record, output = self.run_import("capability", "b", "c1.json")
        self.assertIsNone(record["session"])
        self.assertEqual(record["capability"]["artifact"], "c1.json")
        self.assertIn("s1.json dropped", output)

    def test_a_runtime_files_under_its_directory(self):
        row = {"runtime": "vllm-cuda", "tag": "qwen3.8-27b", "model_identity": "a",
               "artifact": "x.json"}
        with mock.patch.object(results, "project", return_value=("session", row)), \
                contextlib.redirect_stdout(io.StringIO()):
            results.import_row("hw", "file.json")
        self.assertIn("vllm/qwen3.8-27b", results.load("hw")["profiles"])

    def test_an_import_needs_a_page_and_a_model_config(self):
        with self.assertRaises(SystemExit):
            results.import_row("absent", "file.json")
        row = {"runtime": "ollama", "tag": "no-such-conf", "model_identity": "a",
               "artifact": "x.json"}
        with mock.patch.object(results, "project", return_value=("session", row)), \
                self.assertRaises(SystemExit):
            results.import_row("hw", "file.json")


if __name__ == "__main__":
    unittest.main()
