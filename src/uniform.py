"""Exact integer-capacity and private-reservation oracles for uniform eligibility.

Exhaustively checks all m=2..6, n=1..4, s=1..m parameter triples. Capacity vectors
are searched in increasing total cost; each component can be capped at n without
losing a minimum because every demand bound is n. No optimization library used.
"""
from __future__ import annotations
import itertools,json,time,resource
from pathlib import Path


def run():
    start=time.process_time();wall=time.monotonic();rows=[]
    for m in range(2,7):
        for n in range(1,5):
            vectors=sorted(itertools.product(range(n+1),repeat=m),key=lambda c:(sum(c),c))
            for s in range(1,m+1):
                types=list(itertools.combinations(range(m),s));tested=0;subset_checks=0
                optimum=None;best=None
                for caps in vectors:
                    tested+=1;feasible=True
                    for eligible in types:
                        subset_checks+=1
                        if sum(caps[b] for b in eligible)<n:feasible=False;break
                    if feasible:optimum=sum(caps);best=caps;break
                private_min=min(k for k in range(m+1) if any(all(set(owned)&set(e) for e in types) for owned in itertools.combinations(range(m),k)))
                expected=n+(m-s)*((n+s-1)//s);dedicated=n*(m-s+1)
                if optimum!=expected or n*private_min!=dedicated:raise ValueError('capacity formula falsified')
                rows.append({'banks':m,'tenants':n,'eligibility_size':s,'types':len(types),'pooled_minimum':optimum,'dedicated_minimum':n*private_min,'witness_capacity':list(best),'vectors_checked':tested,'subset_checks':subset_checks})
    return {'case_count':len(rows),'cases':rows,'all_oracle_checks_passed':True,'workers':1,'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('results/uniform.json'));a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU,(40,40));resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),)*2)
    out=run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='cases'}))
