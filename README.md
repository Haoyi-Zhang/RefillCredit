# Persistent refill-credit certificates

This repository studies an **owned finite mathematical model**, not a deployed processor or security-testing target. It contains a persistent allocation game, independently implemented certificate and trace checkers, an independent small-state oracle, exact parameter grids, and two-level tenant-local controllers. It is self-contained: no paper directory, network, account, GPU, model API, external solver, or proprietary input is needed.

## What the evidence establishes

The main distinction is between rematching all live credits at each state and assigning newcomers while retaining every incumbent's slot. A configuration may pass the former and fail the latter. A separate matching criterion decides when **every** eligible-free-slot policy works for an independent one-credit-per-tenant language. Failure of that stronger criterion need not mean that no successful policy exists.

Written proofs are in `proofs/model-and-results.md`. They cover exact finite realization and rejection ranks; the pinned-bank fork; the reserve-graph restriction; the all-choice matching criterion; homogeneous capacity minima; and a conditional observational lift. These are written mathematical arguments. The executable checks are finite checks, not machine-checked general proofs.

The completed grids contain 280 fork configurations, 4,296 reserve-graph cases, 80 uniform-capacity cases, and 1,225 policy-independence cases. Among the latter, 748 configurations are realizable, 264 admit every free-slot policy, and 484 require choosing an appropriate policy. These counts describe complete declared parameter grids, not a workload sample or a security failure rate.

A two-tenant, two-level model with two-out-of-three compatibility uses three shared slots; its two observer closures contain 5,602 and 5,734 state pairs. The corresponding permanent, non-borrowable dedicated capacity minimum is four **abstract slots**, proved over the independent lifetime language. This is not a measured hardware-area, latency, throughput, energy, or accelerator result.

## Reproduce

Use Python 3.10 or later on a POSIX system supporting `resource` limits. Only the standard library is required. Do not use Python `-O`: the finite certificate verifier rejects execution with assertions disabled.

From this repository root, run the seven parts sequentially:

```sh
python reproduce.py --part 0
python reproduce.py --part 1
python reproduce.py --part 2
python reproduce.py --part 3
python reproduce.py --part 4
python reproduce.py --part 5
python reproduce.py --part 6
```

Each scientific child is limited to 40 CPU seconds, 3.5 GiB of address space, and a 42-second wall timeout. There is at most one child at a time; the parent only orchestrates it. The total project ceiling is four CPU cores and 4 GiB, with no swap; these commands use one scientific worker. Part 0 checks forks, logical hierarchy, and integrated games. Parts 1–3 cover all 17 graph blocks. Part 4 checks the physical policies and uniform-capacity hierarchy. Part 5 checks all-choice allocation. Part 6 rechecks retained pilots, runs an independent 484-contract small-state oracle comparison, executes 55 regression tests, regenerates CSV tables, and reconciles 44 numerical claims.

Parts can be rerun independently after interruption. The scripts compare regenerated semantic JSON fields against the retained results; CPU time, elapsed time, and memory measurements are deliberately excluded from equality. `results/reproduction-*.json` records each command and comparison outcome. A changed semantic field fails reproduction rather than silently replacing the expected outcome. An exceeded state or resource limit is **no verdict**, not rejection or success.

The comparison covers retained result files, including unchanged files. It does not falsely mean every file was regenerated in each part. The original exploratory timing records in `pilot.json` and `integration-pilot.json` are retained and their eight case semantics are recomputed by `src/recheck_pilots.py`; their historical timings cannot be regenerated. Example certificates and exact hierarchy input JSONs are retained. Bulk grid certificates are checked during each run rather than storing thousands of redundant certificates; deterministic generators reconstruct those exact cases.

Smaller commands for inspecting the certificate boundary are:

```sh
python src/pool.py inputs/fork-two-entries.json /tmp/fork-certificate.json
python src/verify_pool.py inputs/fork-two-entries.json /tmp/fork-certificate.json
python src/pool.py inputs/fork-two-entries.json /tmp/rematched-certificate.json --remap
python src/verify_pool.py inputs/fork-two-entries.json /tmp/rematched-certificate.json
python src/oracle_crosscheck.py
python src/check_tests.py
python src/audit_reference_ledger.py
python src/audit_results.py
```

The first game rejects persistent realization; the rematching relaxation accepts it. A rejected configuration is a legitimate result, so the solver writes a checked negative certificate and exits successfully. Invalid input or an incomplete computation is an error. Direct small commands do not install the orchestration wrapper's resource limits; the seven reproduction parts are the bounded campaign entry point.

## Repository map

