"""Check the numerical claims reported in the accompanying mathematical article.

This is a deterministic consistency check, not additional scientific evidence or
an independent review. It uses retained raw cases, never a manuscript PDF.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'results'/name).read_text())
def run():
    checked=[]
    def check(label,actual,expected):
        if actual!=expected:raise ValueError(f'{label}: {actual!r} != {expected!r}')
        checked.append({'claim':label,'value':actual})
    f=read('forks.json')['cases'];g=[r for b in range(17) for r in read(f'graphs-{b:02d}.json')['cases']]
    a=read('greedy-two-bank.json')['cases'];b=[r for i in range(4) for r in read(f'greedy-three-bank-{i}.json')['cases']]
    check('fork count / snapshot / persistent',[len(f),sum(r['hall'] for r in f),sum(r['persistent'] for r in f)],[280,61,47])
    check('graph count / persistent / maximum states',[len(g),sum(r['persistent'] for r in g),max(r['states'] for r in g)],[4296,2906,602])
    check('two-bank independent-tenant cases / winning / all choices',[len(a),sum(r['realizable'] for r in a),sum(r['all_choices_safe'] for r in a)],[441,150,104])
    check('three-bank independent-tenant cases / winning / all choices',[len(b),sum(r['realizable'] for r in b),sum(r['all_choices_safe'] for r in b)],[784,598,160])
    check('policy-dependent winning cases',sum(r['realizable'] and not r['all_choices_safe'] for r in a+b),484)
    u=read('uniform.json')['cases'];check('uniform count',len(u),80)
    for dims,want in [((3,2,2),(3,4)),((6,4,3),(10,16))]:
        row=next(r for r in u if (r['banks'],r['tenants'],r['eligibility_size'])==dims)
        check('uniform optima '+str(dims),[row['pooled_minimum'],row['dedicated_minimum']],list(want))
    for row,want in zip(read('integration.json')['cases'],[(312,0,1),(312,0,3),(594,510,None),(594,510,None),(972,972,None)]):
        check(row['name']+' integration',[row['states'],row['winning_states'],row['initial_rejection_depth']],list(want))
        check(row['name']+' encoding',[row['logical_nodes'],row['transitions_checked']],[252,972])
    cases=[('11','first-fit',0,640,17280,None),('11','first-fit',1,11,11,1),
      ('12','first-fit',0,834,22518,None),('12','first-fit',1,11,11,1),
      ('12','certified',0,1306,35262,None),('12','certified',1,1318,35586,None),
      ('21','first-fit',0,1024,27648,None),('21','first-fit',1,1070,28890,None),
      ('21','certified',0,1024,27648,None),('21','certified',1,1070,28890,None)]
    for caps,pol,obs,pairs,edges,depth in cases:
        r=read(f'pooled-{caps}-{pol}-{obs}.json')
        check(f'physical {caps} {pol} observer {obs}',[r['visited_pairs'],r['checked_edges'],r['shortest_ticks']],[pairs,edges,depth])
    for mode,depths in [('global-credit',(2,1)),('skip-idle',(2,2)),('foreign-two-level-invalidate',(5,6)),('foreign-fill',(3,2))]:
        check('logical fault '+mode,[read(f'hierarchy-{mode}-{i}.json')['shortest_ticks'] for i in (0,1)],list(depths))
    for i in (0,1):
        r=read(f'hierarchy-protected-{i}.json');check('logical protected '+str(i),[r['visited_pairs'],r['checked_edges']],[630,17010])
    for kind,i,pairs,edges,depth in [('protected',0,5602,358528,None),('protected',1,5734,366976,None),('negative',0,86,145,2),('negative',1,18,18,1)]:
        r=read(f'pair-bank-{kind}-{i}.json');check(f'pair-bank {kind} {i}',[r['visited_pairs'],r['checked_edges'],r['shortest_ticks']],[pairs,edges,depth])
    pilot=read('pair-bank-pilot.json')
    check('pair-bank single positive',[pilot['positive']['physical_states'],pilot['positive']['transitions'],pilot['positive']['projection_failures']],[334,5344,0])
    check('pair-bank single negative',[pilot['negative']['physical_states'],pilot['negative']['transitions'],pilot['negative']['projection_failures']],[232,3712,494])
    oracle=read('oracle-crosscheck.json')
    check('independent tiny-oracle contract cases',oracle['total_contract_cases'],484)
    check('independent tiny-oracle semantic and snapshot comparisons',[oracle['semantic_comparisons'],oracle['snapshot_comparisons']],[764,484])
    check('independent tiny-oracle losing-state ranks',oracle['losing_state_rank_comparisons'],16205)
    r=read('unit-tests.json');check('unit tests',[r['tests_run'],r['failures'],r['errors'],r['successful']],[68,0,0,True])
    out={'all_numerical_checks_passed':True,'checks':checked,'check_count':len(checked)}
    (ROOT/'results/numerical-audit.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':print(json.dumps({k:v for k,v in run().items() if k!='checks'}))
