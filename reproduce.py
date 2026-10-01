"""Reproduce seven bounded parts without modifying the retained baseline.

Each part copies this standalone repository into an external temporary directory,
removes that part's explicitly required generated files from the copy, reruns the
commands there, and compares the new artifacts with the retained repository.
No command executes in the retained repository. Missing outputs, unexpected
tracked outputs, semantic differences, child failures, and timeouts are errors.

Run: python reproduce.py --part 0   ...   python reproduce.py --part 6
An optional --report path must be outside the repository; without it the report
is printed only to standard output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parent
IGNORED_RESULT_FIELDS = frozenset(
    {
        "cpu_seconds",
        "wall_seconds",
        "peak_rss_kib",
        "core_recorded_cpu_seconds",
        "largest_recorded_process_rss_kib",
    }
)
TRACKED_DIRS = ("inputs", "results", "tables")


class ReproductionFailure(RuntimeError):
    """A reproduction failure with a machine-readable partial report."""

    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


def normalize_result(value: Any) -> Any:
    """Drop only declared nondeterministic measurement fields, recursively."""
    if isinstance(value, dict):
        return {
            key: normalize_result(item)
            for key, item in value.items()
            if key not in IGNORED_RESULT_FIELDS
        }
    if isinstance(value, list):
        return [normalize_result(item) for item in value]
    return value


def child_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (40, 40))
    resource.setrlimit(resource.RLIMIT_AS, (int(3.5 * 1024**3),) * 2)


def jobs(part: int) -> list[list[str]]:
    if part == 0:
        return [
            ["src/campaign.py", "forks"],
            ["src/campaign.py", "hierarchy"],
            ["src/campaign.py", "integration"],
        ]
    if part == 1:
        return [["src/campaign.py", "graphs", "--block", str(i)] for i in range(0, 6)]
    if part == 2:
        return [["src/campaign.py", "graphs", "--block", str(i)] for i in range(6, 11)]
    if part == 3:
        return [["src/campaign.py", "graphs", "--block", str(i)] for i in range(11, 17)]
    if part == 4:
        return [
            ["src/pooled_hierarchy.py"],
            ["src/verify_pooled.py"],
            ["src/uniform.py"],
            ["src/pair_bank.py", "--case", "pilot"],
        ] + [
            ["src/pair_bank.py", "--case", kind, "--observer", str(observer)]
            for kind in ("protected", "negative")
            for observer in (0, 1)
        ]
    if part == 5:
        return [
            ["src/greedy.py", "--case", "pilot"],
            ["src/greedy.py", "--case", "two-bank"],
        ] + [
            ["src/greedy.py", "--case", "three-bank", "--block", str(i)]
            for i in range(4)
        ]
    if part == 6:
        return [
            ["src/recheck_pilots.py"],
            ["src/oracle_crosscheck.py"],
            ["src/check_tests.py"],
            ["src/audit_reference_ledger.py"],
            ["src/report.py"],
            ["src/audit_results.py"],
        ]
    raise ValueError("part must be in 0..6")


def expected_outputs(part: int) -> tuple[str, ...]:
    """The complete required generated-file contract for one part."""
    if part == 0:
        modes = (
            "protected",
            "global-credit",
            "skip-idle",
            "foreign-two-level-invalidate",
            "foreign-fill",
        )
        pool_stems = ("02", "11", "12", "21", "22")
        files = ["results/forks.json", "results/hierarchy.json", "results/transition-equivalence.json"]
        files += [f"results/hierarchy-{mode}-{observer}.json" for mode in modes for observer in (0, 1)]
        files += ["results/integration.json"]
        files += [f"results/hierarchy-pool-{stem}.certificate.json" for stem in pool_stems]
        files += [f"inputs/hierarchy-pool-{stem}.json" for stem in pool_stems]
        return tuple(files)
    if part == 1:
        return tuple(f"results/graphs-{i:02d}.json" for i in range(0, 6))
    if part == 2:
        return tuple(f"results/graphs-{i:02d}.json" for i in range(6, 11))
    if part == 3:
        return tuple(f"results/graphs-{i:02d}.json" for i in range(11, 17))
    if part == 4:
        pooled = [
            f"results/pooled-{caps}-{policy}-{observer}.json"
            for caps, policies in (("11", ("first-fit",)), ("12", ("first-fit", "certified")), ("21", ("first-fit", "certified")))
            for policy in policies
            for observer in (0, 1)
        ]
        return tuple(
            pooled
            + [
                "results/pooled-hierarchy.json",
                "results/pooled-verification.json",
                "results/uniform.json",
                "results/pair-bank-pilot.json",
                "results/pair-bank-protected-0.json",
                "results/pair-bank-protected-1.json",
                "results/pair-bank-negative-0.json",
                "results/pair-bank-negative-1.json",
            ]
        )
    if part == 5:
        return tuple(
            ["results/greedy-pilot.json", "results/greedy-two-bank.json"]
            + [f"results/greedy-three-bank-{i}.json" for i in range(4)]
        )
    if part == 6:
        return (
            "results/pilot-recheck.json",
            "results/oracle-crosscheck.json",
            "results/unit-tests.json",
            "results/reference-ledger-audit.json",
            "results/summary.json",
            "results/numerical-audit.json",
            "tables/policy-independence.csv",
            "tables/fork-capacity.csv",
            "tables/reserve-graphs.csv",
            "tables/uniform-capacity.csv",
            "tables/integration.csv",
            "tables/hierarchy.csv",
            "tables/pooled-hierarchy.csv",
        )
    raise ValueError("part must be in 0..6")


def _tracked_files(root: Path) -> set[str]:
    tracked: set[str] = set()
    for directory in TRACKED_DIRS:
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                tracked.add(path.relative_to(root).as_posix())
    return tracked


def _tree_fingerprint(root: Path) -> dict[str, str]:
    """Hash repository content while ignoring disposable Python caches."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        out[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _same_generated(baseline: Path, generated: Path, relative: str) -> bool:
    left = baseline / relative
    right = generated / relative
    if relative.startswith("results/") and relative.endswith(".json"):
        return normalize_result(json.loads(left.read_text(encoding="utf-8"))) == normalize_result(
            json.loads(right.read_text(encoding="utf-8"))
        )
    if relative.startswith("inputs/") and relative.endswith(".json"):
        return json.loads(left.read_text(encoding="utf-8")) == json.loads(right.read_text(encoding="utf-8"))
    return left.read_bytes() == right.read_bytes()


