"""Cross-check project solvers against the independent <=6-slot tiny oracle."""
from __future__ import annotations

import itertools
import json
import resource
import time
from pathlib import Path

from contracts import graph_choice
from pool import Contract, fork, pointwise_hall, solve
from tiny_oracle import solve_tiny


def _summary(cert: dict) -> tuple:
    summary = cert["summary"]
    return (
        cert["conclusion"],
        summary["states"],
        summary["winning_states"],
        summary["losing_states"],
        summary["environment_moves"],
        summary["allocator_edges"],
        summary["initial_rejection_depth"],
        summary["max_rank"],
    )


def _oracle_summary(raw: dict) -> tuple:
    return (
        raw["conclusion"],
        raw["states"],
        raw["winning_states"],
        raw["losing_states"],
        raw["logical_inputs"],
        raw["allocator_edges"],
        raw["initial_rejection_depth"],
        raw["max_rank"],
    )


def _certificate_ranks(cert: dict) -> dict[str, int]:
    states = [(node, tuple(mapping)) for node, mapping in cert["states"]]
    return {repr(states[int(index)]): info["rank"] for index, info in cert["losing"].items()}


def _compare(label: tuple, cert: dict, oracle: dict) -> int:
    if _summary(cert) != _oracle_summary(oracle):
        raise ValueError(("tiny-oracle summary mismatch", *label))
    actual_ranks = _certificate_ranks(cert)
    if actual_ranks != oracle["losing_ranks"]:
        raise ValueError(("tiny-oracle rank mismatch", *label))
    return len(actual_ranks)


def run() -> dict:
    start_cpu = time.process_time()
    start_wall = time.monotonic()
    fork_cases = 0
    graph_cases = 0
    semantic_comparisons = 0
    rank_comparisons = 0
    snapshot_comparisons = 0

    for m, c, n in itertools.product((2, 3), (1, 2), (1, 2)):
        for capacities in itertools.product(range(4), repeat=m):
            if sum(capacities) > 6:
                continue
            obj = fork(m, c, n, capacities)
            contract = Contract.load(obj)
            persistent = solve(contract)
            rematching = solve(contract, True)
            oracle_persistent = solve_tiny(obj)
            oracle_rematching = solve_tiny(obj, True)
            rank_comparisons += _compare(("persistent", m, c, n, capacities), persistent, oracle_persistent)
            rank_comparisons += _compare(("rematching", m, c, n, capacities), rematching, oracle_rematching)
            hall = pointwise_hall(contract)["passes"]
            if hall != oracle_persistent["snapshot_feasible"]:
                raise ValueError(("snapshot tiny-oracle mismatch", m, c, n, capacities))
            fork_cases += 1
            semantic_comparisons += 2
            snapshot_comparisons += 1

    # Every nonempty simple graph through four banks: 1 + 14 + 189 = 204
    # contract instances after multiplying each graph by n=1..m-1.
    for m in (2, 3, 4):
        edge_count = m * (m - 1) // 2
        for mask in range(1, 1 << edge_count):
            for n in range(1, m):
                obj = graph_choice(m, n, mask)
                contract = Contract.load(obj)
                actual = solve(contract)
                oracle = solve_tiny(obj)
                rank_comparisons += _compare(("graph", m, n, mask), actual, oracle)
                if pointwise_hall(contract)["passes"] != oracle["snapshot_feasible"]:
                    raise ValueError(("graph snapshot tiny-oracle mismatch", m, n, mask))
                graph_cases += 1
                semantic_comparisons += 1
                snapshot_comparisons += 1

    result = {
        "all_crosschecks_passed": True,
        "oracle_boundary": "independent standard-library implementation; at most six slots",
        "fork_cases": fork_cases,
        "small_graph_cases": graph_cases,
        "total_contract_cases": fork_cases + graph_cases,
        "semantic_comparisons": semantic_comparisons,
        "snapshot_comparisons": snapshot_comparisons,
        "losing_state_rank_comparisons": rank_comparisons,
        "workers": 1,
        "cpu_seconds": time.process_time() - start_cpu,
        "wall_seconds": time.monotonic() - start_wall,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    return result


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (40, 40))
    resource.setrlimit(resource.RLIMIT_AS, (int(3.5 * 1024**3),) * 2)
    output = Path("results/oracle-crosscheck.json")
    result = run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("cpu_seconds", "wall_seconds", "peak_rss_kib")}))
