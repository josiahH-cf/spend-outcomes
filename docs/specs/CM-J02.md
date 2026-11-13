# CM-J02: Decision-first device report

Revision: 1. Status: ready for implementation. Date: 2026-11-13.
Basis and method identities: [CM-J01](CM-J01.md). The beneficiary is an individual builder deciding what to keep, change, investigate or hold after reviewing qualified usage and explicitly reported progress on one device.

## Starting state and audit basis

`device.device_report` already captures each source once, creates separate project receipts through `core.inspect`, and preserves unknown versus observed zero. `device.render_device` currently puts detailed client/model/service/account metadata and source diagnostics before project outcomes. MCP's renderer call supplies no refresh command. This is verified source behavior; user success, rendered accessibility and usefulness have not been demonstrated by that inspection.

UX-002: secondary diagnostics precede the decision evidence (P03, P06, P08, P10, P11; AP-04; SC-02/06 partial). Reorganize the actual renderer, preserving all measurement semantics and disclosure. UX-003's action-guidance dependency belongs to CM-J03. Do not claim observed customer findability from the approved hierarchy.

## Required behavior

1. Header presents device, inclusive UTC observation window, tracking start, generated timestamp and saved-snapshot state. Synthetic reports carry a prominent warning.
2. Show compact device observed volume and source coverage, with decision-critical issues and unassigned/ambiguous counts visible. A usable source survives another source failing. Unknown is written as unknown, never converted to zero. Label attribution counts by their original unit; do not invent unassigned token totals by subtracting non-additive project views.
3. Put each project's operator-reported outcome, success criterion, checkpoint status/history provenance, observed usage and qualified advisory target comparison together. An absent outcome/target is explicit. Token volume never establishes progress, acceptance, productivity, billed spending or ROI.
4. Keep provider and exact model observations in a separate device breakdown. State the different source token conventions. Keep project views visibly non-additive with device totals and with one another.
5. Reveal service/account/launch metadata, detailed diagnostics, qualifications and raw private JSON through semantic progressive disclosure. Retain their contents. Escape every source/config value and serialized JSON; preserve the report contract, quantities, identity and private destinations.
6. Use semantic sections/headings, text statuses, visible focus, responsive wrapping and readable contrast. Do not introduce remote assets, analytics, storage, live refresh or a new UI framework.

## Acceptance and verification

- Exercise complete, partial, all-unavailable, actual observed-zero, unassigned/ambiguous and long-label fixtures through the real renderer; assert unchanged JSON identities/quantities and safe hostile text escaping.
- Verify project/outcome placement, separate model view, visible limitations and functional details disclosure. Test keyboard focus/activation, narrow widths, 200% zoom, overflow and text contrast in an allowed rendered browser. Record unavailable checks as unverified.
- Compare the rendered output after changes against the same audit criteria. A build, markup test or screenshot alone cannot establish usability or universal accessibility.

Dependencies: existing `device.py` and `core.inspect`; CM-J03 for actions, CM-J04 for explicit decision guidance. No new backend accounting or automatic outcome state changes. No unresolved product decision blocks implementation.
