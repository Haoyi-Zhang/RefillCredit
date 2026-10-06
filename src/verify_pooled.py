"""Separate scalar verification of pooled hierarchy certificates.

No simulator or game-solver imports. A checked policy is interpreted as a
physical mapping; scalar logical semantics supply every visible observation.
"""
from __future__ import annotations
import itertools, json
from pathlib import Path
from verify_hierarchy import ZERO, SYMBOLS, ingress, service, require
from verify_pool import verify as verify_pool

ROOT=(*ZERO,-1,-1)


def check_encoding(obj):
    ann=obj['hierarchy_encoding']; nodes=obj['nodes']; reverse={}
    require(set(ann)==set(nodes),'encoding domain differs')
    for name,a in ann.items():
        h=tuple(a['hierarchy_state']); key=(a['phase'],h)
        require(len(h)==9 and key not in reverse,'invalid encoding')
        reverse[key]=name
    require(reverse.get(('sample',ZERO))==obj['initial'],'wrong root')
    checked=0
    for name,node in nodes.items():
        h=tuple(ann[name]['hierarchy_state']);phase=ann[name]['phase'];live={}
        if h[7]>0:live['a']=[0,1]
        if h[8]>0:live['b']=[h[6]]
        require(node['live']==live,'wrong token interval or compatibility')
        if phase=='sample':
            transitions={f'{x},{y}':reverse.get(('grant',ingress(h,(x,y))[0])) for x,y in itertools.product(SYMBOLS,repeat=2)}
        else:
            require(phase=='grant','wrong boundary')
            nxt,_=service(h,((-1,()),(-1,())))
            transitions={'clock':reverse.get(('sample',nxt))}
        stated={e['input']:e['to'] for e in node['edges']}
        require(len(stated)==len(node['edges']) and stated==transitions and None not in transitions.values(),'wrong transition')
        checked+=len(transitions)
    return reverse,checked


def reference_step(state,inputs,capacities,contract=None,cert=None,lookup=None):
    h=tuple(state[:9]);slots=list(state[9:]);mid,out=ingress(h,inputs)
    if cert is not None:
        node=lookup['sample',h]
        wanted=(node,tuple(slots[t] for t in (0,1) if h[7+t]))
        ids={ (q,tuple(m)):i for i,(q,m) in enumerate(cert['states']) } if lookup.get('ids') is None else lookup['ids']
        sid=ids[wanted];grantid=cert['winning_policy'][str(sid)][f'{inputs[0]},{inputs[1]}']
        grantnode,_=cert['states'][grantid]
        require(grantnode==lookup['grant',mid],'sample refinement fails')
        after,observed=service(mid,out)
        endid=cert['winning_policy'][str(grantid)]['clock'];endnode,mapping=cert['states'][endid]
        require(endnode==lookup['sample',after],'grant refinement fails')
        binding=dict(zip(sorted(contract['nodes'][endnode]['live']),mapping))
        return (*after,binding.get('a',-1),binding.get('b',-1)),observed
    physical=[b for b,c in enumerate(capacities) for _ in range(c)]
    q=list(mid);seen=[[a,list(done)] for a,done in out]
    for tenant in (0,1):
        if h[7+tenant]==0 and q[7+tenant]>0:
            allowed={0,1} if tenant==0 else {q[5+tenant]}
            candidates=[i for i,b in enumerate(physical) if b in allowed and i not in slots]
            if candidates:slots[tenant]=candidates[0]
            else:q[5+tenant]=h[5+tenant];q[7+tenant]=h[7+tenant];seen[tenant][0]=0
    after,observed=service(tuple(q),tuple((a,tuple(d)) for a,d in seen))
    for tenant in (0,1):
        if after[7+tenant]==0:slots[tenant]=-1
    return (*after,*slots),observed


