"""Policy-independent admission criterion for independent one-credit tenants.

Inputs are owned finite compatibility families, not hardware workloads. A tenant
may acquire any type in its nonempty family when idle and release when active.
The matching criterion is compared against an explicitly enumerated persistent
game, its independent certificate verifier, and all legal placement successors.
"""
from __future__ import annotations
import itertools, json, resource, time
from pathlib import Path
from pool import Contract, solve, make_graph
from verify_pool import verify


def blocking_matching(capacities, families, target, eligible):
    """Maximum matching from other tenants to slots inside the target set."""
    slots=[b for b,c in enumerate(capacities) for _ in range(c) if b in eligible]
    neighbors={i:[s for s,b in enumerate(slots) if any(b in e for e in f)]
               for i,f in enumerate(families) if i!=target}
    matched={}
    def augment(i,seen):
        for s in neighbors[i]:
            if s in seen:continue
            seen.add(s)
            if s not in matched or augment(matched[s],seen):
                matched[s]=i;return True
        return False
    for i in neighbors:augment(i,set())
    return len(matched),len(slots)


def criterion(capacities,families):
    if not capacities or any(type(c) is not int or c<0 for c in capacities):raise ValueError('bad capacities')
    if not families or any(not f for f in families):raise ValueError('empty family')
    if any(not e or len(set(e))!=len(e) or any(type(b) is not int or b<0 or b>=len(capacities) for b in e) for f in families for e in f):raise ValueError('bad eligibility')
    for i,f in enumerate(families):
        for e in f:
            occupied,total=blocking_matching(capacities,families,i,e)
            if occupied==total:return False
    return True


def contract(capacities,families):
    choices=[range(-1,len(f)) for f in families]
    def key(q):return ','.join(map(str,q))
    nodes={}
    for q in itertools.product(*choices):
        live={f't{i}':list(families[i][kind]) for i,kind in enumerate(q) if kind>=0}
        edges=[{'input':'wait','to':key(q)}]
        for i,kind in enumerate(q):
            if kind>=0:
                nxt=list(q);nxt[i]=-1;edges.append({'input':f'release-{i}','to':key(nxt)})
            else:
                for a in range(len(families[i])):
                    nxt=list(q);nxt[i]=a;edges.append({'input':f'acquire-{i}-{a}','to':key(nxt)})
        nodes[key(q)]={'live':live,'edges':edges}
    return {'name':'independent-tenant-types','capacities':list(capacities),
            'initial':key([-1]*len(families)),'nodes':nodes}


def all_choices_safe(c):
    # Traverse every physical successor, not a synthesized or fixed greedy rule.
    g=make_graph(c);seen={g['initial']};todo=[g['initial']]
    while todo:
        for _,successors in g['adj'][todo.pop()]:
            if not successors:return False
            for s in successors:
                if s not in seen:seen.add(s);todo.append(s)
    return True


def families_for(m,max_types=None):
    types=[tuple(b for b in range(m) if mask>>b&1) for mask in range(1,1<<m)]
    return [tuple(f) for k in range(1,(max_types or len(types))+1)
            for f in itertools.combinations(types,k)]


def examine(caps,families):
    obj=contract(caps,families);c=Contract.load(obj);cert=solve(c)
    verify(obj,json.loads(json.dumps(cert)))
    safe=criterion(caps,families);exhaustive=all_choices_safe(c)
    if safe!=exhaustive:raise ValueError('policy-independent criterion falsified')
    winning=cert['conclusion']=='realizable'
    if safe and not winning:raise ValueError('all-choice safety not realizable')
    return {'capacities':list(caps),'families':[[list(e) for e in f] for f in families],
            'all_choices_safe':safe,'realizable':winning,**cert['summary']}


def run(kind,block=0):
    start=time.process_time();wall=time.monotonic();rows=[]
    if kind=='pilot':
        rows=[examine((1,1),(((0,1),),((0,),(1,)))),
              examine((1,2),(((0,1),),((0,),(1,)))),
              examine((1,1,1),(((0,1),(0,2),(1,2)),)*2)]
        if [(x['all_choices_safe'],x['realizable']) for x in rows]!=[(False,False),(False,True),(True,True)]:
            raise ValueError('pilot did not discriminate all three cases')
    elif kind=='two-bank':
        fs=families_for(2)
        for caps in itertools.product(range(3),repeat=2):
            for f in itertools.product(fs,repeat=2):rows.append(examine(caps,f))
    elif kind=='three-bank':
        fs=families_for(3,2)
        if not 0<=block<4:raise ValueError('block must be 0..3')
        pairs=list(itertools.product(fs,repeat=2))
        for f in pairs[block*196:(block+1)*196]:rows.append(examine((1,1,1),f))
    else:raise ValueError('unknown case')
    return {'family':kind,'block':block,'case_count':len(rows),'cases':rows,
            'all_choices_safe':sum(x['all_choices_safe'] for x in rows),
            'realizable':sum(x['realizable'] for x in rows),'all_oracle_checks_passed':True,
            'workers':1,'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',choices=('pilot','two-bank','three-bank'),default='pilot')
    p.add_argument('--block',type=int,default=0);p.add_argument('--output',type=Path,default=Path('results'));a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU,(40,40));resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),)*2)
    out=run(a.case,a.block);a.output.mkdir(exist_ok=True,parents=True)
    suffix=f'-{a.block}' if a.case=='three-bank' else ''
    (a.output/f'greedy-{a.case}{suffix}.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='cases'}))
