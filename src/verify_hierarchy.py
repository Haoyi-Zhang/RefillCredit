"""Independently written scalar semantics and finite noninterference verifier.

The transition checker does not import the producer. Positive certificates are
closed two-run relations. Negative witnesses are replayed, and a fresh breadth
layer expansion establishes that no shorter prefix distinguishes observations.
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
from typing import Any

ZERO=(0,-1,-1,-1,-1,-1,-1,0,0)
SYMBOLS=(-1,0,1)
KINDS={'protected','global-credit','skip-idle','foreign-two-level-invalidate','foreign-fill'}


def require(ok: bool, message: str) -> None:
    if not ok: raise ValueError(message)


def ingress(s: tuple[int,...], symbols: tuple[int,int], kind: str='protected'):
    require(kind in KINDS,'unknown model')
    tenants={i:{'near':s[1+i],'far':s[3+i],'request':s[5+i], 'remaining':s[7+i]} for i in (0,1)}
    seen={i:{'admitted':-1,'completed':[]} for i in (0,1)}
    for i in (0,1):
        symbol=symbols[i]; r=tenants[i]
        require(symbol in SYMBOLS,'bad input symbol')
        if symbol < 0: continue
        if r['remaining'] > 0:
            seen[i]['admitted']=0
        elif r['near']==symbol:
            seen[i]['admitted']=1; seen[i]['completed']=[symbol]
        elif kind=='global-credit' and any(tenants[j]['remaining']>0 for j in (0,1)):
            seen[i]['admitted']=0
        else:
            seen[i]['admitted']=1
            r['request']=symbol
            r['remaining']=1 if r['far']==symbol else 2
    mid=(s[0],*(tenants[i]['near'] for i in (0,1)),*(tenants[i]['far'] for i in (0,1)),
         *(tenants[i]['request'] for i in (0,1)),*(tenants[i]['remaining'] for i in (0,1)))
    return mid, tuple((seen[i]['admitted'],tuple(seen[i]['completed'])) for i in (0,1))


def service(mid: tuple[int,...], ingress_outputs, kind: str='protected'):
    q=list(mid); events=[list(ingress_outputs[i][1]) for i in (0,1)]
    owner=q[0]
    if kind=='skip-idle' and q[7+owner]==0: owner=1-owner
    amount=q[7+owner]
    if amount==1:
        q[1+owner]=q[5+owner]; events[owner].append(q[5+owner])
        q[5+owner]=-1; q[7+owner]=0
    elif amount==2:
        q[3+owner]=q[5+owner]
        if q[1+owner]!=q[5+owner]: q[1+owner]=-1
        q[7+owner]=1
        if kind=='foreign-two-level-invalidate':
            # Independent scalar semantics: clear both foreign near and far tags.
            q[2-owner]=-1; q[4-owner]=-1
        if kind=='foreign-fill': q[4-owner]=q[5+owner]
    q[0]=1-q[0]
    return tuple(q),tuple((ingress_outputs[i][0],tuple(events[i])) for i in (0,1))


def tick(s, symbols, kind='protected'):
    mid,observed=ingress(s,symbols,kind)
    return service(mid,observed,kind)


def paired_moves(pair, observer, kind):
    for a,b,c in itertools.product(SYMBOLS,repeat=3):
        u=(a,b) if observer==0 else (b,a)
        v=(a,c) if observer==0 else (c,a)
        p,op=tick(pair[0],u,kind);q,oq=tick(pair[1],v,kind)
        yield (p,q),op[observer],oq[observer]


def verify(cert:dict[str,Any], limit:int=150000) -> dict[str,int]:
    kind=cert['mode']; obs=cert['observer'];require(obs in (0,1),'bad observer')
    root=(ZERO,ZERO); checked=0
    if cert['conclusion']=='noninterference':
        listed=[(tuple(a),tuple(b)) for a,b in cert['closed_relation']]
        relation=set(listed)
        require(len(listed)==len(relation) and root in relation,'invalid relation root or duplicates')
        reachable={root}; pending=[root]
        while pending:
            s=pending.pop()
            for nxt,x,y in paired_moves(s,obs,kind):
                checked+=1;require(x==y,'unequal outputs in positive certificate')
                require(nxt in relation,'relation is not closed')
                if nxt not in reachable:reachable.add(nxt);pending.append(nxt)
        require(reachable==relation,'certificate includes unreachable pair states')
        require(cert['visited_pairs']==len(relation) and cert['checked_edges']==checked,'false counts')
        require(cert['shortest_ticks'] is None,'positive certificate has trace length')
        return {'relation_states':len(relation),'obligations_checked':checked,'trace_ticks':0}
    require(cert['conclusion']=='interference','unknown conclusion')
    trace=cert['trace']; k=cert['shortest_ticks']
    require(type(k) is int and k>0 and k==len(trace),'bad witness length')
    pair=root
    for j,entry in enumerate(trace):
        a=tuple(entry['left_input']);b=tuple(entry['right_input'])
        require(len(a)==len(b)==2 and a[obs]==b[obs],'observer inputs differ')
        p,op=tick(pair[0],a,kind);q,oq=tick(pair[1],b,kind)
        x,y=op[obs],oq[obs]
        require([x[0],list(x[1])]==entry['left_output'],'incorrect left observation')
        require([y[0],list(y[1])]==entry['right_output'],'incorrect right observation')
        require((x!=y)==(j==k-1),'witness does not first distinguish at its last tick')
        pair=(p,q)
    # Search all shorter depths afresh, retaining exact layers and a seen set.
    layer={root};seen={root}
    for depth in range(1,k):
        nxt_layer=set()
        for s in layer:
            for nxt,x,y in paired_moves(s,obs,kind):
                checked+=1;require(x==y,'witness is not shortest')
                if nxt not in seen:nxt_layer.add(nxt)
        seen.update(nxt_layer);layer=nxt_layer
        require(len(seen)<=limit,'independent verification state limit exceeded')
    return {'relation_states':len(seen),'obligations_checked':checked,'trace_ticks':k}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('certificate',type=Path)
    a=p.parse_args()
    try:print(json.dumps(verify(json.loads(a.certificate.read_text()))))
    except (ValueError,KeyError,TypeError) as exc:raise SystemExit('REJECTED: '+str(exc))
