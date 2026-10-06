# Persistent-credit model and proof arguments

These definitions and arguments are self-contained. They concern mathematical states and slot counts, not device behavior. The statements are general written proofs; their parameterized executable checks cover only the explicit finite grids in this repository.

## 1. Contract and observation domains

Let B be a finite bank set, C_b a nonnegative integer capacity, P the disjoint union of all physical slots, and beta:P→B its bank map. Let C(E)=sum_{b in E} C_b and K=|P|. A finite contract has an empty initial node q0, a live token set L(q) at every node, and a nonempty eligibility set E_q(x) for each live token. Every node has at least one allowed input, each determining exactly one next logical node. All logical nodes are reachable from q0. Surviving token names retain their eligibility. Reusing a name for a different lifetime requires a boundary where it is absent.

A physical state (q,mu) assigns live tokens injectively to eligible physical slots. For an input u leading to q', its possible next states are every eligible injection mu' at q' such that mu'(x)=mu(x) for each survivor x in L(q)∩L(q'). Absent tokens release before newcomers acquire. Intra-bank movement is not implicitly allowed.

The environment selects the current input before the allocator selects its extension. The allocator knows the present state and entire present input, not future inputs. The environment used for realization may observe the full mapping; tenant observations later erase it. Empty physical successor sets are rejection. A strategy is winning when it never rejects any allowed input sequence.

The hierarchy observation is (acceptance, ordered completion list) at every discrete tick. Idle input has its own status. Completions are distinguished by tenant-local identifiers. Compared runs have the same observer input sequence, local initial state, and public phase; other-tenant input sequences may differ. Slot identifiers, allocation cost, and internal bank names are unobserved. These are explicit premises.

## 2. Snapshot matching is only a relaxation

At one logical node, an injection exists if and only if, for every bank subset A,

    |{x in L(q): E_q(x) is a subset of A}| <= C(A).

Necessity follows by placing all counted tokens in A. For sufficiency, expand each bank into its slots. If Hall's condition fails for some token set T, let A be the union of its eligible banks. Its slot neighborhood is exactly the slots in A, while every token in T is counted in the displayed left side. That bank-subset inequality fails. This proves equivalence with ordinary bipartite Hall matching.

If all logical nodes are matchable, the rematching semantics can choose any destination matching independently at every edge. Conversely, a path to an unmatchable logical node prevents realization. This proof uses no persistence: restoring survivor equality changes the problem.

## 3. Exact finite realization and ranked certificates

Let S contain all eligible assignments at all logical nodes, including assignments not selected by a winning policy. Write Post(s,u) for the exact persistent successor set. Set L0=empty and

    L(k+1) = Lk union {s: some input u has Post(s,u) subset of Lk}.

The finite sequence stabilizes after at most |S| strict increases. Its complement W is closed under some allocator response for every input. Indeed, failure of that statement would add the state to the losing fixed point. Choosing one such successor per state and input yields a memoryless winning policy.

For a state first added at level k, a selected input forces successors at levels at most k−1, with the empty set producing immediate rejection at level one. Induction forces rejection within k contract edges. Conversely, because a level-k state was not in level k−1, every input has a successor outside level k−2 when k>1. The allocator can choose it and avoid rejection for k−1 edges. Hence k is exactly the minimum environment / maximum allocator rejection depth. This is an adaptive counterstrategy, not necessarily a single fixed input word.

Assign infinity to winning states. Finite ranks satisfy

    r(s) = min_u (1 + max_{t in Post(s,u)} r(t)),  max(empty)=0.

A certificate contains all states, the initial index, disjoint exhaustive winning/losing sets, a winning successor for every winning-state input, and a positive rank plus an attaining input for every losing state. The independent verifier reconstructs the universe and successors rather than trusting a producer adjacency list. Winning closure proves safety. For a finite losing rank, the attaining input produces strict descent; the checked minimum allows an allocator to delay until that rank. Those upper and lower arguments rule out an incorrect verdict or rank. The attractor produces an accepted certificate, establishing completeness for enumerated well-formed inputs.

The state count is at most sum_q (K)_{|L(q)|}, using zero for more tokens than slots. Ranks use at most ceil(log2(|S|+1)) bits. Explicit-slot enumeration can be exponentially larger than a binary capacity description; no general polynomial synthesis claim follows. The executable verifier's eight-slot and state limits are operational limits, not theorem assumptions.

## 4. Late pinned-bank fork

Let m>=2 banks hold n>=1 fully flexible incumbents. The next input requests c>=1 new credits pinned to any one chosen bank; incumbents remain. All credits later retire.

Snapshots are feasible exactly when every C_b>=c and total capacity is at least n+c. For a chosen bank, place the c pinned credits first and use the remaining slots for the flexible incumbents.

A persistent allocation leaves occupancy x_b incumbents in bank b. Every possible next bank must retain c free slots: x_b<=C_b−c. Summing over banks yields total capacity at least mc+n, in addition to C_b>=c. Conversely those inequalities allow n incumbents to be distributed within residual capacities C_b−c. This leaves the needed c slots in every bank and works after every complete retirement. The argument supplies necessity and sufficiency.

The optimized snapshot minimum is max(mc,n+c); the persistent minimum is mc+n. Their ratio increases up to n=(m−1)c and decreases thereafter, so its family-specific maximum is 2−1/m. It is not a universal competitive bound.

The two-bank, one-incumbent, one-pinned-credit example with capacities (1,1) is snapshot feasible and persistently losing at depth two. Capacity (1,2) is winning only if the first credit avoids consuming the sole bank-zero slot. A lowest-bank-first policy is therefore not interchangeable with a winning strategy.

## 5. Reserve-graph restriction

Let each of m banks have one slot, let 1<=n<m fully flexible incumbents remain live, and let a later single credit request either endpoint of any edge in a nonempty simple graph G on the banks. Every snapshot fits: assign the later credit one endpoint and the n incumbents to other banks.

An incumbent occupied set S blocks an edge exactly when both endpoints are in S. It supports every future edge if and only if S is independent. Thus persistent realization holds precisely when n<=alpha(G). Equivalently, the free banks form a vertex cover. For arbitrary nonempty eligibility hyperedges, the free banks form a hitting set.

An independent occupied set is a polynomial certificate. Mapping an Independent Set instance with a nonempty graph and 1<=n<m to this contract is polynomial; trivial out-of-range or empty-graph instances can be decided and mapped to fixed yes/no examples. This proves NP-completeness of the unbounded restricted decision problem. It is a small specialization of established combinatorial hardness, not a new general robust-matching hardness claim. Finite five-bank checking is not the proof of NP-completeness.

## 6. Every-policy admission criterion

Suppose n independent tenants each hold at most one live credit. An idle tenant i may acquire any type E from its fixed, nonempty family F_i; it may later release. Events are serialized, with arbitrary waiting and releases. A free-slot policy must use a free eligible slot when one exists and never move an incumbent.

For each (i,E), create a bipartite graph H_iE. Right vertices are physical slots in E; left vertices are other tenants. Connect tenant j to a slot in bank b when some type in F_j contains b. Then every policy succeeds for every event sequence if and only if

    maximum_matching(H_iE) < C(E) for every i and E in F_i.

For sufficiency, any blocked arrival to E finds every slot in E occupied. The requesting tenant is idle, and each other tenant owns at most one slot. Matching each occupied slot to its owner covers the right side of H_iE, contradicting the inequality.

For necessity, take a matching covering E. For each matched tenant choose a permitted type containing the bank of its assigned slot. From empty, acquire those credits one by one and choose the matched distinct slots; all these choices are legal. Then request E for i without releasing any incumbent. It is blocked. At most C(E)+1<=n acquisitions, including the failed one, suffice. If C(E)=0 the first request is already blocked.

This proves failure of universal policy safety, not failure of existential realization. Another strategy may avoid the blocking assignment. A direct augmenting-path test is polynomial in explicit tenants, types, and physical slots; it does not require constructing all lifetime states. For general languages, the full game retains additional event constraints.

## 7. Homogeneous and uniform optima

When all tenants have the same family F, realization is possible exactly when C(E)>=n for every allowed type E. Necessity follows by having all n tenants hold E simultaneously. For sufficiency, at most n−1 slots are occupied before any acquisition, so any eligible set with at least n slots contains a free one. Every free-slot policy is safe, for arbitrary releases and repeated lifetimes.

Let F be every s-bank subset among m banks. Let capacities be arbitrary nonnegative integers with unit cost per slot. The pooled optimum is

    P*(m,n,s) = n + (m−s) ceil(n/s).

Sort capacities increasingly. The s smallest must sum to at least n, so the s-th is at least q=ceil(n/s); all larger ones are also at least q. This gives the lower bound. Put d=sq−n banks at capacity q−1 and the other banks at q, where 0<=d<s. The s smallest sum to n and the total equals the bound, proving attainability.

For permanently owned non-borrowable slots, each tenant needs owned slots in a bank set intersecting every s-subset. This requires at least m−s+1 banks, since its complement must have size below s. One distinct slot in each such bank suffices for a tenant with one live credit. Summing disjoint slot ownership yields the dedicated optimum

    D*(m,n,s) = n(m−s+1).

Both sides may optimize capacity placement. Thus m=3,n=2,s=2 gives P*=3 and D*=4 without comparing against a deliberately poor partition. At s=1 both equal mn; at s=m both equal n. For fixed n<=s and growing m−s, D*/P* approaches n. These are abstract slot counts.

## 8. Conditional lift and finite instantiation

Let each reference tenant evolve as (z_i',o_i)=F_i(z_i,u_i,p), with deterministic F_i depending on no foreign state or input; let public p'=G(p). The physical hierarchy must project to these reference states and observations at every tick. Every logically required resource acquisition must be represented by the credit contract and served by its winning allocator. Physical slot choices and internal costs must not add observed delay.

Take two executions with equal initial p and z_i and equal u_i. By induction their logical next states and observations are equal. Winning allocation realizes the required credits in each run. Conformance transfers the logical equality to physical projected states and outputs; G advances the public phase identically. This proves per-tick noninterference. It is an ordinary refinement argument under strong explicit premises, not a proof that a particular RTL implementation meets them.

The finite controller has two private cache levels and one pending operation per tenant. Inputs are sampled before service. Busy tenants reject new requests; L1 hits complete immediately; an L1 miss begins one or two refill stages. Public alternating grants advance stage two to stage one or complete stage one. Only the owner's cache tags change. An accepted miss completes by its second own opportunity, no later than four tick positions including acceptance.

Sampling and service are separate contract boundaries. A credit born and released within one tick still occupies a physical slot between those boundaries. Collapsing the endpoints into empty-to-empty would incorrectly certify zero capacity. The independent encoding checker verifies these intermediate live sets.

Positive paired-machine checks retain a relation containing reset, equal observations, and all successors for every pair of equal observer inputs and independently chosen foreign inputs. Closure proves the finite reset-reachable result for arbitrary future length. Negative checks replay a first-difference trace and exhaust every shorter depth in a separately written transition model. Minimum ticks for a fixed policy and minimax contract edges for an adaptive allocation game have different quantifiers and units.

## 9. Scope of validation

The 280 forks, 4,296 graph cases, 80 uniform minima, and 1,225 all-choice cases agree with the corresponding formulas or graph/matching oracles. In addition, the independent tiny oracle cross-checks 484 contracts, 764 persistent/rematching verdict-and-summary instances, 484 snapshot verdicts, and all 16,205 losing-state ranks in that small boundary. Ten two-bank physical-policy observer cases and four three-bank observer cases distinguish allocation existence from policy substitution. Four separate benign logical faults affect admission, idle-slot service, foreign two-level (L1 and L2) invalidation, or foreign L2 fill. Their checked minimum differences range from one to six ticks.

The tests do not prove architecture relevance, general code correctness, literature priority, device security, or acceptance readiness. The checker implementations share a mathematical specification and research process. Their independence is limited to code paths and algorithms. The necessary primary-source distinctions are recorded separately in `source-boundary.md`.

The seven-part reproduction driver treats the retained repository as a comparison baseline rather than an output directory. For each part it copies the repository to an external temporary directory, deletes that part's explicit required-output set from the copy, and runs all children there. Generated result JSON is compared after removing only declared execution-measurement fields; generated input JSON is compared exactly as parsed; generated CSV is compared byte-for-byte; and every tracked file outside the part's output set must remain byte-identical. Missing output, an undeclared tracked output, semantic change, retained-file mutation, nonzero exit, or timeout fails. Small fixtures exercise output deletion, nonzero exit, timeout, two consecutive instances of the same semantic regression, and mutation of a retained file; the original fixture baseline remains unchanged in each case. With an external report path, the driver also copies the attempt's available regenerated raw files to a unique external directory before temporary cleanup. A failure fixture checks that these are the actual mismatching outputs, not the baseline files.

The current 68-test record includes six additional input-boundary, certificate-metadata, and raw-retention regressions. It comes from a Windows finite recheck with an explicit adapter for the POSIX-oriented orchestration fixtures. The older seven-part records and campaign timing fields remain historical POSIX evidence; they do not certify the updated driver on POSIX.
