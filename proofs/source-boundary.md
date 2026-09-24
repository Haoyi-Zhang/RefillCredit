# Source boundary and closest-work disposition

The technical bibliography, `external_resources.csv`, and `literature-calibration.csv` separate three questions: what earlier work actually establishes, what this project proves, and what remains only a conditional architectural interpretation. Titles and keywords are never treated as proof of a theorem. Publications supply attributed principles and comparison boundaries; the contracts, finite inputs, code, certificates, proofs, and results in this repository are original project materials.

## Historical origin

**IRAM, IEEE Computer 1997, DOI 10.1109/2.612252.** The full four-page article motivates processor–DRAM integration, high internal memory bandwidth, and vector-oriented use. It contains no tenant-isolation definition, cache-state noninterference proof, persistent-placement theorem, or shared-accelerator experiment. Its legitimate role is historical memory-centric motivation only. No security property is inherited.

## Closest architecture and security work

**MI6, MICRO 2019, DOI 10.1145/3352460.3358310.** MI6 partitions or separates cache arrays, MSHRs, queues, arbitration, and memory paths. It therefore establishes that cache-way partitioning alone is not enough and that reserving queue/service capacity is not a new diagnosis. The present model asks when compatible storage behind a fixed logical interface can be pooled without moving incumbents. It neither reimplements MI6 nor compares hardware performance with it.

**IRONHIDE, HPCA 2020, DOI 10.1109/HPCA47549.2020.00019, and ASM, TACO 2023, DOI 10.1145/3587480.** IRONHIDE's full manuscript was inspected. It forms spatially isolated secure and insecure clusters, gives them dedicated cache/TLB/DRAM regions and memory-controller resources, and reconfigures the allocation at application granularity to reduce repeated purge cost. ASM is mandatory closest work in the same research line. Its bibliographic record, abstract, indexed section information, and author-site listing were inspected, but the exact linked ASM PDF repeatedly timed out; ASM is therefore not counted as a full-paper calibration source. The manuscript makes only the comparison supported at this resolution: cluster adaptation and dedicated resources answer an architectural deployment/performance question, not exact realizability of the paper's immutable bank-compatible repeated-lifetime credit language. No finer ASM theorem, implementation detail, or performance result is inferred.

**Sanctum, USENIX Security 2016.** Sanctum combines a security monitor, explicit DRAM ownership, cache partitioning, page-table protection, and state cleaning. It explicitly excludes bottlenecks such as DRAM or cache-directory bandwidth and does not protect timing deliberately exposed through an enclave's public API or completion time. It is strong evidence for an explicit threat-model boundary, not for the present admission/service theorem.

**Time Protection, EuroSys 2019, DOI 10.1145/3302424.3303976, and Timing Channel Protection for a Shared Memory Controller, HPCA 2014.** These works already establish partition/flush/pad reasoning and fixed or public service opportunities. The public-service assumption in this project is inherited context; no new service scheduler is claimed.

**MTIsolation, CCS 2024, DOI 10.1145/3658644.3690203.** MTIsolation gives per-domain specifications, eager reservation against future backpressure, response-space checks, compositional refinement, Coq/SMT proofs, and synthesizable case studies. The present conditional projection is a restricted application of that established reasoning, not a stronger timing-isolation or hardware-verification theorem. The retained difference is the exact persistent compatibility/capacity/policy characterization for the finite credit language.

**DAWG, MICRO 2018, DOI 10.1109/MICRO.2018.00083, and NoMo, TACO 2012, DOI 10.1145/2086696.2086714.** These works protect cache allocation/replacement with different reservation and sharing boundaries. They rule out a claim that cache partitioning, reserved minima, or a shared remainder is new. They do not by themselves characterize every lower-level compatible admission resource.

**DAGguise, ASPLOS 2022, DOI 10.1145/3503222.3507747.** DAGguise uses response-aware request shaping under a different timing-protection specification. It is evidence against a blanket assertion that dynamic sharing is insecure. Guarantees must be compared at their observation boundary; its result is not silently converted into equality of this paper's acceptance/completion traces.

**SCP, arXiv:2606.12259 (2026 preprint).** SCP separates partitioned tags from a shared data pool and gives a sizing invariant for capacity isolation while retaining explicit out-of-cache limitations. Its publication status and exclusions are preserved. A shared cache-data pool is not equated with the paper's persistent type-compatible refill credits.

## Matching, persistence, and commitment

**Online Matching and Ad Allocation, 2013, DOI 10.1561/0400000057.** Online matching already studies irrevocable decisions under unknown arrivals and competitive objectives. This project is not a general online-matching advance. Its objective is exact universal realization of a finite request/release language with repeated lifetimes, incumbent preservation, and finite rejection ranks.

**Matching Drivers to Riders: A Two-Stage Robust Approach, arXiv:2011.03624v4**, and **Recoverable Robust Optimization with Commitment, Mathematical Programming 2026, DOI 10.1007/s10107-026-02385-7.** These works already study first-stage assignments under future uncertainty, hardness/approximation, and recovery that preserves surviving commitments. Thus uncertainty, irrevocability, preservation, or matching hardness cannot be claimed as new. The paper's retained contribution is the exact theorem and certificate package for its specific event language, including a separate criterion for whether every legal free-slot policy succeeds.

Hall matching, Independent Set hardness, reachability safety games, and self-composition are established foundations. The repository provides specialized arguments where needed but does not claim those general methods.

## Capacity management, interference measurement, and cache defenses

Utility-Based Cache Partitioning, ATR, and Vantage establish runtime and fine-grained cache-capacity management. BPM/BPM+ and MemGuard establish DRAM bank/channel partitioning and bandwidth reservation. CacheInspector, the COTS resource-stressing study, and Caliper establish measurement and estimation of shared-resource behavior. CATalyst and Sanctum establish concrete cache or hardware--software isolation mechanisms. These are prior mechanisms and empirical methods, not persistent typed-credit realization theorems. Their inclusion prevents the paper from presenting cache allocation, partitioning, reservation, or interference measurement as new.

## Accelerator and memory-system context

CCBP studies concurrent GPU kernels through coordinated CTA and NoC/DRAM bandwidth control. DASH studies CPU/HWA memory scheduling under deadline and performance objectives. BPM/BPM+ studies software bank/channel partitioning and dynamic resizing on multicore machines. Buffets makes storage lifetimes explicit in a decoupled accelerator-oriented interface. These works establish that accelerator sharing, bandwidth control, bank partitioning, dynamic borrowing, and lifetime-aware storage are already active architectural techniques. None licenses an inference from this finite CPU checker to accelerator throughput, silicon cost, or deployed side-channel resistance.

## Completed calibration

`literature-calibration.csv` and `literature-calibration.md` record a nonoverlapping calibration set of 12 full TACO papers, 5 full influential papers, and 5 full adjacent-field papers. “Full” is defined as all pages being available plus structured inspection of the complete section sequence, mechanism or proof-bearing sections, methodology/evaluation, limitations, conclusion, and argument-bearing figures/tables; it does not imply memorization of every sentence. ASM is deliberately outside that count because its exact PDF endpoint remained inaccessible.

The calibration narrows rather than broadens the contribution. The project makes no firstness claim for isolation, reservation, persistence, online placement, robust matching, commitment, dynamic sharing, bank partitioning, or resource pooling. The supported research claim is an exact characterization and certificate system for the stated finite typed-credit admission language, with structural policy/capacity results and a conditional observation lift. Successful reproduction proves neither venue significance nor independent review.
