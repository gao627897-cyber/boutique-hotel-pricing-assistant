# Historical audit material

The project-root README and results/refinement_01 describe the current
implementation. Earlier results are retained to make the before/after
comparison auditable, including the original two missed hard reviews.

| Location | Historical role |
|---|---|
| benchmarks/internal-v1 | Earlier developer-authored synthetic cases and covered sources |
| benchmarks/external-challenges-v2 | Approved external challenge data and pre-LLM sources |
| benchmarks/openrouter-v3-preflight-1 | First offline adapter validation failure and source freeze |
| benchmarks/openrouter-v3.1 | First real-evaluation runtime, Gold and source manifest |
| results/stage4 | First real LLM results and contemporaneous analysis |
| results/refinement_01 | Revised temporal-evidence implementation's actual regression |

Covered runtime files and label guides remain byte-identical to their
historical manifests. These snapshots are for audit, not alternative current
entry points. Redundant historical operator READMEs, planning documents and
preflight workflow-status notes are omitted from the submission export;
their absence does not remove any file covered by a freeze manifest.

Use the root saved-evidence verifiers to recount historical and current
results. They do not require credentials and do not make model requests.
Gold/execution snapshots describe what was frozen and when; they do not prove
label quality, unseen generalization or real-world price correctness.
