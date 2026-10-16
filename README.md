# Persistent refill-credit certificates

This self-contained artifact studies an owned finite allocation game, not a
deployed processor or security-testing target. It distinguishes rematching all
live credits from assigning newcomers while retaining incumbent slots, and
checks when every eligible-free-slot policy works for the declared independent
one-credit-per-tenant language. It includes certificate/trace checkers, a
small-state oracle, exact grids and two-level tenant-local controllers.

## Manuscript diagrams

The self-contained `figures/draw_diagrams.py` exports three embedded-font vector PDFs directly with Matplotlib 3.11.2. Run `python -B figures/draw_diagrams.py --check` to check the illustrated 3-versus-4 capacity minimum, label bounds and deterministic fresh exports. `--output-dir PATH` selects the destination; the complete project's paper Makefile supplies `../paper/figures`. Drawing is separate from the standard-library scientific workflow below.

## Environment and quick checks

The complete reproduction requires Python 3.10 or later on a POSIX system with
`resource` limits; only the standard library is needed. No network, solver,
account, GPU, proprietary input or sibling paper directory is required.
Do not use `-O`: the finite campaign also uses normal-mode assertions.

From the repository root, use an external writable directory for certificates:

```sh
python -B src/pool.py inputs/fork-two-entries.json ../fork-certificate.json
python -B src/verify_pool.py inputs/fork-two-entries.json ../fork-certificate.json
python -B src/pool.py inputs/fork-two-entries.json ../rematched-certificate.json --remap
python -B src/verify_pool.py inputs/fork-two-entries.json ../rematched-certificate.json
```

The persistent game rejects this configuration; the rematching relaxation
accepts it. A checked negative result exits successfully; invalid input or
incomplete computation is an error. These small commands do not install the
reproduction wrapper's resource limits.

A separate portable regression is available:

```sh
python -B tests/regression_pair_reuse.py -v
```

It checks retained paired certificates, tiny literal words, counter/relation
tampering, lazy local transition reuse and refusals. On Windows its deny-all
`resource` import stub permits pure functions only; this does not validate POSIX
orchestration. It does not relabel the historical 68-test receipt.

## Complete reproduction

Run the seven parts sequentially:

```sh
python -B reproduce.py --part 0
python -B reproduce.py --part 1
python -B reproduce.py --part 2
python -B reproduce.py --part 3
python -B reproduce.py --part 4
python -B reproduce.py --part 5
python -B reproduce.py --part 6
```

Each part copies the retained repository to an external temporary directory,
removes its explicit required outputs there and runs one child at a time.
Each child has a 40-second CPU, 3.5-GiB address-space and 42-second wall limit.
`expected_outputs()` defines the required regenerated files. Missing outputs,
semantic differences, changes to unassigned inputs/results/tables, child failure
or timeout fail the part. CSVs compare byte-for-byte; JSON ignores only declared
measurement fields. A whole-tree fingerprint checks the retained baseline.

Reports go to stdout. Add, for example,
`--report ../reproduction-records/reproduction-0.json` to retain a report and
available raw outputs outside the repository, including on failure. In-repository
report paths are rejected. Parts 0--5 cover the finite game/controller families;
part 6 rechecks pilots, runs the small-state oracle and 68-test suite, regenerates
seven CSVs and reconciles their numerical claims.

`data/native-replay.zip` distributes the native Ubuntu seven-part replay under
`results/current/` (40 commands and 78 regenerated files). From the artifact root,
extract it with `python -m zipfile -e data/native-replay.zip .` to inspect the
retained reports and raw files without rerunning experiments. Older top-level records and exploratory
pilot timings remain separate observations. The scientific workflow runs all
parts and the portable regression on Ubuntu 24.04, with a whole-run 4-GiB,
zero-swap, four-CPU-equivalent, 600-second ceiling and raw-output upload.

## Inputs, results and consumers

- `inputs/`: exact model JSON, including hierarchy certificates' input statements.
- `src/pool.py`, `verify_pool.py`, `tiny_oracle.py`: separately structured game,
  certificate and small-state oracle implementations.
- `src/hierarchy.py`, `verify_hierarchy.py`, `pooled_hierarchy.py`,
  `verify_pooled.py`, `pair_bank.py`: declared finite controller models/checkers.
- `src/campaign.py`, `greedy.py`, `uniform.py`: deterministic case generators.
- `results/`: raw cases, certificates, observer relations, witnesses and timing
  records. Exploratory pilots are retained and semantically rechecked, not retimed.
- `src/report.py`: derives `tables/` from raw results; `src/audit_results.py`
  checks numerical quantities. Run these in a disposable copy to preserve results.
- `proofs/`, `claim_evidence_ledger.csv`: model arguments and claim/evidence links.
- `bibliography_manifest.csv`, `external_resources.csv` and calibration records:
  preserved source/provenance consumers, not standalone novelty certification.

## Conditions and license

Inputs are abstract private address symbols. Observations are tick-indexed
acceptance and ordered completions; internal slot choice and allocation cost are
hidden. Tenant-owned cache/refill updates, the fixed public service phase and the
independent lifetime language are model assumptions. Physical side channels,
coherence, writable sharing, translation and speculative execution are outside
the model. Capacity comparisons concern abstract slots, not hardware measurements.

The general enumerator admits at most eight slots and 100,000 physical states;
paired searches stop at 150,000 pairs. A refusal is not a scientific verdict.
Adaptive game depths count contract boundaries; fixed-policy two-run witnesses
count ticks. Positive relations concern all future paired inputs from reset.
The pure transition reuse preserves paired-obligation counts and traversal order;
no measured speedup is claimed.

Written proofs and finite cross-checks are not proof-assistant general theorems,
independent blind review, RTL validation or production performance/security
results. Established matching, game and self-composition principles remain
attributed in `proofs/source-boundary.md`. Original code, model inputs and
generated outputs use the accompanying MIT `LICENSE`; third-party research
texts, figures, software internals and datasets are not copied.
