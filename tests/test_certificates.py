"""Benign finite-model and certificate mutation tests; no target systems."""
import copy,itertools,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pool import Contract,solve,fork,make_graph,pointwise_hall
from verify_pool import verify as pool_check
from hierarchy import pair_check,step,EMPTY
from verify_hierarchy import verify as trace_check
from contracts import graph_choice,independent_number,hierarchy_contract
from verify_pooled import verify as pooled_check,check_encoding
from tiny_oracle import OracleInputError,solve_tiny

ROOT=Path(__file__).resolve().parents[1]

def serial(o):return json.loads(json.dumps(o))

class PoolCertificateTests(unittest.TestCase):
    def setUp(self):
        self.obj=fork(2,1,1,(2,1));self.c=Contract.load(self.obj);self.cert=solve(self.c)
    def rejects(self,obj,cert):
        with self.assertRaises((ValueError,AssertionError,KeyError,TypeError,IndexError)):
            pool_check(obj,cert)
    def test_positive_certificate(self):pool_check(self.obj,self.cert)
    def test_negative_certificate(self):
        o=fork(2,1,1,(1,1));c=solve(Contract.load(o));pool_check(o,c)
        self.assertEqual(c['summary']['initial_rejection_depth'],2)
    def test_snapshot_does_not_imply_persistence(self):
        c=Contract.load(fork(2,1,1,(1,1)))
        self.assertTrue(pointwise_hall(c)['passes'])
        self.assertEqual(solve(c,True)['conclusion'],'realizable')
        self.assertEqual(solve(c)['conclusion'],'unrealizable')
    def test_missing_state(self):
        c=copy.deepcopy(self.cert);c['states'].pop();self.rejects(self.obj,c)
    def test_duplicate_state(self):
        c=copy.deepcopy(self.cert);c['states'].append(c['states'][0]);self.rejects(self.obj,c)
    def test_false_verdict(self):
        c=copy.deepcopy(self.cert);c['conclusion']='unrealizable';self.rejects(self.obj,c)
    def test_wrong_policy_successor(self):
        c=copy.deepcopy(self.cert);k=next(iter(c['winning_policy']));a=next(iter(c['winning_policy'][k]));c['winning_policy'][k][a]=-1;self.rejects(self.obj,c)
    def test_missing_policy_input(self):
        c=copy.deepcopy(self.cert);k=next(iter(c['winning_policy']));c['winning_policy'][k].pop(next(iter(c['winning_policy'][k])));self.rejects(self.obj,c)
    def test_wrong_rank(self):
        c=copy.deepcopy(self.cert);k=next(iter(c['losing']));c['losing'][k]['rank']+=1;self.rejects(self.obj,c)
    def test_wrong_summary(self):
        c=copy.deepcopy(self.cert);c['summary']['states']+=1;self.rejects(self.obj,c)
    def test_wrong_semantics(self):
        c=copy.deepcopy(self.cert);c['semantics']='clairvoyant';self.rejects(self.obj,c)
    def test_negative_capacity(self):
        o=copy.deepcopy(self.obj);o['capacities'][0]=-1
        with self.assertRaises(ValueError):Contract.load(o)
    def test_boolean_capacity(self):
        o=copy.deepcopy(self.obj);o['capacities'][0]=True
        with self.assertRaises(ValueError):Contract.load(o)
    def test_over_limit(self):
        o=copy.deepcopy(self.obj);o['capacities']=[8,1]
        with self.assertRaises(ValueError):Contract.load(o)
    def test_changed_incumbent_eligibility(self):
        o=copy.deepcopy(self.obj);o['nodes']['branch0']['live']['f0']=[0]
        with self.assertRaises(ValueError):Contract.load(o)
    def test_duplicate_input(self):
        o=copy.deepcopy(self.obj);o['nodes']['start']['edges']*=2
        with self.assertRaises(ValueError):Contract.load(o)
    def test_unknown_target(self):
        o=copy.deepcopy(self.obj);o['nodes']['start']['edges'][0]['to']='absent'
        with self.assertRaises(ValueError):Contract.load(o)
    def test_unreachable_logical_node(self):
        o=copy.deepcopy(self.obj);o['nodes']['unused']={'live':{},'edges':[{'input':'wait','to':'unused'}]}
        with self.assertRaises(ValueError):Contract.load(o)
    def test_state_limit_has_no_verdict(self):
        with self.assertRaises(RuntimeError):make_graph(self.c,state_limit=1)
    def test_ephemeral_token_boundary(self):
        exact={'name':'ephemeral','capacities':[0],'initial':'a','nodes':{
          'a':{'live':{},'edges':[{'input':'sample','to':'b'}]},
          'b':{'live':{'x':[0]},'edges':[{'input':'grant','to':'a'}]}}}
        collapsed={'name':'endpoint','capacities':[0],'initial':'a','nodes':{
          'a':{'live':{},'edges':[{'input':'tick','to':'a'}]}}}
        self.assertEqual(solve(Contract.load(exact))['conclusion'],'unrealizable')
        self.assertEqual(solve(Contract.load(collapsed))['conclusion'],'realizable')
    def test_complete_graph_threshold(self):
        for n in (1,2,3):
            obj=graph_choice(4,n,63);cert=solve(Contract.load(obj));pool_check(obj,cert)
            self.assertEqual(cert['conclusion']=='realizable',n==1)
            self.assertEqual(independent_number(4,63),1)

class HierarchyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good=serial(pair_check('protected',0));cls.bad=serial(pair_check('global-credit',1))
    def test_protected_relation(self):trace_check(self.good)
    def test_shortest_witness(self):trace_check(self.bad)
    def test_broken_relation(self):
        raw=copy.deepcopy(self.good);raw['closed_relation'].pop()
        with self.assertRaises(ValueError):trace_check(raw)
    def test_false_observation(self):
        raw=copy.deepcopy(self.bad);raw['trace'][0]['left_output'][0]=777
        with self.assertRaises(ValueError):trace_check(raw)
    def test_unequal_observer_inputs(self):
        raw=copy.deepcopy(self.bad);raw['trace'][0]['right_input'][1]=-1
        with self.assertRaises(ValueError):trace_check(raw)
    def test_wrong_witness_length(self):
        raw=copy.deepcopy(self.bad);raw['shortest_ticks']+=1
        with self.assertRaises(ValueError):trace_check(raw)
    def test_phase_encoding(self):check_encoding(hierarchy_contract((2,1)))
    def test_erased_live_interval(self):
        obj=hierarchy_contract((2,1));node=next(n for n in obj['nodes'].values() if n['live']);node['live']={}
        with self.assertRaises(ValueError):check_encoding(obj)
    def test_pooled_policy_independent(self):
        raw=json.loads((ROOT/'results/pooled-12-certified-1.json').read_text())
        obj=json.loads((ROOT/'inputs/hierarchy-pool-12.json').read_text());cert=json.loads((ROOT/'results/hierarchy-pool-12.certificate.json').read_text())
        pooled_check(raw,obj,cert)
    def test_pooled_first_fit_witness(self):
        raw=json.loads((ROOT/'results/pooled-12-first-fit-1.json').read_text());pooled_check(raw)
    def test_pooled_false_claim(self):
        raw=json.loads((ROOT/'results/pooled-12-first-fit-1.json').read_text());raw['trace'][0]['left_output'][0]=123
        with self.assertRaises(ValueError):pooled_check(raw)



class PolicyIndependenceTests(unittest.TestCase):
    def test_three_outcomes(self):
        from greedy import examine
        f=(((0,1),),((0,),(1,)))
        for caps,want in [((1,1),(False,False)),((1,2),(False,True))]:
            r=examine(caps,f);self.assertEqual((r['all_choices_safe'],r['realizable']),want)
        r=examine((1,1,1),(((0,1),(0,2),(1,2)),)*2)
        self.assertTrue(r['all_choices_safe'] and r['realizable'])
    def test_zero_capacity_is_not_vacuous(self):
        from greedy import criterion
        self.assertFalse(criterion((0,),(((0,),),)))
    def test_bad_family(self):
        from greedy import criterion
        for fam in [(),((),),(((),),),(((9,),),),(((True,),),)]:
            with self.assertRaises(ValueError):criterion((1,),fam)
    def test_bad_capacity(self):
        from greedy import criterion
        for caps in [(),(-1,),(True,)]:
            with self.assertRaises(ValueError):criterion(caps,(((0,),),))
    def test_independent_checker_capacity_before_allocation(self):
        # Oversized input is rejected before enumerating any physical slots.
        obj=fork(2,1,1,(1,1));obj['capacities']=[10**12,1]
        with self.assertRaises(AssertionError):pool_check(obj,{})
    def test_independent_checker_bad_labels(self):
        obj=fork(2,1,1,(1,2));cert=solve(Contract.load(obj));obj['nodes']['start']['edges'][0]['input']=''
        with self.assertRaises(AssertionError):pool_check(obj,cert)
    def test_pair_bank_reference_witness(self):
        from pair_bank import verify
        raw=json.loads((ROOT/'results/pair-bank-negative-0.json').read_text());verify(raw)
    def test_pair_bank_bad_parameters(self):
        from pair_bank import verify
        base=json.loads((ROOT/'results/pair-bank-negative-0.json').read_text())
        for caps in [(1,1,-1),(1,1,True),(1,1,20)]:
            raw=copy.deepcopy(base);raw['capacities']=list(caps)
            with self.assertRaises(ValueError):verify(raw)
        raw=copy.deepcopy(base);raw['observer']=True
        with self.assertRaises(ValueError):verify(raw)
    def test_pair_bank_bad_input(self):
        from pair_bank import verify
        raw=json.loads((ROOT/'results/pair-bank-negative-0.json').read_text());raw['trace'][0]['left_input']=[0,0,0]
        with self.assertRaises(ValueError):verify(raw)


