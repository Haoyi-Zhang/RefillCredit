"""Bounded deterministic finite validation; one process, no network or subprocesses.

Commands select resumable chunks. The cases are generated mathematical models,
not architectural workloads. Runtime measurements are CPU checker costs only.
"""
from __future__ import annotations
import argparse,csv,itertools,json,resource,time
from pathlib import Path
from pool import Contract,solve,pointwise_hall,fork
from contracts import graph_choice,independent_number,hierarchy_contract,check_hierarchy_encoding
from verify_pool import verify as verify_pool
from hierarchy import pair_check,MODES,EMPTY,step
from verify_hierarchy import verify as verify_hierarchy,tick


def run(case:str,out:Path,block:int=0):
    if not __debug__:raise ValueError('run validation without Python optimization')
    start=time.process_time();clock=time.monotonic(); out.mkdir(parents=True,exist_ok=True)
    rows=[];name=case+(f'-{block:02d}' if case=='graphs' else '')
    if case=='forks':
        for m,c,n in itertools.product((2,3),(1,2),(1,2)):
            for caps in itertools.product(range(4),repeat=m):
                if sum(caps)>6:continue
                obj=fork(m,c,n,caps);config=Contract.load(obj)
                hall=pointwise_hall(config); cert=solve(config); remap=solve(config,True)
                verify_pool(obj,cert);verify_pool(obj,remap)
                # Closed-form oracles are independent of the game implementation.
                instant=all(x>=c for x in caps) and sum(caps)>=n+c
                online=all(x>=c for x in caps) and sum(caps)>=m*c+n
                assert hall['passes']==instant
                assert (cert['conclusion']=='realizable')==online
                assert (remap['conclusion']=='realizable')==instant
                rows.append({'m':m,'c':c,'n':n,'capacities':list(caps),'hall':instant,
                    'persistent':online,'rematching':instant,**cert['summary']})
    elif case=='graphs':
        # Seventeen fixed chunks: m<=4 in block 0, sixteen blocks of 64 masks for m=5.
        if not 0<=block<=16:raise ValueError('graph block must be 0..16')
        groups=[(m,range(1,1<<(m*(m-1)//2))) for m in (2,3,4)] if block==0 else [(5,range(max(1,(block-1)*64),min(1024,block*64)))]
        for m,masks in groups:
            for mask in masks:
                alpha=independent_number(m,mask)
                for n in range(1,m):
                    obj=graph_choice(m,n,mask);config=Contract.load(obj)
                    cert=solve(config); verify_pool(obj,cert);hall=pointwise_hall(config)
                    assert hall['passes']
                    assert (cert['conclusion']=='realizable')==(n<=alpha)
                    rows.append({'m':m,'incumbents':n,'edge_mask':mask,'alpha':alpha,
                        'hall':True,'persistent':n<=alpha,**cert['summary']})
    elif case=='hierarchy':
        for mode in MODES:
            for observer in (0,1):
                raw=pair_check(mode,observer)
                # Serialized formats, rather than in-memory tuples, cross the checker boundary.
                raw=json.loads(json.dumps(raw));verified=verify_hierarchy(raw)
                path=out/f'hierarchy-{mode}-{observer}.json'
                path.write_text(json.dumps(raw,indent=2)+'\n')
                rows.append({k:v for k,v in raw.items() if k not in ('closed_relation','trace')}|{'verification':verified})
        # Exact one-run transition equivalence on each mode's entire reachable closure.
        totals=[]
        for mode in MODES:
            seen={EMPTY};todo=[EMPTY];edges=0
            while todo:
                s=todo.pop()
                for u in itertools.product((-1,0,1),repeat=2):
                    actual=step(s,u,mode); reference=tick(s,u,mode)
                    assert actual==reference,('semantics disagree',mode,s,u)
                    edges+=1
                    if actual[0] not in seen:seen.add(actual[0]);todo.append(actual[0])
            totals.append({'mode':mode,'states':len(seen),'transitions':edges})
        (out/'transition-equivalence.json').write_text(json.dumps(totals,indent=2)+'\n')
    elif case=='integration':
        for caps in ((0,2),(1,1),(2,1),(1,2),(2,2)):
            obj=hierarchy_contract(caps);config=Contract.load(obj)
            cert=solve(config);checks=check_hierarchy_encoding(obj);checks.update(verify_pool(obj,cert))
            identifier='hierarchy-pool-'+''.join(map(str,caps))
            (out.parent/'inputs').mkdir(exist_ok=True)
            (out.parent/'inputs'/f'{identifier}.json').write_text(json.dumps(obj,indent=2)+'\n')
            (out/f'{identifier}.certificate.json').write_text(json.dumps(cert,indent=2)+'\n')
            rows.append({'name':identifier,'capacities':list(caps),'hall':pointwise_hall(config)['passes'],
                         'conclusion':cert['conclusion'],**cert['summary'],**checks})
    else:raise ValueError('unknown campaign')
    result={'family':case,'block':block,'workers':1,'randomness':'none; complete stated parameter grids',
            'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-clock,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'case_count':len(rows),'all_oracle_checks_passed':True,'cases':rows}
    (out/f'{name}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('case',choices=('forks','graphs','hierarchy','integration'))
    p.add_argument('--block',type=int,default=0);p.add_argument('--output',type=Path,default=Path('results'))
    a=p.parse_args()
    # 3.5 GiB virtual-address-space cap is stronger than the project's RSS ceiling.
    resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),int(3.5*1024**3)))
    resource.setrlimit(resource.RLIMIT_CPU,(40,40))
    run(a.case,a.output,a.block)
