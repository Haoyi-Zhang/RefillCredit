"""Regression fixtures for immutable-baseline reproduction orchestration."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reproduce import ReproductionFailure, expected_outputs, run_part


class ImmutableReproductionTests(unittest.TestCase):
    def fixture(self, program: str, *, output: dict | None = None, retained: dict | None = None):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        (root / "results").mkdir(parents=True)
        (root / "inputs").mkdir()
        (root / "tables").mkdir()
        (root / "job.py").write_text(program, encoding="utf-8")
        (root / "results/out.json").write_text(
            json.dumps(output if output is not None else {"value": 1}) + "\n",
            encoding="utf-8",
        )
        (root / "results/retained.json").write_text(
            json.dumps(retained if retained is not None else {"kept": True}) + "\n",
            encoding="utf-8",
        )
        return temp, root

    def test_success_uses_isolated_copy_and_records_both_file_classes(self):
        temp, root = self.fixture(
            "from pathlib import Path\n"
            "Path('results/out.json').write_text('{\"value\": 1, \"cpu_seconds\": 999}\\n')\n",
            output={"value": 1, "cpu_seconds": 1},
        )
        self.addCleanup(temp.cleanup)
        before = (root / "results/out.json").read_bytes()
        result = run_part(
            root,
            0,
            commands=[["job.py"]],
            required_outputs=["results/out.json"],
            timeout_seconds=2,
            apply_limits=False,
        )
        self.assertTrue(result["semantic_results_equal"])
        self.assertEqual(result["regenerated_files"], ["results/out.json"])
        self.assertIn("results/retained.json", result["retained_files"])
        self.assertEqual((root / "results/out.json").read_bytes(), before)

    def test_deleted_required_output_fails_without_touching_baseline(self):
        temp, root = self.fixture("from pathlib import Path\np=Path('results/out.json')\np.unlink(missing_ok=True)\n")
        self.addCleanup(temp.cleanup)
        before = (root / "results/out.json").read_bytes()
        with self.assertRaises(ReproductionFailure) as ctx:
            run_part(
                root,
                0,
                commands=[["job.py"]],
                required_outputs=["results/out.json"],
                timeout_seconds=2,
                apply_limits=False,
            )
        self.assertIn("missing", str(ctx.exception))
        self.assertEqual((root / "results/out.json").read_bytes(), before)

    def test_child_failure_and_timeout_both_preserve_baseline(self):
        programs = {
            "failure": "raise SystemExit(7)\n",
            "timeout": "import time\ntime.sleep(2)\n",
        }
        for label, program in programs.items():
            with self.subTest(label=label):
                temp, root = self.fixture(program)
                try:
                    before = (root / "results/out.json").read_bytes()
                    with self.assertRaises(ReproductionFailure):
                        run_part(
                            root,
                            0,
                            commands=[["job.py"]],
                            required_outputs=["results/out.json"],
                            timeout_seconds=0.15 if label == "timeout" else 2,
                            apply_limits=False,
                        )
                    self.assertEqual((root / "results/out.json").read_bytes(), before)
                finally:
                    temp.cleanup()

    def test_same_semantic_regression_fails_twice(self):
        temp, root = self.fixture(
            "from pathlib import Path\nPath('results/out.json').write_text('{\"value\": 2}\\n')\n"
        )
        self.addCleanup(temp.cleanup)
        before = (root / "results/out.json").read_bytes()
        failures = 0
        for _ in range(2):
            with self.assertRaises(ReproductionFailure):
                run_part(
                    root,
                    0,
                    commands=[["job.py"]],
                    required_outputs=["results/out.json"],
                    timeout_seconds=2,
                    apply_limits=False,
                )
            failures += 1
            self.assertEqual((root / "results/out.json").read_bytes(), before)
        self.assertEqual(failures, 2)

    def test_unexpected_mutation_of_retained_file_fails(self):
        temp, root = self.fixture(
            "from pathlib import Path\n"
            "Path('results/out.json').write_text('{\"value\": 1}\\n')\n"
            "Path('results/retained.json').write_text('{\"kept\": false}\\n')\n"
        )
        self.addCleanup(temp.cleanup)
        before = (root / "results/retained.json").read_bytes()
        with self.assertRaises(ReproductionFailure) as ctx:
            run_part(
                root,
                0,
                commands=[["job.py"]],
                required_outputs=["results/out.json"],
                timeout_seconds=2,
                apply_limits=False,
            )
        self.assertIn("retained", str(ctx.exception))
        self.assertEqual((root / "results/retained.json").read_bytes(), before)

    def test_all_part_manifests_are_explicit_unique_and_disjoint(self):
        all_required: set[str] = set()
        for part in range(7):
            required = expected_outputs(part)
            self.assertTrue(required)
            self.assertEqual(len(required), len(set(required)))
            for relative in required:
                path = Path(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertIn(path.parts[0], {"inputs", "results", "tables"})
            overlap = all_required.intersection(required)
            self.assertFalse(overlap, overlap)
            all_required.update(required)

    def test_failed_semantic_attempt_retains_its_actual_raw_output(self):
        temp, root = self.fixture(
            "from pathlib import Path\nPath('results/out.json').write_text('{\"value\": 2}\\n')\n"
        )
        self.addCleanup(temp.cleanup)
        report_path = root.parent / "records" / "attempt.json"
        with self.assertRaises(ReproductionFailure) as ctx:
            run_part(root, 0, commands=[["job.py"]], required_outputs=["results/out.json"],
                     timeout_seconds=2, apply_limits=False, report_path=report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        raw = Path(report["raw_output_directory"]) / "results/out.json"
        self.assertEqual(json.loads(raw.read_text(encoding="utf-8")), {"value": 2})
        self.assertEqual(report["retained_raw_generated_files"], ["results/out.json"])
        self.assertIn("semantic", str(ctx.exception))
        self.assertTrue(report["baseline_tree_unchanged"])


if __name__ == "__main__":
    unittest.main()
