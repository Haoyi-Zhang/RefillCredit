"""Small independent oracle for finite persistent-credit contracts.

This module deliberately imports no project solver or certificate checker.  It
reconstructs the state graph with permutations and solves the safety game over
hashable state tuples.  The implementation is intended only for small owned
models used as a common-mode cross-check, not as a scalable solver or a formal
proof kernel.
"""
from __future__ import annotations

import itertools
from typing import Any


class OracleInputError(ValueError):
    """Raised when an input is outside the tiny oracle's explicit boundary."""


def _parse(obj: dict[str, Any]) -> tuple[tuple[int, ...], str, dict[str, dict[str, tuple[int, ...]]], dict[str, tuple[tuple[str, str], ...]]]:
    if not isinstance(obj, dict):
        raise OracleInputError("contract must be an object")
    name = obj.get("name")
    if not isinstance(name, str) or not name:
        raise OracleInputError("name must be a nonempty string")
    capacities_raw = obj.get("capacities")
    if not isinstance(capacities_raw, list) or not capacities_raw:
        raise OracleInputError("capacities must be a nonempty list")
    if any(type(c) is not int or c < 0 for c in capacities_raw):
        raise OracleInputError("capacities must be nonnegative integers")
    capacities = tuple(capacities_raw)
    if sum(capacities) > 6:
        raise OracleInputError("tiny-oracle limit is six slots")

    nodes_raw = obj.get("nodes")
    if not isinstance(nodes_raw, dict) or not nodes_raw:
        raise OracleInputError("nodes must be a nonempty object")
    live_by_node: dict[str, dict[str, tuple[int, ...]]] = {}
    edges_by_node: dict[str, tuple[tuple[str, str], ...]] = {}
    for node, spec in nodes_raw.items():
        if not isinstance(node, str) or not node or not isinstance(spec, dict):
            raise OracleInputError("invalid node")
        live_raw = spec.get("live")
        edges_raw = spec.get("edges")
        if not isinstance(live_raw, dict) or not isinstance(edges_raw, list) or not edges_raw:
            raise OracleInputError("each node needs live and nonempty edges")
        live: dict[str, tuple[int, ...]] = {}
        for token, eligible_raw in live_raw.items():
            if not isinstance(token, str) or not token:
                raise OracleInputError("invalid token")
            if not isinstance(eligible_raw, list) or not eligible_raw or len(set(eligible_raw)) != len(eligible_raw):
                raise OracleInputError("invalid eligibility")
            if any(type(bank) is not int or bank < 0 or bank >= len(capacities) for bank in eligible_raw):
                raise OracleInputError("eligibility outside bank set")
            live[token] = tuple(sorted(eligible_raw))
        edges: list[tuple[str, str]] = []
        labels: set[str] = set()
        for edge in edges_raw:
            if not isinstance(edge, dict):
                raise OracleInputError("edge must be an object")
            label, target = edge.get("input"), edge.get("to")
            if not isinstance(label, str) or not label or not isinstance(target, str) or not target:
                raise OracleInputError("invalid edge")
            if label in labels:
                raise OracleInputError("duplicate input label")
            labels.add(label)
            edges.append((label, target))
        live_by_node[node] = dict(sorted(live.items()))
        edges_by_node[node] = tuple(edges)

    initial = obj.get("initial")
    if not isinstance(initial, str) or initial not in live_by_node or live_by_node[initial]:
        raise OracleInputError("initial node must exist and be empty")
    for node, edges in edges_by_node.items():
        for _, target in edges:
            if target not in live_by_node:
                raise OracleInputError("unknown destination")
            for token in live_by_node[node].keys() & live_by_node[target].keys():
                if live_by_node[node][token] != live_by_node[target][token]:
                    raise OracleInputError("persistent token changed type")
    reachable = {initial}
    work = [initial]
    while work:
        node = work.pop()
        for _, target in edges_by_node[node]:
            if target not in reachable:
                reachable.add(target)
                work.append(target)
    if reachable != set(live_by_node):
        raise OracleInputError("unreachable logical node")
    return capacities, initial, live_by_node, edges_by_node


def _assignments(live: dict[str, tuple[int, ...]], slot_banks: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    tokens = tuple(sorted(live))
    if len(tokens) > len(slot_banks):
        return ()
    return tuple(
        placement
        for placement in itertools.permutations(range(len(slot_banks)), len(tokens))
        if all(slot_banks[slot] in live[token] for token, slot in zip(tokens, placement))
    )


def solve_tiny(obj: dict[str, Any], rematching: bool = False) -> dict[str, Any]:
    """Return a compact exact verdict and ranks for a contract with <=6 slots."""
    capacities, initial, live_by_node, edges_by_node = _parse(obj)
    slot_banks = tuple(bank for bank, count in enumerate(capacities) for _ in range(count))
    assignments = {node: _assignments(live, slot_banks) for node, live in live_by_node.items()}
    states = tuple((node, placement) for node in live_by_node for placement in assignments[node])
    state_set = set(states)
    if (initial, ()) not in state_set:
        raise OracleInputError("initial physical state missing")

    successors: dict[tuple[str, tuple[int, ...]], tuple[tuple[str, tuple[tuple[str, tuple[int, ...]], ...]], ...]] = {}
    edge_count = 0
    for state in states:
        node, placement = state
        incumbent = dict(zip(sorted(live_by_node[node]), placement))
        moves: list[tuple[str, tuple[tuple[str, tuple[int, ...]], ...]]] = []
        for label, target in edges_by_node[node]:
            candidates: list[tuple[str, tuple[int, ...]]] = []
            for next_placement in assignments[target]:
                candidate = dict(zip(sorted(live_by_node[target]), next_placement))
                if not rematching and any(
                    candidate[token] != incumbent[token]
                    for token in live_by_node[node].keys() & live_by_node[target].keys()
                ):
                    continue
                candidates.append((target, next_placement))
            edge_count += len(candidates)
            moves.append((label, tuple(candidates)))
        successors[state] = tuple(moves)

    ranks: dict[tuple[str, tuple[int, ...]], int] = {}
    spoiling_input: dict[tuple[str, tuple[int, ...]], str] = {}
    while True:
        layer: dict[tuple[str, tuple[int, ...]], tuple[int, str]] = {}
        for state in states:
            if state in ranks:
                continue
            candidates: list[tuple[int, str]] = []
            for label, next_states in successors[state]:
                if all(next_state in ranks for next_state in next_states):
                    candidates.append((1 + max((ranks[next_state] for next_state in next_states), default=0), label))
            if candidates:
                layer[state] = min(candidates)
        if not layer:
            break
        for state, (rank, label) in layer.items():
            ranks[state] = rank
            spoiling_input[state] = label

    start = (initial, ())
    winning = state_set - ranks.keys()
    return {
        "semantics": "rematching" if rematching else "persistent",
        "conclusion": "realizable" if start in winning else "unrealizable",
        "snapshot_feasible": all(assignments[node] for node in live_by_node),
        "states": len(states),
        "winning_states": len(winning),
        "losing_states": len(ranks),
        "logical_inputs": sum(len(edges_by_node[node]) for node, _ in states),
        "allocator_edges": edge_count,
        "initial_rejection_depth": ranks.get(start),
        "max_rank": max(ranks.values(), default=0),
        "losing_ranks": {repr(state): rank for state, rank in sorted(ranks.items(), key=lambda item: repr(item[0]))},
        "spoiling_inputs": {repr(state): spoiling_input[state] for state in sorted(ranks, key=repr)},
    }
