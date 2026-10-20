# Literature calibration and closest-work boundary

## Scope and counting rule

This calibration records **12 full TACO papers, 5 full influential papers, and 5 full adjacent-field papers**, with no source counted in more than one bucket. “Full” means that all pages were available and a structured inspection covered the title and abstract, introduction, complete section sequence, mechanism or proof-bearing sections, methodology/evaluation, stated limitations, conclusion, and the figures and tables that carry the argument. It does not mean every sentence was memorized. The row-level record is `../literature-calibration.csv`. The manuscript bibliography contains 32 cited works, each mapped one-to-one to a provenance row in `../external_resources.csv`; the 22 calibration papers are a nonoverlapping reading subset, not a citation-count target.

The calibration is a research-quality control, not a bibliometric survey and not independent peer review. It is used to test whether this paper’s question has been subsumed and to calibrate TACO-native narrative and evidence. Publications are cited rather than copied; no third-party PDF is redistributed.

## Closest-work disposition

The comparison eliminates several possible broad claims:

* IRAM supplies historical processor–memory integration motivation but no tenant-isolation property.
* NoMo, MI6, Time Protection, the fixed-service memory controller, Sanctum, IRONHIDE/ASM, DAGguise, and MTIsolation already establish important forms of reservation, partitioning, public or shaped service, spatial secure clusters, and strong timing-isolation reasoning.
* Online matching, two-stage robust matching, and recoverable optimization with commitment already establish irrevocable choices, future uncertainty, preservation, and hardness in broader mathematical settings.
* Accelerator scheduling and memory-partitioning papers already study dynamic sharing, bandwidth control, banks/channels, deadlines, and multi-tenant interference under performance objectives.

Accordingly, the retained contribution is deliberately narrow: **an exact characterization and certificate system for the paper’s stated finite, typed, repeated-lifetime request/release contract under incumbent preservation, together with structural policy-independence tests and a conditional lift to the declared observation model.** The paper makes no firstness claim for isolation, reservation, persistence, online placement, robust matching, commitment, or resource pooling. It makes no hardware-performance claim.

### ASM access limitation

ASM (Sahni, Omar, Ali, and Khan, TACO 20(3), Article 32, DOI 10.1145/3587480) was treated as mandatory closest work. Its bibliographic record, abstract, section-index information, and the full IRONHIDE predecessor were inspected, but the exact publicly linked ASM PDF endpoint repeatedly timed out in this environment. ASM is therefore **not** counted among the 12 full TACO calibration papers. The available evidence is sufficient for the limited non-subsumption statement used in the manuscript: this research line adapts spatial secure/insecure clusters and dedicated memory-controller resources at application granularity, whereas the present theorem concerns exact realizability of an immutable bank-compatible credit language. No finer ASM theorem or performance comparison is asserted.

## Same-venue pattern synthesis

The twelve TACO papers consistently move from a concrete architectural failure to one mechanism or analytical principle, then connect the mechanism to decisive evidence. The strongest papers do not let generic multi-tenancy stand in for a contribution: they identify a particular cache, DRAM, bandwidth, prefetch, deadline, or visibility failure and use figures to expose the causal path. Quantitative plots and tables have workload or configuration meaning; limitations and implementation costs are explicit.

The present paper follows that pattern with a concrete late-pinned-bank counterexample, one finite game and certificate language, structural capacity/policy theorems, and finite negative controls. Because it is a theory-first paper, complete small-state enumeration and independent certificate replay replace performance curves. Generated instance counts are not represented as production workload breadth.

## Influential-paper pattern synthesis

IRAM, MI6, Time Protection, IRONHIDE, and Sanctum show the importance of declaring a system boundary before claiming architectural relevance. MI6 and Sanctum proceed resource by resource; Time Protection separates partitionable state from time-multiplexed state; IRONHIDE couples a spatial-isolation architecture to a specific interaction workload; IRAM is historical motivation rather than security evidence. This calibration is the reason the paper’s deployment mapping remains conditional and why no accelerator-hardware efficacy is inferred from the finite CPU checker.

## Adjacent-field pattern synthesis

The fixed-service controller and DAGguise demonstrate that service and response semantics must be compared at the observation boundary. MTIsolation shows that eager reservation and compositional trace refinement are established principles. Online and robust matching show that irrevocability and uncertainty are not new. The remaining delta is therefore the paper’s exact event language and its certificate-producing decision procedure, not a new general matching paradigm.

## Narrative and figure consequences

The paper retains eight main sections: concrete failure and contribution boundary; architecture/observation contract; finite model; exact checker; structural theorems; conditional hierarchy lift; exhaustive finite evidence; limitations and conclusion. The three figures have distinct roles: expose pointwise-versus-persistent failure, state pooled-versus-dedicated capacity, and show the conditional conformance boundary. Their current assets are direct Python/Matplotlib vector PDFs generated by `figures/draw_diagrams.py` in the artifact and consumed through the paper's `persistent-fork.tex`, `shared-capacity.tex`, and `refinement.tex` inclusion wrappers. No decorative redraw or borrowed architecture result is needed.

## Residual uncertainty

This calibration supports a defensible non-subsumption boundary, not guaranteed novelty, acceptance, or independent review. The ASM full-text access limitation is preserved. A future externally submitted version must still be checked by accountable human authors against any newly published work and the live venue portal.
