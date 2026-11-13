# CM-J04: Explicit decision continuity

Revision: 1. Status: ready for implementation. Date: 2026-11-13.
Basis and method identities: [CM-J01](CM-J01.md).

## Purpose and compatibility boundary

The builder explicitly records keep/change/investigate/hold, a reason, next action and review trigger against one exact immutable device snapshot, then retrieves that decision and any later decisions. This records human judgment without executing work or inferring benefit.

`__main__.py record` currently accepts only `pv-receipt-v1`; device snapshots use `cherry-meter-device-report-v1`, so direct CLI reuse is incompatible. `core.save_record` already owns immutable `pv-decision-v1` files at `state/decisions/<id>.json`, and legacy import/export preserves its defined fields. Reuse that owner, format and location through a narrow declared MCP adapter, never a shell fallback or parallel store. UX-004 is an approved backend dependency, not a front-end-only fix.

## Required behavior

1. Add a declared decision command/tool with exact config, saved report path, stable user-chosen decision ID, actor, keep/change/investigate/hold, reason, next action, review trigger and optional superseded decision ID. Require nonblank human fields; do not manufacture them. Preserve legacy field names `feedback`, `next_action`, `review_trigger`, `supersedes`.
2. Bind `receipt` to the full canonical device-report SHA256, verify the filename and report contract, and retain generation/contract provenance in `source_versions`. Require the snapshot under that config's exact `state/device-reports` directory and the device identity to match. Do not rescan usage to record a decision.
3. Preview/apply binds config bytes, snapshot bytes/identity, exact record contents and read/write scope, including decision-store, lock/temp/directory effects. A hash is a stale-scope guard, never consent. Do not bypass held plans. Read exact prior/superseded records only as declared.
4. Save through the existing immutable owner. Exact retries retain the first timestamp and bytes, including simultaneous identical requests. Conflicting reuse of an ID is refused. A later ID can supersede an existing decision without overwriting it; missing, self or incompatible supersession is held. Existing records and legacy behavior remain intact.
5. Add declared bounded retrieval of decisions from the approved config's decision directory, with optional exact ID; no source reads, execution, credentials, helper/settings changes or arbitrary file access. Explain retrieval scope before reading and fail explicitly on malformed records/limits.
6. Static report guidance names the exact snapshot and supported decision/retrieval commands. It never pretends to persist a decision. Old reports remain frozen and need not embed later decisions.

## Acceptance and verification

- Device binding, canonical filename/hash, unsupported contracts, path traversal, symlink/reparse components, source/config tampering and stale plan refusal.
- Exact retry, concurrent retry, conflicting reuse, valid later supersession, missing/self supersession, preserved history and legacy decision export/import.
- Recording/retrieval with source observers, subprocess and network made unavailable must still succeed. No reports, config, usage stores or previous decisions change merely from recording.
- Installed protocol discovery, preview/apply and later retrieval in CM-J05. Human acceptance/usefulness is never supplied by the agent.

Dependencies: existing core/storage/MCP contracts; CM-J02/03 guidance. No parallel persistence or new workflow platform. No unresolved product decision blocks implementation.
