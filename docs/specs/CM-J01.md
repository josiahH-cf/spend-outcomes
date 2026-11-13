# CM-J01: First trustworthy report

Revision: 1. Status: ready for implementation. Date: 2026-11-13.
Source basis: public preview commit `2ad0451c1b2b0d9ce19a1a103c0492f0a3d749cd`, tree `0e740a6ef1689b1db2db9f200f1199011b9e81cd`.
Intent: Jo's approved five-spec plan, delegated in task `6af6f0d6-251c-8191-b9c7-53d01f7310db`; user messages `Sentinel_a0200ac8c1b08191a860e68c8b5d7a06` and `Sentinel_17cda33896048191adbe739a0527f205`.

## Purpose and starting state

An individual builder using Claude Code and Codex on one Windows AMD64 device must select an appropriate install route, approve exact bindings, and obtain a qualified report from actual usage. Forward collection is sufficient. Existing main/stable v1.0.1 is a legacy WSL/Codex path; the 1.2.1-rc.1 preview is a separate declared-MCP implementation. Neither source inspection nor installed metadata proves client integration.

The inspected root contains no AGENTS.md, native spec format, queue, agent loop, or spec validator. These five self-contained Markdown specs are the fallback authoring mechanism; they introduce no runner or approval platform. `scripts/build_candidate.py` remains the package validator, and the normal checks are unittest discovery, compileall and Git whitespace checks. See [journey](../journey.md) for shared backend ownership.

## Required behavior

1. README, Windows guide and public resource entry distinguish legacy stable from the new numbered Windows preview and link exact release assets and checksums. Retain `/resources/spend-outcomes` and the existing Resources card.
2. Before enabling, require an existing trusted Python 3.10+ absolute interpreter selection, compatible Claude Code, and Git only for public Git acquisition. No download, policy repair, credentials, SSO, Directory resubmission or auto-update change.
3. Setup asks only for a new private config, state destination, device label, project key and existing workspace, explicit source bindings, prospective tracking start, and the user's optional outcome/target/checkpoints. Defer additional workspaces and advanced attribution/tuning unless needed for the first report. Never infer a root or outcome.
4. Keep exact preview/apply approval, ancillary write disclosures, no overwrite, independent helper/export setup, and the declared-tool-only plugin boundary. Installing the plugin does not start or install collection.
5. Show demo as synthetic throughout. Doctor checks config/path existence, then a separately approved report reads only the configured sources. Missing inputs yield qualified unknowns and recovery guidance.
6. Privacy copy distinguishes the local engine's no-network behavior from selected tool output entering Claude's hosted conversation. Do not publish private config, logs, reports or paths.

## Acceptance and verification

- Inspect installed duplicates/version/interpreter before update; exercise a fresh isolated profile install and exact-source readback without copying credentials.
- Verify published assets as a signed-out reader and hash downloaded bytes; keep update/rollback state and previous runtime.
- A qualified fresh tester must select the correct route, produce an actual-usage report, and distinguish demo, setup assistance and provider measurement. Record observed friction; do not invent success time or human acceptance.
- Automation, existing-device qualification, clean consumer/non-admin Windows, native Mac/ARM, and authenticated fresh-client evidence remain separate. Any missing access is an explicit verification boundary.

Dependencies: CM-J02/03 for the resulting report, CM-J05 for the integrated litmus. No unresolved product decision blocks implementation.

## Method identities

Read in full from Espansr's `templates` directory without editing that repository: `clarify_features.json` SHA256 `986bfc5e4bcd001f3f431e1fec5a1f308e30ecfc562dea5ceac5c85990b86868`; `user_journey.json` SHA256 `746eadda2a7e1df90da9e6675bd304ca8fab9f77674bd39092275c5a0a060da7`; `ui_ux_audit.json` SHA256 `9702f851dcbab7f92713096f15003edac58c34dea8df2ca8ff6575db7167f082`. Readiness means implementable specification, not delivered or human accepted behavior.
