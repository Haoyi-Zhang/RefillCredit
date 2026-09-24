"""Derive compact tables from retained raw finite results (no simulations)."""
import csv,json
from pathlib import Path


def build(root):
    result=root/'results'; tables=root/'tables';tables.mkdir(exist_ok=True)
    graphs=[x for i in range(17) for x in json.loads((result/f'graphs-{i:02d}.json').read_text())['cases']]
    forks=json.loads((result/'forks.json').read_text())['cases']
    uniform=json.loads((result/'uniform.json').read_text())['cases']
    greedy=json.loads((result/'greedy-two-bank.json').read_text())['cases'] + [row for block in range(4) for row in json.loads((result/f'greedy-three-bank-{block}.json').read_text())['cases']]
    if len(greedy)!=1225:raise ValueError('incomplete greedy family')
    if (len(graphs),len(forks),len(uniform))!=(4296,280,80):raise ValueError('incomplete families')
    datasets={'policy-independence':greedy,'fork-capacity':forks,'reserve-graphs':graphs,'uniform-capacity':uniform,
              'integration':json.loads((result/'integration.json').read_text())['cases'],
              'hierarchy':json.loads((result/'hierarchy.json').read_text())['cases'],
              'pooled-hierarchy':json.loads((result/'pooled-hierarchy.json').read_text())['cases']}
    for name,rows in datasets.items():
        keys=list(dict.fromkeys(k for row in rows for k in row))
        with (tables/f'{name}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
            w.writerows({k:json.dumps(v,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in rows)
    scientific=[result/'oracle-crosscheck.json',result/'forks.json',result/'hierarchy.json',result/'integration.json',result/'pooled-hierarchy.json',result/'pooled-verification.json',result/'uniform.json']
    scientific += [result/f'graphs-{i:02d}.json' for i in range(17)]
    scientific += [result/'pair-bank-pilot.json'] + sorted(result.glob('pair-bank-protected-?.json'))+sorted(result.glob('pair-bank-negative-?.json'))
    scientific += [result/'greedy-two-bank.json'] + [result/f'greedy-three-bank-{b}.json' for b in range(4)]
    measurements=[json.loads(p.read_text()) for p in scientific]
    summary={'fork_cases':len(forks),'fork_pointwise_feasible':sum(x['hall'] for x in forks),'fork_persistent_feasible':sum(x['persistent'] for x in forks),
       'graph_cases':len(graphs),'graph_persistent_feasible':sum(x['persistent'] for x in graphs),
       'greedy_cases':len(greedy),'greedy_realizable':sum(x['realizable'] for x in greedy),
       'greedy_all_choices_safe':sum(x['all_choices_safe'] for x in greedy),
       'greedy_policy_dependent_realizable':sum(x['realizable'] and not x['all_choices_safe'] for x in greedy),
       'graph_max_mapped_states':max(x['states'] for x in graphs),'uniform_cases':len(uniform),'independent_oracle_cases':json.loads((result/'oracle-crosscheck.json').read_text())['total_contract_cases'],
       'core_recorded_cpu_seconds':sum(x['cpu_seconds'] for x in measurements),'largest_recorded_process_rss_kib':max(x['peak_rss_kib'] for x in measurements),
       'resource_boundary':'one worker per chunk; CPU checker measurements, not device performance',
       'measurement_scope':'main finite campaign and the pair-bank pilot; excludes earlier exploratory pilots, compilation and packaging'}
    (result/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary
if __name__=='__main__':print(json.dumps(build(Path(__file__).resolve().parents[1]),indent=2))
