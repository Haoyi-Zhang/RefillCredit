"""Independent finite certificate checker, with a permutation-based oracle.

Does not import the game solver. This checks a finite mathematical model;
it is not a proof-assistant kernel or an independent human review.
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
from typing import Any


def verify(obj: dict[str,Any], cert: dict[str,Any]) -> dict[str,int]:
    if not __debug__: raise ValueError('run the checker without Python optimization')
    assert isinstance(obj,dict) and isinstance(cert,dict), 'input and certificate must be objects'
    assert isinstance(obj.get('name'),str) and obj['name'], 'invalid contract name'
    capacities=obj.get('capacities')
    assert isinstance(capacities,list) and capacities and all(type(c) is int and c>=0 for c in capacities), 'invalid capacities'
    assert sum(capacities)<=8, 'oracle limit'
    slots=tuple(b for b,n in enumerate(capacities) for _ in range(n))
    nodes=obj.get('nodes'); initial=obj.get('initial')
    assert isinstance(nodes,dict) and nodes and all(isinstance(q,str) and q for q in nodes), 'bad node name'
    for spec in nodes.values():
        assert isinstance(spec,dict) and isinstance(spec.get('live'),dict) and isinstance(spec.get('edges'),list), 'bad node specification'
        assert spec['edges'], 'dead logical node'
        for e in spec['edges']:
            assert isinstance(e,dict), 'bad edge'
            assert isinstance(e.get('input'),str) and e['input'], 'bad input label'
            assert isinstance(e.get('to'),str) and e['to'], 'bad destination'
    assert isinstance(initial,str) and initial in nodes and not nodes[initial]['live'], 'invalid initial node'
    seen={initial}; todo=[initial]
    while todo:
        q=todo.pop()
        assert len({e['input'] for e in nodes[q]['edges']})==len(nodes[q]['edges']), 'duplicate input'
        for e in nodes[q]['edges']:
            assert e['to'] in nodes,'unknown destination'
            if e['to'] not in seen: seen.add(e['to']);todo.append(e['to'])
    assert seen==set(nodes), 'unreachable logical node'
    expected=set(); by_node={}
    for q,spec in nodes.items():
        live=spec['live']; keys=sorted(live)
        for t,bs in live.items():
            assert isinstance(t,str) and t and isinstance(bs,list) and bs and len(set(bs))==len(bs),'bad token'
            assert all(type(b) is int and 0<=b<len(capacities) for b in bs),'bad eligibility'
        by_node[q]=[]
        for perm in itertools.permutations(range(len(slots)),len(keys)):
            if all(slots[s] in live[t] for t,s in zip(keys,perm)):
                state=(q,perm);expected.add(state);by_node[q].append(state)
        for edge in spec['edges']:
            other=nodes[edge['to']]['live']
            assert all(set(live[t])==set(other[t]) for t in live.keys() & other.keys()), 'persistent type changed'
    required={'semantics','conclusion','states','initial','winning_policy','losing','summary'}
    assert required<=set(cert), 'missing certificate field'
    assert isinstance(cert['states'],list) and isinstance(cert['winning_policy'],dict) and isinstance(cert['losing'],dict) and isinstance(cert['summary'],dict), 'bad certificate schema'
    assert all(isinstance(q,str) and isinstance(m,(list,tuple)) and all(type(x) is int for x in m) for q,m in cert['states']), 'bad state encoding'
    stated=[(q,tuple(m)) for q,m in cert['states']]
    assert len(set(stated))==len(stated) and set(stated)==expected, 'incomplete or invalid state universe'
    index={s:i for i,s in enumerate(stated)}
    start=index[initial,()]
    assert type(cert['initial']) is int and cert['initial']==start,'wrong initial state'
    assert all(isinstance(k,str) and k==str(int(k)) for k in cert['winning_policy']), 'bad winning-state key'
    assert all(isinstance(k,str) and k==str(int(k)) for k in cert['losing']), 'bad losing-state key'
    win={int(k) for k in cert['winning_policy']}; lose={int(k) for k in cert['losing']}
    assert not win & lose and win|lose==set(range(len(stated))), 'incomplete partition'
    assert cert['semantics'] in ('persistent','rematching'),'unknown semantics'
    assert cert['conclusion'] in ('realizable','unrealizable'),'unknown conclusion'
    inf=float('inf'); ranks={s:inf for s in win}
    for s in lose:
        item=cert['losing'][str(s)]
        assert isinstance(item,dict) and set(item)=={'rank','input'}, 'bad losing-state record'
        r=item['rank'];assert type(r) is int and r>=1,'bad rank'
        assert isinstance(item['input'],str) and item['input'], 'bad spoiling input'
        ranks[s]=r
    checked=0; successors=0
    for i,(q,mapping) in enumerate(stated):
        incumbent=dict(zip(sorted(nodes[q]['live']),mapping)); scores={}
        liveq=nodes[q]['live']
        labels={e['input'] for e in nodes[q]['edges']}
        if i in win:
            policy=cert['winning_policy'][str(i)]
            assert isinstance(policy,dict) and set(policy)==labels,'missing or extra policy input'
        for edge in nodes[q]['edges']:
            label,dst=edge['input'],edge['to']; target=nodes[dst]['live']
            ids=[]
            for state in by_node[dst]:
                candidate=dict(zip(sorted(target),state[1]))
                if cert['semantics']=='persistent' and any(candidate[t]!=incumbent[t] for t in liveq.keys() & target.keys()):
                    continue
                ids.append(index[state])
            checked+=1;successors+=len(ids)
            scores[label]=1+max((ranks[s] for s in ids),default=0)
            if i in win:
                chosen=cert['winning_policy'][str(i)][label]
                assert type(chosen) is int and chosen in ids and chosen in win,'illegal or nonwinning policy move'
        if i in lose:
            chosen=cert['losing'][str(i)]['input'];r=ranks[i]
            assert chosen in scores and scores[chosen]==r,'bad spoiling choice'
            assert min(scores.values())==r,'rank is not the exact minimax rejection depth'
    expected_verdict='realizable' if start in win else 'unrealizable'
    assert cert['conclusion']==expected_verdict,'wrong conclusion'
    sm=cert['summary']
    expected_summary={'states':len(stated),'winning_states':len(win),'losing_states':len(lose),
        'environment_moves':checked,'allocator_edges':successors,
        'initial_rejection_depth':None if start in win else ranks[start],
        'max_rank':max((ranks[s] for s in lose),default=0)}
    assert sm==expected_summary,'inconsistent summary'
    return {'states_checked':len(stated),'input_obligations_checked':checked,'allocator_edges_checked':successors}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('certificate',type=Path)
    a=p.parse_args()
    try:
        print(json.dumps(verify(json.loads(a.input.read_text()),json.loads(a.certificate.read_text()))))
    except (AssertionError,KeyError,TypeError,ValueError) as e:
        raise SystemExit('REJECTED: '+str(e))
