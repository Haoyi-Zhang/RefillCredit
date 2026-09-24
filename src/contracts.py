"""Deterministic families of abstract reservation contracts; no workloads."""
from __future__ import annotations
from itertools import combinations
from collections import deque
import json
from pathlib import Path


def graph_choice(m:int,n:int,edge_mask:int):
    """All n incumbents are flexible; a later singleton chooses an edge's banks."""
    edges=[e for i,e in enumerate(combinations(range(m),2)) if edge_mask>>i&1]
    if not (2<=m and 1<=n<m and edges):raise ValueError('nonempty graph and 0<n<m required')
    flex={f'a{i}':list(range(m)) for i in range(n)}
    nodes={'start':{'live':{},'edges':[{'input':'reserve','to':'hold'}]},
           'hold':{'live':flex,'edges':[]},
           'end':{'live':{},'edges':[{'input':'wait','to':'end'}]}}
    for i,e in enumerate(edges):
        name=f'choice{i}'
        nodes['hold']['edges'].append({'input':f'edge{i}','to':name})
        nodes[name]={'live':{**flex,'b':list(e)},'edges':[{'input':'retire','to':'end'}]}
    return {'name':f'graph-m{m}-n{n}-g{edge_mask}','capacities':[1]*m,'initial':'start','nodes':nodes}


def independent_number(m:int,edge_mask:int)->int:
    # Direct subset oracle: deliberately does not use the contract solver.
    edges=[e for i,e in enumerate(combinations(range(m),2)) if edge_mask>>i&1]
    return max((len(s) for k in range(m+1) for s in combinations(range(m),k)
                if all(not (u in s and v in s) for u,v in edges)),default=0)


def hierarchy_contract(capacities=(1,1)):
    """Reachable two-phase product contract for the exact protected hierarchy.

    Sampling and service have different boundaries so that short-lived credits
    born and retired during the same tick are not erased. A's credit may reside
    in either bank; B's credit is pinned by its (private) request address.
    """
    from hierarchy import EMPTY,ALPHABET
    # Producer semantics are used explicitly, rather than the independent checker.
    def sample(s,inputs):
        q=list(s)
        for t,a in enumerate(inputs):
            if a==-1 or q[7+t]!=0 or q[1+t]==a:continue
            q[5+t]=a;q[7+t]=1 if q[3+t]==a else 2
        return tuple(q)
    def grant(s):
        from hierarchy import step
        return step(s,(-1,-1),'protected')[0]
    def live(s):
        d={}
        if s[7]:d['a']=[0,1]
        if s[8]:d['b']=[s[6]]
        return d
    root=('sample',EMPTY); pairs=[root];ids={root:'q0'};todo=deque([root]);nodes={};annotations={}
    while todo:
        phase,s=todo.popleft();name=ids[phase,s]; es=[]
        actions=[(f'{a},{b}',('grant',sample(s,(a,b)))) for a in ALPHABET for b in ALPHABET] if phase=='sample' else [('clock',('sample',grant(s)))]
        for label,pair in actions:
            if pair not in ids:
                ids[pair]=f'q{len(ids)}';pairs.append(pair);todo.append(pair)
            es.append({'input':label,'to':ids[pair]})
        nodes[name]={'live':live(s),'edges':es}
        annotations[name]={'phase':phase,'hierarchy_state':list(s)}
    return {'name':'two-level-credit-product','capacities':list(capacities),
            'initial':'q0','nodes':nodes,'hierarchy_encoding':annotations}


def check_hierarchy_encoding(obj):
    """Independent transition reconstruction from scalar ingress/service semantics."""
    from verify_hierarchy import ingress,service,ZERO
    from itertools import product
    ann=obj['hierarchy_encoding']; nodes=obj['nodes'];reverse={}
    for q,a in ann.items():
        key=(a['phase'],tuple(a['hierarchy_state']))
        if key in reverse:raise ValueError('duplicate encoded state')
        reverse[key]=q
    if set(ann)!=set(nodes) or reverse.get(('sample',ZERO))!=obj['initial']:
        raise ValueError('incorrect encoded state universe or initial')
    obligations=0
    for q,spec in nodes.items():
        a=ann[q];s=tuple(a['hierarchy_state']);ph=a['phase'];live={}
        if s[7]>0:live['a']=[0,1]
        if s[8]>0:live['b']=[s[6]]
        if spec['live']!=live:raise ValueError('wrong lifetime or eligibility')
        expected={}
        if ph=='sample':
            for x,y in product((-1,0,1),repeat=2):
                mid,_=ingress(s,(x,y));expected[f'{x},{y}']=reverse.get(('grant',mid))
        elif ph=='grant':
            after,_=service(s,((-1,()),(-1,())));expected['clock']=reverse.get(('sample',after))
        else:raise ValueError('unknown boundary')
        got={e['input']:e['to'] for e in spec['edges']}
        if got!=expected or None in expected.values():raise ValueError('incorrect product transition')
        obligations+=len(expected)
    return {'logical_nodes':len(nodes),'transitions_checked':obligations}