def _run_child(
    stage_root: Path,
    job: Sequence[str],
    env: dict[str, str],
    timeout_seconds: float,
    apply_limits: bool,
) -> dict[str, Any]:
    command = [sys.executable, *job]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=stage_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=child_limits if apply_limits else None,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    elapsed = time.monotonic() - started
    return {
        "command": ["python", *job],
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "wall_seconds": elapsed,
        "stdout": stdout,
        "stderr": stderr,
    }


def _safe_report_path(root: Path, report_path: Path | None) -> Path | None:
    if report_path is None:
        return None
    resolved_root = root.resolve()
    resolved_report = report_path.resolve()
    if resolved_report == resolved_root or resolved_root in resolved_report.parents:
        raise ValueError("--report must be outside the retained repository")
    return resolved_report


def _write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_part(
    root: Path,
    part: int,
    *,
    commands: Sequence[Sequence[str]] | None = None,
    required_outputs: Sequence[str] | None = None,
    timeout_seconds: float = 42.0,
    apply_limits: bool = True,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Run one part against an immutable baseline and return its report."""
    root = root.resolve()
    command_list = [list(job) for job in (commands if commands is not None else jobs(part))]
    required = tuple(required_outputs if required_outputs is not None else expected_outputs(part))
    if len(required) != len(set(required)):
        raise ValueError("required output list contains duplicates")
    if not required:
        raise ValueError("required output list is empty")
    for relative in required:
        p = Path(relative)
        if p.is_absolute() or ".." in p.parts or p.parts[0] not in TRACKED_DIRS:
            raise ValueError(f"invalid required output path: {relative}")

    safe_report = _safe_report_path(root, report_path)
    baseline_before = _tree_fingerprint(root)
    baseline_assets = _tracked_files(root)
    missing_baseline = sorted(set(required) - baseline_assets)
    if missing_baseline:
        report = {
            "part": part,
            "all_commands_succeeded": False,
            "semantic_results_equal": False,
            "baseline_tree_unchanged": True,
            "error": "retained baseline lacks required comparison files",
            "missing_baseline_files": missing_baseline,
            "regenerated_files": sorted(required),
            "retained_files": sorted(baseline_assets - set(required)),
            "commands": [],
        }
        _write_report(safe_report, report)
        raise ReproductionFailure(report["error"], report)

    before_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    completed: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "part": part,
        "all_commands_succeeded": False,
        "semantic_results_equal": False,
        "required_outputs_complete": False,
        "baseline_tree_unchanged": False,
        "commands": completed,
        "regenerated_files": sorted(required),
        "retained_files": sorted(baseline_assets - set(required)),
        "ignored_nondeterministic_result_fields": sorted(IGNORED_RESULT_FIELDS),
    }

    try:
        with tempfile.TemporaryDirectory(prefix=f"tenant-isolation-reproduce-{part}-") as tmp:
            stage_root = Path(tmp) / "repository"
            shutil.copytree(
                root,
                stage_root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            for relative in required:
                target = stage_root / relative
                if target.exists():
                    target.unlink()
                target.parent.mkdir(parents=True, exist_ok=True)

            env = dict(
                os.environ,
                OMP_NUM_THREADS="1",
                OPENBLAS_NUM_THREADS="1",
                PYTHONDONTWRITEBYTECODE="1",
            )
            for job in command_list:
                child = _run_child(stage_root, job, env, timeout_seconds, apply_limits)
                completed.append(child)
                if child["stdout"]:
                    print(child["stdout"], end="")
                if child["stderr"]:
                    print(child["stderr"], end="", file=sys.stderr)
                if child["timed_out"]:
                    raise ReproductionFailure(
                        "child timed out: " + " ".join(child["command"]), report
                    )
                if child["exit_code"] != 0:
                    raise ReproductionFailure(
                        "child failed: " + " ".join(child["command"]), report
                    )

            stage_assets = _tracked_files(stage_root)
            required_set = set(required)
            missing_generated = sorted(required_set - stage_assets)
            missing_retained = sorted((baseline_assets - required_set) - stage_assets)
            unexpected = sorted(stage_assets - baseline_assets)
            report.update(
                {
                    "missing_generated_files": missing_generated,
                    "missing_retained_files": missing_retained,
                    "unexpected_tracked_files": unexpected,
                }
            )
            if missing_generated:
                raise ReproductionFailure("required generated output is missing", report)
            if missing_retained:
                raise ReproductionFailure("a retained tracked file was deleted", report)
            if unexpected:
                raise ReproductionFailure("an undeclared tracked output was created", report)

            changed_generated = [
                relative
                for relative in sorted(required_set)
                if not _same_generated(root, stage_root, relative)
            ]
            changed_retained = [
                relative
                for relative in sorted(baseline_assets - required_set)
                if (root / relative).read_bytes() != (stage_root / relative).read_bytes()
            ]
            report.update(
                {
                    "semantic_mismatches": changed_generated,
                    "modified_retained_files": changed_retained,
                    "compared_regenerated_files": len(required_set),
                    "verified_retained_files_unchanged": len(baseline_assets - required_set),
                    "required_outputs_complete": True,
                }
            )
            if changed_generated:
                raise ReproductionFailure("semantic mismatch in regenerated output", report)
            if changed_retained:
                raise ReproductionFailure("a non-regenerated retained file changed", report)

            report["all_commands_succeeded"] = True
            report["semantic_results_equal"] = True
    except ReproductionFailure as exc:
        report["error"] = str(exc)
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report["error"] = f"comparison or staging error: {exc}"
        raise ReproductionFailure(report["error"], report) from exc
    finally:
        after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        report.update(
            {
                "child_cpu_seconds": (after_usage.ru_utime + after_usage.ru_stime)
                - (before_usage.ru_utime + before_usage.ru_stime),
                "wall_seconds": time.monotonic() - started,
                "max_child_rss_kib": after_usage.ru_maxrss,
                "measurement_note": "maximum individual child RSS, not aggregate system RSS; children run sequentially in an isolated copy",
            }
        )
        baseline_after = _tree_fingerprint(root)
        report["baseline_tree_unchanged"] = baseline_after == baseline_before
        if not report["baseline_tree_unchanged"]:
            report["error"] = "retained repository changed during reproduction"
        _write_report(safe_report, report)

    if not report["baseline_tree_unchanged"]:
        raise ReproductionFailure(report["error"], report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", required=True, type=int, choices=range(7))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_part(ROOT, args.part, report_path=args.report)
    except ReproductionFailure as exc:
        print(json.dumps(exc.report, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"reproduction configuration error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