def verify(raw,contract=None,cert=None,limit=150000):
    caps=raw['capacities'];observer=raw['observer'];policy=raw['policy'];lookup=None
    require(type(observer) is int and observer in (0,1) and policy in ('first-fit','certified'),'bad observation or policy')
    require(len(caps)==2 and all(type(n) is int and n>=0 for n in caps) and sum(caps)<=8,'bad capacities')
    if policy=='certified':
        require(contract is not None and cert is not None,'missing policy evidence')
        require(caps==contract['capacities'] and cert['semantics']=='persistent' and cert['conclusion']=='realizable','wrong contract or policy')
        verify_pool(contract,cert);lookup,_=check_encoding(contract)
        lookup['ids']={(q,tuple(m)):i for i,(q,m) in enumerate(cert['states'])}
    else:contract=cert=None
    def move(s,u):return reference_step(s,u,caps,contract,cert,lookup)
    def successors(pair):
        for own,left,right in itertools.product(SYMBOLS,repeat=3):
            u=(own,left) if observer==0 else (left,own)
            v=(own,right) if observer==0 else (right,own)
            s,x=move(pair[0],u);t,y=move(pair[1],v)
            yield (s,t),x[observer],y[observer]
    root=(ROOT,ROOT);count=0
    if raw['conclusion']=='noninterference':
        listed=[(tuple(a),tuple(b)) for a,b in raw['closed_relation']];relation=set(listed)
        require(root in relation and len(relation)==len(listed),'bad relation')
        reached={root};todo=[root]
        while todo:
            for nxt,x,y in successors(todo.pop()):
                count+=1;require(x==y and nxt in relation,'not an observationally closed relation')
                if nxt not in reached:reached.add(nxt);todo.append(nxt)
                require(len(reached)<=limit,'verification limit exceeded; no verdict')
        require(reached==relation,'unreachable relation states')
        require(raw['visited_pairs']==len(relation) and raw['checked_edges']==count and raw['shortest_ticks'] is None,'incorrect summary')
        return {'pair_states':len(relation),'checked_edges':count,'shortest_ticks':None}
    require(raw['conclusion']=='interference','bad verdict');trace=raw['trace'];k=raw['shortest_ticks']
    require(type(k) is int and k==len(trace) and k>0,'bad length')
    pair=root
    for i,event in enumerate(trace):
        u=tuple(event['left_input']);v=tuple(event['right_input'])
        require(len(u)==len(v)==2 and u[observer]==v[observer],'unequal own input')
        a,x=move(pair[0],u);b,y=move(pair[1],v);x=x[observer];y=y[observer]
        require([x[0],list(x[1])]==event['left_output'] and [y[0],list(y[1])]==event['right_output'],'false observations')
        require((x!=y)==(i==k-1),'not first distinction at last event');pair=(a,b)
    reached={root};layer={root}
    for depth in range(1,k):
        following=set()
        for pair in layer:
            for nxt,x,y in successors(pair):
                count+=1;require(x==y,'a shorter distinction exists')
                if nxt not in reached:following.add(nxt)
        reached.update(following);layer=following
        require(len(reached)<=limit,'verification limit exceeded; no verdict')
    return {'pair_states':len(reached),'checked_edges':count,'shortest_ticks':k}

if __name__=='__main__':
    import argparse,time,resource
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,default=Path('results'))
    a=p.parse_args();start=time.process_time();wall=time.monotonic();rows=[]
    resource.setrlimit(resource.RLIMIT_CPU,(40,40));resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),)*2)
    for path in sorted(a.results.glob('pooled-*-*-?.json')):
        raw=json.loads(path.read_text());stem='hierarchy-pool-'+''.join(map(str,raw['capacities']))
        obj=json.loads((a.results.parent/'inputs'/f'{stem}.json').read_text())
        cert=json.loads((a.results/f'{stem}.certificate.json').read_text())
        rows.append({'file':path.name,**verify(raw,obj,cert)})
    require(len(rows)==10,'expected exact ten pooled cases')
    out={'case_count':len(rows),'all_checks_passed':True,'cases':rows,'workers':1,'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (a.results/'pooled-verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='cases'}))
