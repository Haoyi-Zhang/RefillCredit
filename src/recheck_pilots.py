"""Recheck retained exploratory pilot semantics without replacing original timings."""
import json
from pathlib import Path
from pool import Contract, solve, pointwise_hall
from contracts import graph_choice, independent_number, hierarchy_contract, check_hierarchy_encoding
from verify_pool import verify

ROOT=Path(__file__).resolve().parents[1]

def run():
    checks=0
    for row in json.loads((ROOT/'results/pilot.json').read_text())['cases']:
        name=row['case'];obj=json.loads((ROOT/'inputs'/f'{name}.json').read_text());c=Contract.load(obj)
        actual=solve(c);remap=solve(c,True)
        cert=json.loads((ROOT/'results'/f'{name}.certificate.json').read_text())
        verify(obj,cert);verify(obj,actual);verify(obj,remap)
        assert actual==cert, 'retained pilot certificate changed'
        assert row['hall']==pointwise_hall(c)['passes']
        assert row['persistent']==actual['conclusion'] and row['rematching']==remap['conclusion']
        assert all(row[k]==v for k,v in actual['summary'].items())
        checks+=1
    for row in json.loads((ROOT/'results/integration-pilot.json').read_text())['cases']:
        name=row['name']
        if name.startswith('hierarchy-pool-'):
            caps=tuple(map(int,name.rsplit('-',1)[1]));obj=hierarchy_contract(caps)
            oracle=check_hierarchy_encoding(obj)
        else:
            _,m,n,g=name.split('-');m,n,g=int(m[1:]),int(n[1:]),int(g[1:])
            obj=graph_choice(m,n,g);oracle={'independence':independent_number(m,g)}
        c=Contract.load(obj);cert=solve(c);oracle.update(verify(obj,cert))
        actual={'conclusion':cert['conclusion'],'hall':pointwise_hall(c)['passes'],**cert['summary'],**oracle}
        assert all(row[k]==v for k,v in actual.items() if k in row),name
        checks+=1
    result={'retained_pilot_cases_rechecked':checks,'semantic_checks_passed':True,
            'timing_note':'original exploratory timing records retained, not re-created'}
    (ROOT/'results/pilot-recheck.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':print(json.dumps(run()))
