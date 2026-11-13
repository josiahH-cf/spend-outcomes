# CM-J03: Honest refresh, checkpoint and recovery

Revision: 1. Status: ready for implementation. Date: 2026-11-13.
Basis and method identities: [CM-J01](CM-J01.md).

## Purpose and starting state

The builder must know how to refresh a saved report, explicitly update a checkpoint and diagnose a named coverage problem. `mcp.execute` saves immutable JSON and HTML after an exact report preview/apply; `cherry_meter_checkpoint` updates only config and operator history with a stale-config guard. The current MCP-rendered HTML warns that it is saved but lacks actionable refresh guidance. UX-003: inconsistent CLI/MCP recovery and next steps (P02, P04, P05, P09, P12, P13; SC-03/04/08 partial).

## Required behavior

1. Every device report gives truthful guidance for `/cherry-meter:report`, `/cherry-meter:checkpoint` and `/cherry-meter:doctor`. MCP-generated reports include their exact private config and snapshot identities in the guidance. Native CLI reports retain their independent refresh command.
2. The report is a static snapshot. No HTML control claims to run a command or save progress. Any copy affordance labels the copied text as instructions; success means only copied, and failure leaves selectable text. Never describe copied as run, refreshed or saved.
3. Refresh instructs the person to approve the report plan and open the returned new HTML path, comparing generated time/report identity. It never modifies the old JSON/HTML. A fixed historical end date remains explicit in guidance.
4. Checkpoint guidance carries project/checkpoint identities available in the snapshot, asks for the human-chosen status/actor/note and explains that it will appear only after regeneration. Do not mark an outcome complete or infer benefit from tokens, tests or agent output.
5. Missing/partial sources identify limitations while preserving good observations. Doctor checks only permitted config and path existence. It cannot establish collector uptime or fix a helper. No hidden root discovery, source expansion, shell fallback, helper restart or provider settings repair.
6. Keep changed-plan, cancellation and partial-write behavior honest: a stale plan is held, completed writes may remain, and the caller inspects the approved destination before retrying. Repeated static interactions have no backend effect.

## Acceptance and verification

- Traverse report -> explicit checkpoint -> new report using declared handlers. Assert old snapshots' bytes remain unchanged and only the new snapshot contains the update.
- Verify missing-source recovery, stale config/plan refusal, cancellation before writes and after completed writes, and repeat safety. Verify no subprocess/network/helper effects from MCP tools.
- Inspect instructions in MCP and CLI render paths, demo labeling and private identity escaping. Exercise copy success/failure if copy controls are included; plain selectable guidance is sufficient and avoids inventing an execution UI.
- Actual installed-client traversal belongs to CM-J05; source tests remain separate evidence.

Dependencies: CM-J02 renderer; existing MCP and storage owners. No new execution backend is required. No unresolved product decision blocks implementation.
