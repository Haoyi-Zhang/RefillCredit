"""Connect a certified credit allocator to the two-level toy hierarchy.

Physical state appends the current slot of each tenant's pending credit to the
logical hierarchy state. Slots are deliberately absent from observations.
"""
from __future__ import annotations
import itertools,json
from collections import deque
from pathlib import Path
from hierarchy import EMPTY,ALPHABET,step

ROOT=(*EMPTY,-1,-1)


class Machine:
    def __init__(self,capacities,contract=None,certificate=None):
        self.capacities=tuple(capacities)
        if len(self.capacities)!=2 or any(type(n) is not int or n<0 for n in self.capacities) or sum(self.capacities)>8:raise ValueError('two bounded banks required')
        self.banks=tuple(b for b,n in enumerate(capacities) for _ in range(n))
        self.contract=contract;self.cert=certificate
        if certificate is not None:
            if certificate['conclusion']!='realizable':raise ValueError('initial state must be winning')
            self.lookup={}
            for i,(node,mapping) in enumerate(certificate['states']):
                a=contract['hierarchy_encoding'][node]
                self.lookup[(a['phase'],tuple(a['hierarchy_state']),tuple(mapping))]=i

    def tick(self,state,inputs):
        if not isinstance(inputs,(tuple,list)) or len(inputs)!=2 or any(type(a) is not int or a not in ALPHABET for a in inputs):
            raise ValueError('two integer inputs from the finite alphabet required')
        s=tuple(state[:9]);old=list(state[9:])
        if self.cert is not None:
            active=tuple(old[t] for t in (0,1) if s[7+t])
            sid=self.lookup['sample',s,active]
            mid=self.cert['winning_policy'][str(sid)][f'{inputs[0]},{inputs[1]}']
            end=self.cert['winning_policy'][str(mid)]['clock']
            node,mapping=self.cert['states'][end]
            ns=tuple(self.contract['hierarchy_encoding'][node]['hierarchy_state'])
            reference,outputs=step(s,inputs)
            if reference!=ns:raise ValueError('one-tick refinement diagram does not commute')
            assignments=dict(zip(sorted(self.contract['nodes'][node]['live']),mapping))
            return (*ns,assignments.get('a',-1),assignments.get('b',-1)),outputs
        # Baseline: mandatory local admission is attempted with the lowest free slot.
        q=list(s);accept=[-1,-1];done=[[],[]]
        for t,a in enumerate(inputs):
            if a==-1:continue
            if q[7+t]:accept[t]=0;continue
            if q[1+t]==a:accept[t]=1;done[t].append(a);continue
            eligible=(0,1) if t==0 else (a,)
            choices=[i for i,b in enumerate(self.banks) if b in eligible and i not in old]
            if not choices:accept[t]=0;continue
            old[t]=choices[0];accept[t]=1;q[5+t]=a;q[7+t]=1 if q[3+t]==a else 2
        ns,completion=step(tuple(q),(-1,-1))
        for t in (0,1):
            done[t].extend(completion[t][1])
            if ns[7+t]==0:old[t]=-1
        return (*ns,*old),tuple((accept[t],tuple(done[t])) for t in (0,1))


def reference_first_fit(state,inputs,capacities):
    # Independent scalar ingress/service implementation; producer is not called.
    from verify_hierarchy import ingress,service
    h=tuple(state[:9]); loc=list(state[9:]); phys=[]
    for b in range(2):phys.extend([b]*capacities[b])
    tentative,observed=ingress(h,inputs)
    q=list(tentative); obs=[[a,list(done)] for a,done in observed]
    for t in (0,1):
        if h[7+t]==0 and q[7+t]>0:
            bank_requirement=set(range(2)) if t==0 else {q[5+t]}
            chosen=None
            for j,b in enumerate(phys):
                if b in bank_requirement and j not in loc:chosen=j;break
            if chosen is None:
                q[5+t]=h[5+t];q[7+t]=h[7+t];obs[t][0]=0
            else:loc[t]=chosen
    ns,no=service(tuple(q),tuple((a,tuple(done)) for a,done in obs))
    for t in (0,1):
        if ns[7+t]==0:loc[t]=-1
    return (*ns,*loc),no


