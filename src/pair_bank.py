"""Two-level logical hierarchy with two-out-of-three bank compatibility.

Owned finite mathematical model. No hardware execution, workloads, attack
reproduction, or measured device timings. Capacity is an abstract slot count.
"""
from __future__ import annotations
import itertools,json,resource,time
from pathlib import Path
from collections import deque
ROOT=(0,-1,-1,-1,-1,-1,-1,0,0,-1,-1)
INPUT=(-1,0,1,2)


def transition(state,symbols,capacities=(1,1,1)):
    if not isinstance(symbols,(tuple,list)) or len(symbols)!=2 or any(type(a) is not int or a not in INPUT for a in symbols):raise ValueError('two integer input symbols required')
    q=list(state);answers=[[-1,[]],[-1,[]]];banks=[b for b,n in enumerate(capacities) for _ in range(n)]
    for t,a in enumerate(symbols):
        if a not in INPUT:raise ValueError('bad input')
        if a==-1:continue
        if q[7+t]:answers[t][0]=0;continue
        if q[1+t]==a:answers[t]=[1,[a]];continue
        free=[j for j,b in enumerate(banks) if b!=a and j not in q[9:]]
        if not free:answers[t][0]=0;continue
        q[9+t]=free[0];q[5+t]=a;q[7+t]=1 if q[3+t]==a else 2;answers[t][0]=1
    t=q[0]
    if q[7+t]==2:
        q[3+t]=q[5+t]
        if q[1+t]!=q[5+t]:q[1+t]=-1
        q[7+t]=1
    elif q[7+t]==1:
        q[1+t]=q[5+t];answers[t][1].append(q[5+t]);q[5+t]=-1;q[7+t]=0;q[9+t]=-1
    q[0]=1-q[0]
    return tuple(q),tuple((a,tuple(d)) for a,d in answers)


def reference(state,symbols,capacities=(1,1,1),logical=False):
    # Independent dictionary-based semantics; no transition() call.
    if not isinstance(symbols,(tuple,list)) or len(symbols)!=2 or any(type(a) is not int or a not in INPUT for a in symbols):raise ValueError('two integer input symbols required')
    p=state[0];local={i:dict(near=state[1+i],far=state[3+i],pending=state[5+i],stage=state[7+i],slot=state[9+i]) for i in (0,1)}
    obs={i:dict(accept=-1,done=[]) for i in (0,1)};physical=[]
    for bank,count in enumerate(capacities):physical.extend([bank]*count)
    for i in (0,1):
        r=local[i];a=symbols[i]
        if a not in INPUT:raise ValueError('bad input')
        if a<0:continue
        if r['stage']!=0:obs[i]['accept']=0
        elif r['near']==a:obs[i]['accept']=1;obs[i]['done'].append(a)
        else:
            chosen=next((j for j,b in enumerate(physical) if b!=a and all(j!=local[k]['slot'] for k in (0,1))),None)
            if chosen is None and not logical:obs[i]['accept']=0
            else:
                obs[i]['accept']=1;r['pending']=a;r['stage']=1 if r['far']==a else 2;r['slot']=-1 if logical else chosen
    owner=local[p]
    if owner['stage']==1:
        owner['near']=owner['pending'];obs[p]['done'].append(owner['pending']);owner['stage']=0;owner['pending']=-1;owner['slot']=-1
    elif owner['stage']==2:
        owner['far']=owner['pending']
        if owner['near']!=owner['pending']:owner['near']=-1
        owner['stage']=1
    out=(1-p,*(local[i]['near'] for i in (0,1)),*(local[i]['far'] for i in (0,1)),*(local[i]['pending'] for i in (0,1)),*(local[i]['stage'] for i in (0,1)),*(local[i]['slot'] for i in (0,1)))
    return out,tuple((obs[i]['accept'],tuple(obs[i]['done'])) for i in (0,1))


def single_check(capacities):
    seen={ROOT};todo=[ROOT];edges=0;projection_failures=0
    while todo:
        s=todo.pop()
        for u in itertools.product(INPUT,repeat=2):
            ns,obs=transition(s,u,capacities);ref,ro=reference(s,u,capacities)
            if (ns,obs)!=(ref,ro):raise ValueError('transition oracle disagreement')
            logical,lo=reference(s,u,logical=True)
            if ns[:9]!=logical[:9] or obs!=lo:projection_failures+=1
            edges+=1
            if ns not in seen:seen.add(ns);todo.append(ns)
            if len(seen)>100000:raise RuntimeError('state bound; no verdict')
    return {'physical_states':len(seen),'transitions':edges,'projection_failures':projection_failures}


