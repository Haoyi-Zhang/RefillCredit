"""Exact safety-game solver for finite, non-migrating credit pools.

This is an abstract resource model, not a hardware security-testing tool.
An environment edge releases absent tokens before assigning newly live tokens.
No incumbent may change its slot. Slot identifiers are unobservable.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Contract:
    name: str
    banks: tuple[int, ...]
    initial: str
    nodes: dict[str, dict[str, tuple[int, ...]]]
    edges: dict[str, tuple[tuple[str, str], ...]]

    @property
    def slot_banks(self) -> tuple[int, ...]:
        return tuple(b for b, count in enumerate(self.banks) for _ in range(count))

    @classmethod
    def load(cls, obj: dict[str, Any]) -> 'Contract':
        if not isinstance(obj, dict):
            raise ValueError('contract must be an object')
        contract_name = obj.get('name')
        if not isinstance(contract_name, str) or not contract_name:
            raise ValueError('name must be a nonempty string')
        capacities = obj.get('capacities')
        if not isinstance(capacities, list) or not capacities:
            raise ValueError('capacities must be a nonempty list')
        banks = tuple(capacities)
        if any(type(c) is not int or c < 0 for c in banks):
            raise ValueError('capacities must be nonnegative integers')
        if sum(banks) > 8:
            raise ValueError('enumeration limit: at most eight physical entries')
        raw_nodes = obj.get('nodes')
        if not isinstance(raw_nodes, dict) or not raw_nodes:
            raise ValueError('nodes must be a nonempty object')
        nodes: dict[str, dict[str, tuple[int, ...]]] = {}
        edges: dict[str, tuple[tuple[str, str], ...]] = {}
        for name, spec in raw_nodes.items():
            if not isinstance(name, str) or not name or not isinstance(spec, dict):
                raise ValueError('node names must be nonempty strings with object specifications')
            raw_live = spec.get('live')
            raw_edges = spec.get('edges')
            if not isinstance(raw_live, dict) or not isinstance(raw_edges, list):
                raise ValueError('each node must have a live object and an edge list')
            demands: dict[str, tuple[int, ...]] = {}
            for tok, allowed in raw_live.items():
                if not isinstance(tok, str) or not tok or not isinstance(allowed, list):
                    raise ValueError('invalid token or eligibility list')
                if not allowed or len(allowed) != len(set(allowed)):
                    raise ValueError('empty or duplicated eligibility')
                if any(type(b) is not int or b < 0 or b >= len(banks) for b in allowed):
                    raise ValueError('eligibility outside bank set')
                demands[tok] = tuple(sorted(allowed))
            nodes[name] = dict(sorted(demands.items()))
            parsed_edges: list[tuple[str, str]] = []
            for edge in raw_edges:
                if not isinstance(edge, dict):
                    raise ValueError('edge must be an object')
                label, target = edge.get('input'), edge.get('to')
                if not isinstance(label, str) or not label or not isinstance(target, str) or not target:
                    raise ValueError('invalid edge input or destination')
                parsed_edges.append((label, target))
            es = tuple(parsed_edges)
            if not es or len({label for label, _ in es}) != len(es):
                raise ValueError('each node needs nonempty, uniquely labelled input edges')
            edges[name] = es
        initial = obj.get('initial')
        if not isinstance(initial, str) or initial not in nodes or nodes[initial]:
            raise ValueError('initial node must exist and be empty')
        for node, es in edges.items():
            for _, dst in es:
                if dst not in nodes:
                    raise ValueError('unknown destination')
                for tok in nodes[node].keys() & nodes[dst].keys():
                    if nodes[node][tok] != nodes[dst][tok]:
                        raise ValueError('a persistent token cannot change eligibility')
        reachable = {initial}
        todo = [initial]
        while todo:
            for _, dst in edges[todo.pop()]:
                if dst not in reachable:
                    reachable.add(dst)
                    todo.append(dst)
        if reachable != set(nodes):
            raise ValueError('every logical node must be reachable')
        return cls(contract_name, banks, initial, nodes, edges)



def assignments(demands: dict[str, tuple[int, ...]], slot_banks: tuple[int, ...],
                fixed: dict[str,int] | None = None) -> list[tuple[int,...]]:
    """Enumerate legal injections using incremental backtracking."""
    keys = tuple(demands)
    fixed = fixed or {}
    if any(t not in demands for t in fixed):
        return []
    if len(set(fixed.values())) != len(fixed):
        return []
    for tok,s in fixed.items():
        if s < 0 or s >= len(slot_banks) or slot_banks[s] not in demands[tok]:
            return []
    answer: list[tuple[int,...]] = []
    partial: list[int] = []
    used: set[int] = set()
    def visit(i: int) -> None:
        if i == len(keys):
            answer.append(tuple(partial)); return
        key = keys[i]
        choices = (fixed[key],) if key in fixed else range(len(slot_banks))
        for s in choices:
            if s not in used and slot_banks[s] in demands[key]:
                used.add(s);partial.append(s);visit(i+1);partial.pop();used.remove(s)
    visit(0)
    return answer


def state_key(node: str, mapping: tuple[int,...]) -> str:
    return json.dumps([node,list(mapping)], separators=(',',':'))


def make_graph(c: Contract, remap: bool=False, state_limit: int=100000) -> dict[str, Any]:
    states: list[tuple[str,tuple[int,...]]] = []
    ids: dict[tuple[str,tuple[int,...]],int] = {}
    for node,demands in c.nodes.items():
        for mapping in assignments(demands,c.slot_banks):
            ids[node,mapping] = len(states);states.append((node,mapping))
            if len(states) > state_limit:
                raise RuntimeError('state enumeration limit exceeded; no verdict')
    adj: list[list[tuple[str,list[int]]]] = []
    for node,mapping in states:
        old = dict(zip(c.nodes[node],mapping))
        moves = []
        for label,dst in c.edges[node]:
            fixed = {} if remap else {t:s for t,s in old.items() if t in c.nodes[dst]}
            nxt = [ids[dst,m] for m in assignments(c.nodes[dst],c.slot_banks,fixed)]
            moves.append((label,nxt))
        adj.append(moves)
    return {'states': states, 'adj': adj, 'initial': ids[c.initial,()]}


def solve(c: Contract, remap: bool=False) -> dict[str,Any]:
    g = make_graph(c,remap)
    states,adj = g['states'],g['adj']
    rank: dict[int,int] = {}
    spoil: dict[int,str] = {}
    depth = 1
    # Synchronous attractor layers: one edge is one contract boundary.
    while True:
        remove = {}
        for s,moves in enumerate(adj):
            if s in rank: continue
            for label,nxt in moves:
                if all(t in rank for t in nxt):
                    r = 1 + max((rank[t] for t in nxt),default=0)
                    if s not in remove or r < remove[s][0]:
                        remove[s] = (r,label)
        if not remove:break
        for s,(r,label) in remove.items():rank[s]=r;spoil[s]=label
        depth += 1
    winning = set(range(len(states))) - rank.keys()
    policy = {}
    for s in sorted(winning):
        policy[str(s)] = {label: next(t for t in nxt if t in winning) for label,nxt in adj[s]}
    serial_states = [[node,list(mapping)] for node,mapping in states]
    verdict = 'realizable' if g['initial'] in winning else 'unrealizable'
    return {
        'semantics': 'rematching' if remap else 'persistent',
        'conclusion': verdict,
        'states': serial_states,
        'initial': g['initial'],
        'winning_policy': policy,
        'losing': {str(s): {'rank':rank[s],'input':spoil[s]} for s in sorted(rank)},
        'summary': {
            'states':len(states),'winning_states':len(winning),'losing_states':len(rank),
            'environment_moves':sum(len(x) for x in adj),
            'allocator_edges':sum(len(nxt) for moves in adj for _,nxt in moves),
            'initial_rejection_depth':rank.get(g['initial']),
            'max_rank':max(rank.values(),default=0)
        }
    }


def pointwise_hall(c: Contract) -> dict[str,Any]:
    """Exact all-subset Hall test, forgetting incumbent placement and history."""
    failures=[]; checks=0
    for node,live in c.nodes.items():
        for mask in range(1,1<<len(c.banks)):
            banks={b for b in range(len(c.banks)) if mask>>b&1}
            demand=sum(set(allowed)<=banks for allowed in live.values())
            capacity=sum(c.banks[b] for b in banks)
            checks+=1
            if demand>capacity:
                failures.append({'node':node,'banks':sorted(banks),'demand':demand,'capacity':capacity})
    return {'passes':not failures,'subset_checks':checks,'failures':failures}


def fork(m: int=2, c: int=1, n: int=1, capacities: tuple[int,...] | None=None,
         optional: bool=True) -> dict[str,Any]:
    if m < 2 or c < 1 or n < 1:raise ValueError('invalid fork dimensions')
    all_banks=list(range(m)); flex={f'f{k}':all_banks for k in range(n)}
    nodes={'start':{'live':{},'edges':[{'input':'flex','to':'hold'}]},
           'hold':{'live':flex,'edges':[]},
           'drain':{'live':{},'edges':[{'input':'reset','to':'start'}]}}
    if optional:
        nodes['start']['edges'].append({'input':'idle','to':'idlehold'})
        nodes['idlehold']={'live':{},'edges':[]}
    for j in range(m):
        for origin,prefix,base in [('hold','branch',flex)]+([('idlehold','idlebranch',{})] if optional else []):
            name=f'{prefix}{j}'
            nodes[origin]['edges'].append({'input':f'bank{j}','to':name})
            nodes[name]={'live':{**base,**{f'b{k}':[j] for k in range(c)}},
                         'edges':[{'input':'retire','to':'drain'}]}
    return {'name':f'fork-m{m}-c{c}-n{n}', 'capacities':list(capacities or (c,)*m),
            'initial':'start','nodes':nodes}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--remap',action='store_true')
    args=p.parse_args()
    c=Contract.load(json.loads(args.input.read_text()))
    result=solve(c,args.remap)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'conclusion':result['conclusion'],**result['summary']}))