def check(machine:Machine,observer:int,limit:int=150000):
    root=(ROOT,ROOT);pairs=[root];index={root:0};todo=deque([0]);parent={};edges=0
    while todo:
        sid=todo.popleft();p,q=pairs[sid]
        left_moves={};right_moves={}
        for a,b,c in itertools.product(ALPHABET,repeat=3):
            u=(a,b) if observer==0 else (b,a);v=(a,c) if observer==0 else (c,a)
            if u not in left_moves:left_moves[u]=machine.tick(p,u)
            ns,x=left_moves[u]
            if v not in right_moves:right_moves[v]=machine.tick(q,v)
            nt,y=right_moves[v];edges+=1
            entry={'left_input':list(u),'right_input':list(v),'left_output':x[observer],'right_output':y[observer]}
            if x[observer]!=y[observer]:
                trace=[entry];cur=sid
                while cur in parent:cur,z=parent[cur];trace.append(z)
                trace.reverse()
                return {'observer':observer,'conclusion':'interference','shortest_ticks':len(trace),
                        'trace':trace,'visited_pairs':len(pairs),'checked_edges':edges}
            pair=(ns,nt)
            if pair not in index:
                if len(pairs)>=limit:raise RuntimeError('state limit exceeded; no verdict')
                index[pair]=len(pairs);pairs.append(pair);todo.append(index[pair]);parent[index[pair]]=(sid,entry)
    return {'observer':observer,'conclusion':'noninterference','shortest_ticks':None,
            'closed_relation':[[list(a),list(b)] for a,b in pairs],
            'visited_pairs':len(pairs),'checked_edges':edges}


def verify_first_fit_reference(machine:Machine):
    if machine.cert is not None:raise ValueError('this oracle is for first-fit only')
    seen={ROOT};todo=[ROOT];count=0
    while todo:
        s=todo.pop()
        for u in itertools.product(ALPHABET,repeat=2):
            actual=machine.tick(s,u);reference=reference_first_fit(s,u,machine.capacities)
            if actual!=reference:raise ValueError('first-fit transition implementations disagree')
            count+=1
            if actual[0] not in seen:seen.add(actual[0]);todo.append(actual[0])
    return {'reachable_physical_states':len(seen),'reference_transitions':count}


if __name__=='__main__':
    import argparse,time,resource
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('results'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    resource.setrlimit(resource.RLIMIT_CPU,(40,40));resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),)*2)
    start=time.process_time();wall=time.monotonic();rows=[]
    for caps in [(1,1),(1,2),(2,1)]:
        stem='hierarchy-pool-'+''.join(map(str,caps))
        obj=json.loads((a.output.parent/'inputs'/f'{stem}.json').read_text())
        cert=json.loads((a.output/f'{stem}.certificate.json').read_text())
        for policy in ['first-fit']+(['certified'] if cert['conclusion']=='realizable' else []):
            machine=Machine(caps,obj if policy=='certified' else None,cert if policy=='certified' else None)
            independent=verify_first_fit_reference(machine) if policy=='first-fit' else None
            for observer in (0,1):
                result=check(machine,observer);result.update({'capacities':list(caps),'policy':policy})
                name='pooled-'+''.join(map(str,caps))+'-'+policy+'-'+str(observer)
                (a.output/f'{name}.json').write_text(json.dumps(result,indent=2)+'\n')
                rows.append({k:v for k,v in result.items() if k not in ('closed_relation','trace')}|{'first_fit_reference':independent})
    result={'case_count':len(rows),'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1,'cases':rows}
    (a.output/'pooled-hierarchy.json').write_text(json.dumps(result,indent=2)+'\n')
    for r in rows:print({k:v for k,v in r.items() if k!='first_fit_reference'})
    print({k:v for k,v in result.items() if k!='cases'})
