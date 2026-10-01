"""Two-tenant, two-level read-only hierarchy with a finite synchronous clock.

Only the declared accept/completion alphabet is observable. No real devices,
external services, exploit primitives, or timing measurements are involved.
"""
from __future__ import annotations
from collections import deque
import itertools,json
from pathlib import Path
from typing import Any

# State = (phase, L1[0], L1[1], L2[0], L2[1], address[0], address[1], stage[0], stage[1]).
# -1 denotes an empty cache or no pending address; stage 0 means no pending refill.
EMPTY=(0,-1,-1,-1,-1,-1,-1,0,0)
ALPHABET=(-1,0,1)
MODES=('protected','global-credit','skip-idle','foreign-two-level-invalidate','foreign-fill')


def step(s: tuple[int,...], inputs: tuple[int,int], mode: str='protected') -> tuple[tuple[int,...],tuple[Any,...]]:
    if mode not in MODES: raise ValueError('unknown mode')
    phase=s[0]; l1=list(s[1:3]);l2=list(s[3:5]);addr=list(s[5:7]);stage=list(s[7:9])
    accept=[-1,-1];done=[[],[]]
    # Input sampling precedes service. Busy-at-sampling requests are rejected,
    # even if the old transaction will retire later in this same abstract tick.
    for t,a in enumerate(inputs):
        if a==-1:continue
        if a not in (0,1):raise ValueError('input outside finite alphabet')
        if stage[t]!=0:
            accept[t]=0;continue
        # Hits do not require a refill credit.
        if l1[t]==a:
            accept[t]=1;done[t].append(a);continue
        if mode=='global-credit' and sum(x!=0 for x in stage)>=1:
            accept[t]=0;continue
        accept[t]=1;addr[t]=a;stage[t]=1 if l2[t]==a else 2
    selected=phase
    if mode=='skip-idle' and stage[selected]==0:
        selected=1-selected
    t=selected
    if stage[t]==2:
        a=addr[t];l2[t]=a
        if l1[t]!=a:l1[t]=-1
        stage[t]=1
        if mode=='foreign-two-level-invalidate':
            # Deliberately invalidate both private cache levels of the other tenant.
            l1[1-t]=-1; l2[1-t]=-1
        if mode=='foreign-fill':l2[1-t]=a
    elif stage[t]==1:
        a=addr[t];l1[t]=a;done[t].append(a);stage[t]=0;addr[t]=-1
    ns=(1-phase,*l1,*l2,*addr,*stage)
    observations=tuple((accept[t],tuple(done[t])) for t in range(2))
    return ns,observations


def pair_check(mode: str, observer: int=0, limit: int=150000) -> dict[str,Any]:
    """Exact two-run reachability, not bounded trace sampling.

    The observer's input is equal in both runs at each tick. The other input
    is universally and independently varied in each run. BFS gives a
    minimum-tick distinguishing prefix for a fixed deterministic model.
    """
    if observer not in (0,1):raise ValueError('observer must be 0 or 1')
    root=(EMPTY,EMPTY); states=[root];index={root:0}; parent={};todo=deque([0]);edges=0
    for_nodes=[]
    while todo:
        sid=todo.popleft();s0,s1=states[sid]
        for low,h0,h1 in itertools.product(ALPHABET,repeat=3):
            u0=(low,h0) if observer==0 else (h0,low)
            u1=(low,h1) if observer==0 else (h1,low)
            n0,o0=step(s0,u0,mode);n1,o1=step(s1,u1,mode);edges+=1
            if o0[observer]!=o1[observer]:
                trace=[{'left_input':list(u0),'right_input':list(u1),
                        'left_output':o0[observer],'right_output':o1[observer]}]
                p=sid
                while p in parent:
                    p,entry=parent[p];trace.append(entry)
                trace.reverse()
                return {'mode':mode,'observer':observer,'conclusion':'interference',
                        'shortest_ticks':len(trace),'trace':trace,
                        'visited_pairs':len(states),'checked_edges':edges}
            pair=(n0,n1)
            if pair not in index:
                if len(states)>=limit:raise RuntimeError('pair-state limit exceeded; no verdict')
                nid=len(states);index[pair]=nid;states.append(pair);todo.append(nid)
                parent[nid]=(sid,{'left_input':list(u0),'right_input':list(u1),
                                 'left_output':o0[observer],'right_output':o1[observer]})
    return {'mode':mode,'observer':observer,'conclusion':'noninterference',
            'shortest_ticks':None,'visited_pairs':len(states),'checked_edges':edges,
            'closed_relation':[[list(a),list(b)] for a,b in states]}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=MODES,default='protected')
    p.add_argument('--observer',type=int,choices=(0,1),default=0);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=pair_check(a.mode,a.observer);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('closed_relation','trace')}))