def paired(capacities,observer):
    if type(observer) is not int or observer not in (0,1):raise ValueError('bad observer')
    if len(capacities)!=3 or any(type(c) is not int or c<0 for c in capacities) or sum(capacities)>8:raise ValueError('bad capacities')
    root=(ROOT,ROOT);seen={root:0};states=[root];todo=deque([root]);parent={};edges=0
    while todo:
        pair=todo.popleft()
        for a,b,c in itertools.product(INPUT,repeat=3):
            u=(a,b) if observer==0 else (b,a);v=(a,c) if observer==0 else (c,a)
            s,x=transition(pair[0],u,capacities);t,y=transition(pair[1],v,capacities);edges+=1
            entry={'left_input':list(u),'right_input':list(v),'left_output':x[observer],'right_output':y[observer]}
            if x[observer]!=y[observer]:
                trace=[entry];cur=pair
                while cur in parent:cur,z=parent[cur];trace.append(z)
                trace.reverse()
                return {'conclusion':'interference','shortest_ticks':len(trace),'trace':trace,'visited_pairs':len(seen),'checked_edges':edges}
            nxt=(s,t)
            if nxt not in seen:
                seen[nxt]=len(states);states.append(nxt);todo.append(nxt);parent[nxt]=(pair,entry)
                if len(seen)>150000:raise RuntimeError('paired state bound; no verdict')
    return {'conclusion':'noninterference','shortest_ticks':None,'closed_relation':[[list(a),list(b)] for a,b in states],'visited_pairs':len(states),'checked_edges':edges}


def verify(raw):
    caps=raw['capacities'];i=raw['observer'];root=(ROOT,ROOT);count=0
    if type(i) is not int or i not in (0,1) or not isinstance(caps,list) or len(caps)!=3:raise ValueError('bad parameters')
    if any(type(c) is not int or c<0 for c in caps) or sum(caps)>8:raise ValueError('bad capacities')
    def moves(pair):
        for a,b,c in itertools.product(INPUT,repeat=3):
            u=(a,b) if i==0 else (b,a);v=(a,c) if i==0 else (c,a)
            s,x=reference(pair[0],u,caps);t,y=reference(pair[1],v,caps)
            yield (s,t),x[i],y[i]
    if raw['conclusion']=='noninterference':
        if raw['shortest_ticks'] is not None:raise ValueError('positive certificate has a difference length')
        listed=[(tuple(a),tuple(b)) for a,b in raw['closed_relation']];rel=set(listed)
        if root not in rel or len(rel)!=len(listed):raise ValueError('bad relation')
        seen={root};todo=[root]
        while todo:
            for nxt,x,y in moves(todo.pop()):
                count+=1
                if x!=y or nxt not in rel:raise ValueError('relation not closed')
                if nxt not in seen:seen.add(nxt);todo.append(nxt)
        if rel!=seen or len(rel)!=raw['visited_pairs'] or count!=raw['checked_edges']:raise ValueError('incorrect relation counts')
    elif raw['conclusion']=='interference':
        k=raw['shortest_ticks'];trace=raw['trace'];pair=root
        if type(k) is not int or k!=len(trace) or k<1:raise ValueError('incorrect length')
        for j,e in enumerate(trace):
            u=tuple(e['left_input']);v=tuple(e['right_input'])
            if len(u)!=2 or len(v)!=2 or any(type(a) is not int or a not in INPUT for a in u+v):raise ValueError('bad trace input')
            if u[i]!=v[i]:raise ValueError('unequal own inputs')
            s,x=reference(pair[0],u,caps);t,y=reference(pair[1],v,caps);x=x[i];y=y[i]
            if [x[0],list(x[1])]!=e['left_output'] or [y[0],list(y[1])]!=e['right_output'] or (x!=y)!=(j==k-1):raise ValueError('incorrect trace')
            pair=(s,t)
        layer={root};seen={root}
        for _ in range(1,k):
            after=set()
            for pair in layer:
                for nxt,x,y in moves(pair):
                    count+=1
                    if x!=y:raise ValueError('trace not shortest')
                    if nxt not in seen:after.add(nxt)
            seen.update(after);layer=after
    else:raise ValueError('unknown verdict')
    return {'independent_obligations':count,'checked':True}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',choices=('pilot','protected','negative'),default='pilot');p.add_argument('--observer',type=int,choices=(0,1),default=0);p.add_argument('--output',type=Path,default=Path('results'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);start=time.process_time();wall=time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU,(40,40));resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),)*2)
    caps=(1,1,1) if a.case!='negative' else (1,1,0)
    if a.case=='pilot':
        result={'positive':single_check((1,1,1)),'negative':single_check((1,1,0))}
        if result['positive']['projection_failures'] or not result['negative']['projection_failures']:raise ValueError('pilot failed discrimination')
        stem='pair-bank-pilot'
    else:
        result=paired(caps,a.observer);result.update({'capacities':list(caps),'observer':a.observer})
        result=json.loads(json.dumps(result));result['verification']=verify(result);stem=f'pair-bank-{a.case}-{a.observer}'
    result.update({'workers':1,'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    (a.output/f'{stem}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('closed_relation','trace')}))
