"""Reproduce in seven bounded, sequential parts; no network and no dependencies.

Run: python reproduce.py --part 0   ...   python reproduce.py --part 6
Each subprocess has its own scientific CPU/address-space bound. At most one
scientific child is active. Semantic results exclude nondeterministic timings.
"""
from __future__ import annotations
import argparse,json,os,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def normalize(value):
    if isinstance(value,dict):return {k:normalize(v) for k,v in value.items() if k not in ('cpu_seconds','wall_seconds','peak_rss_kib','core_recorded_cpu_seconds','largest_recorded_process_rss_kib')}
    if isinstance(value,list):return [normalize(x) for x in value]
    return value


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU,(40,40))
    resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),)*2)

def jobs(part):
    if part==0:return [['src/campaign.py','forks'],['src/campaign.py','hierarchy'],['src/campaign.py','integration']]
    if part==1:return [['src/campaign.py','graphs','--block',str(i)] for i in range(0,6)]
    if part==2:return [['src/campaign.py','graphs','--block',str(i)] for i in range(6,11)]
    if part==3:return [['src/campaign.py','graphs','--block',str(i)] for i in range(11,17)]
    if part==4:return [['src/pooled_hierarchy.py'],['src/verify_pooled.py'],['src/uniform.py'],['src/pair_bank.py','--case','pilot']]+[['src/pair_bank.py','--case',kind,'--observer',str(i)] for kind in ('protected','negative') for i in (0,1)]
    if part==5:return [['src/greedy.py','--case','pilot'],['src/greedy.py','--case','two-bank']]+[['src/greedy.py','--case','three-bank','--block',str(i)] for i in range(4)]
    return [['src/recheck_pilots.py'],['src/oracle_crosscheck.py'],['src/check_tests.py'],['src/audit_reference_ledger.py'],['src/report.py'],['src/audit_results.py']]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--part',required=True,type=int,choices=range(7));a=p.parse_args()
    os.chdir(ROOT);start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    snapshots={p.name:normalize(json.loads(p.read_text())) for p in (ROOT/'results').glob('*.json') if not p.name.startswith('reproduction-')}
    input_snapshots={p.name:json.loads(p.read_text()) for p in (ROOT/'inputs').glob('*.json')}
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    completed=[]
    for job in jobs(a.part):
        r=subprocess.run([sys.executable,*job],env=env,capture_output=True,text=True,timeout=42,preexec_fn=child_limits)
        print(r.stdout,end='');print(r.stderr,end='',file=sys.stderr)
        completed.append({'command':['python',*job],'exit_code':r.returncode})
        if r.returncode:raise SystemExit(r.returncode)
    compared=[]
    for name,old in snapshots.items():
        now=ROOT/'results'/name
        if now.exists() and normalize(json.loads(now.read_text()))!=old:raise SystemExit('semantic mismatch: '+name)
        compared.append(name)
    for name,old in input_snapshots.items():
        if json.loads((ROOT/'inputs'/name).read_text())!=old:raise SystemExit('input mismatch: '+name)
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    result={'part':a.part,'all_commands_succeeded':True,'semantic_results_equal':True,'commands':completed,'compared_result_files':len(compared),'compared_input_files':len(input_snapshots),
       'child_cpu_seconds':(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime),'wall_seconds':time.monotonic()-start,'max_child_rss_kib':after.ru_maxrss,
       'measurement_note':'maximum individual child RSS, not aggregate system RSS; parent orchestrates sequentially'}
    (ROOT/'results'/f'reproduction-{a.part}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