`src/pool.py` builds the game with backtracking assignments. `src/verify_pool.py` rebuilds assignments by permutations without importing the solver. `src/tiny_oracle.py` is a third, deliberately small implementation that imports neither the producer nor certificate verifier; `src/oracle_crosscheck.py` compares its persistent/rematching verdicts, snapshot feasibility, and losing-state ranks over 484 contracts. `src/contracts.py` contains exact case generators and a controller encoding check. `src/hierarchy.py` and `src/verify_hierarchy.py` implement separate tuple and scalar transition semantics. `src/pooled_hierarchy.py` installs fixed or synthesized allocation; `src/verify_pooled.py` reconstructs it independently. `src/pair_bank.py` contains the three-bank model and a separately written dictionary-based reference function that does not call the producer transition. Keeping two implementations in one file is not a separate trust domain or an independent development team.

`src/greedy.py` compares the all-choice matching criterion with all reachable legal allocations and with the realizability game. `src/uniform.py` enumerates integer capacity vectors and permanent-reservation hitting sets. `src/campaign.py` selects bounded finite families. `src/report.py` produces compact CSVs from raw results. `src/audit_results.py` checks the paper's stated numerical quantities against those raw files. The independent tiny-oracle campaign covers 764 persistent/rematching semantic comparisons, 484 snapshot comparisons, and 16,205 losing-state rank comparisons.

`inputs/` contains exact consumed model JSONs. `results/` contains raw cases, example and hierarchy certificates, full positive observer relations, negative witness sequences, recheck records, and measured execution costs. `tables/` contains derived CSVs, not additional observations. `claim_evidence_ledger.csv` maps material claims to proofs and raw evidence. `bibliography_manifest.csv` is the 32-entry cited-work inventory, and `src/audit_reference_ledger.py` checks it against the source and calibration ledgers without requiring the paper directory. `external_resources.csv` records scholarly and software provenance, legal integration boundaries, access limitations, and a one-to-one mapping for all 32 manuscript citations. `literature-calibration.csv` records the completed 12 same-venue, 5 influential, and 5 adjacent full-paper calibration set. `proofs/source-boundary.md` distinguishes reused principles from this model's specific obligations, and `proofs/literature-calibration.md` records the reading standard, pattern synthesis, and retained novelty boundary.

## Observation and input boundaries

Inputs are abstract private address symbols. No real addresses, devices, processes, network services, cryptographic secrets, exploit payloads, or attack scripts are used. Negative controls modify only these owned transition functions. An observation is a tick-indexed pair of acceptance status and ordered completions. Internal slot choice and allocation cost are hidden assumptions. A public fixed service phase never transfers an idle opportunity based on another tenant's private activity. Cache lines and all refill updates are tenant owned; writable sharing, coherence, translation, speculative execution, and physical side channels are outside the model.

The general allocator sees the current whole logical input batch before selecting its assignment. A concrete first-fit implementation may commit in tenant order and can therefore fail earlier. An adaptive game counterstrategy measures contract boundaries; the fixed-policy two-run search measures **ticks**. They are not the same shortest-trace metric. A positive relation proves equality from reset for all future paired inputs of the finite model, not merely for a selected bounded prefix.

The general enumerator admits at most eight slots and 100,000 physical states. Paired searches stop at 150,000 pairs. All parameters are explicit. Integer arithmetic is exact. Grids and traversal order are deterministic, so no random seed, training set, hidden test split, or statistical confidence interval is applicable. The study was exploratory; it was not prospectively preregistered. The final frozen grids were not filtered for favorable outcomes.

## Trust and maturity

General safety games, Hall matching, self-composition, online and robust matching, reservation against backpressure, resource pooling, and per-domain refinement are established ideas. This artifact does not claim those principles as new. A completed 12+5+5 full-paper calibration and a separate closest-work boundary review narrow the retained contribution to an exact characterization and certificate system for the stated finite persistent typed-credit admission language, plus a conditional lift to the declared observation model. That calibration is evidence of diligence, not an independent novelty review or a guarantee of venue significance. No RTL, accelerator execution, production performance, physical-security claim, or proof-assistant general theorem is supplied.

Generative AI was used substantively for problem formulation, mathematical arguments, code, experiment design and interpretation, validation planning, and writing. The experiments were actually executed. Separately written checkers and the small-state oracle are implementation cross-checks within the same research process, not an independent blind review. The oracle is algorithmically separate but shares the same English specification and therefore reduces, rather than eliminates, common-mode risk. Human authorship, accountability, and any external-use declarations require a separate truthful determination. No external publication or repository URL is asserted.

The original code, model inputs, and generated outputs are licensed under the accompanying MIT license. Third-party research text, figures, software internals, and datasets are not copied into this repository. Ideas and mathematical results are attributed in the source boundary and resource inventory.