class IndependentOracleAndSchemaTests(unittest.TestCase):
    def test_tiny_oracle_negative_rank(self):
        obj=fork(2,1,1,(1,1));cert=solve(Contract.load(obj));oracle=solve_tiny(obj)
        self.assertEqual(oracle['conclusion'],'unrealizable')
        self.assertEqual(oracle['initial_rejection_depth'],2)
        self.assertEqual(oracle['states'],cert['summary']['states'])
        self.assertEqual(oracle['losing_states'],cert['summary']['losing_states'])

    def test_tiny_oracle_positive_summary(self):
        obj=fork(3,1,2,(2,1,1));cert=solve(Contract.load(obj));oracle=solve_tiny(obj)
        self.assertEqual(oracle['conclusion'],cert['conclusion'])
        self.assertEqual(oracle['winning_states'],cert['summary']['winning_states'])
        self.assertEqual(oracle['allocator_edges'],cert['summary']['allocator_edges'])

    def test_tiny_oracle_rematching(self):
        obj=fork(2,1,1,(1,1));oracle=solve_tiny(obj,True)
        self.assertEqual(oracle['semantics'],'rematching')
        self.assertEqual(oracle['conclusion'],'realizable')
        self.assertTrue(oracle['snapshot_feasible'])

    def test_tiny_oracle_small_graph_family(self):
        for m in (2,3):
            for mask in range(1,1<<(m*(m-1)//2)):
                for n in range(1,m):
                    obj=graph_choice(m,n,mask);cert=solve(Contract.load(obj));oracle=solve_tiny(obj)
                    self.assertEqual(oracle['conclusion'],cert['conclusion'])
                    self.assertEqual(oracle['max_rank'],cert['summary']['max_rank'])

    def test_contract_rejects_invalid_name(self):
        obj=fork();obj['name']=42
        with self.assertRaises(ValueError):Contract.load(obj)
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,{})

    def test_contract_rejects_invalid_nodes_shape(self):
        obj=fork();obj['nodes']=[]
        with self.assertRaises(ValueError):Contract.load(obj)
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,{})

    def test_contract_rejects_missing_live_map(self):
        obj=fork();del obj['nodes']['start']['live']
        with self.assertRaises(ValueError):Contract.load(obj)
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,{})

    def test_contract_rejects_malformed_edge(self):
        obj=fork();obj['nodes']['start']['edges'][0]=None
        with self.assertRaises(ValueError):Contract.load(obj)
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,{})

    def test_checker_rejects_noncanonical_winning_key(self):
        obj=fork(2,1,1,(2,1));cert=solve(Contract.load(obj));key=next(iter(cert['winning_policy']))
        cert['winning_policy']['0'+key]=cert['winning_policy'].pop(key)
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,cert)

    def test_checker_rejects_noncanonical_losing_key(self):
        obj=fork(2,1,1,(1,1));cert=solve(Contract.load(obj));key=next(iter(cert['losing']))
        cert['losing']['0'+key]=cert['losing'].pop(key)
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,cert)

    def test_checker_rejects_extra_losing_field(self):
        obj=fork(2,1,1,(1,1));cert=solve(Contract.load(obj));key=next(iter(cert['losing']))
        cert['losing'][key]['extra']='not allowed'
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,cert)

    def test_checker_rejects_boolean_policy_successor(self):
        obj=fork(2,1,1,(2,1));cert=solve(Contract.load(obj));key=next(iter(cert['winning_policy']));label=next(iter(cert['winning_policy'][key]))
        cert['winning_policy'][key][label]=True
        with self.assertRaises((AssertionError,ValueError)):pool_check(obj,cert)

    def test_tiny_oracle_enforces_slot_limit(self):
        obj=fork(2,1,1,(6,1))
        with self.assertRaises(OracleInputError):solve_tiny(obj)

    def test_tiny_oracle_rejects_unreachable_node(self):
        obj=fork();obj['nodes']['orphan']={'live':{},'edges':[{'input':'stay','to':'orphan'}]}
        with self.assertRaises(OracleInputError):solve_tiny(obj)


if __name__=='__main__':unittest.main()
