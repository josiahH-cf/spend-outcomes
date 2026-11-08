# Explicit source bindings

The local config is an access declaration, not a discovery request. Only its
consumer and digest-bound files are read. A manager uses the same permission
boundary. Keep config, consumer exports, receipts and decisions private. There
is no raw provider/client scan and no automatic upstream write.

Live reads invoke the configured `consumer.py --json --scope {...}` with project,
canonical outcome Project, days and optional explicit native session pairs.
A configured `reporting` workspace-reporting-v1 map is passed intact to its
existing owner. The returned generation, scope, source clocks, coverage,
provider/account/source metadata, conflicts, capacity and non-additive accounting
views remain inspectable. No collection is triggered. An unreadable/refused
consumer is named and independent outcome facts remain available. An invalid
contract or digest prevents qualification rather than silently substituting data.

For offline use replace the live binding with:

```json
{"telemetry":{"permitted":true,"export":{"permitted":true,"path":"consumer.local.json","sha256":"FULL_FILE_SHA256"}}}
```

Use complete unchanged UTF-8 telemetry-consumer-v1 output, not a dashboard slice.
The hash binds exact bytes. Producer project period dates are `from_day` and
`to_day`; output normalizes those names without changing dates or token classes.
No parent/delegate, target/executor, session/project or accounting totals are added
together. Native exact session observation and correlated repository association
remain different concepts; absent lineage remains absent.

An optional `outcomes` config entry is a digest-bound file with `permitted`,
`path`, `sha256`. Its content is a minimal authorized owner/operator export:

```json
{"contract":"pv-outcomes-v1","source_id":"existing-result-owner","version":"immutable-export-version","project_id":"YOUR-CANONICAL-PROJECT","permitted":true,"denominator":null,"outcomes":[{"id":"original-result-id","version":"original-result-version","association":"exact","intended_result":"the intended finish","artifact":"authorized artifact reference","revision":"exact revision","checks":[],"delivered":true,"installed":null,"acceptance":null,"benefit":null,"corrections":[],"observed_at":"2026-11-05T00:00:00Z"}]}
```

Use the existing result owner to export only authorized fields. This application
reads no OA database and requires no new OA endpoint. Explicitly attributed
operator reports may use `association: owner-attested`; correlated matches remain
`correlated`. Unknown installed/review/benefit fields stay null. A delivered
artifact or Accept supplies no benefit verdict. Contradictory observations and
rework remain in their original version. Duplicate identical result versions
collapse; conflicts refuse qualification. No receipt or task is recreated.

Targets are explicit per selected workflow. Numeric targets require amount,
unit, meaning, inclusive UTC dates and optional canonical project_id. Supported
meanings: tokens/observed, USD/api-equivalent, USD/billed-cash (unknown unless a
future authorized billed source exists). Partial pricing exposes the known
estimate but prevents claiming a fully priced target comparison. Qualitative
`{"kind":"qualitative","aim":"preserve quality"}` and no target work too.
Allocation targets preserve the declared percentage/account without inventing a
denominator. All targets are advisory, including an exhausted account observation.

Use `--baseline prior.json` for a prior/manual pv-receipt-v1. Comparable selection,
duration, basis and explicit `changed_conditions: []` are required; otherwise the
comparison is unsupported. No causal saving, human minutes or equivalent quality
is inferred. Receipt hashes identify the decisive source/result versions.

Decisions are minimal immutable pv-decision-v1 records. Actor is attributed as
operator-reported, not authenticated machine evidence. Retry under the same ID
returns identical bytes; changed content requires a new ID with `--supersedes`.
Export/import retain original IDs, timestamps, receipt/source versions and
provenance; an existing different record holds. Export only decision records,
never full restricted telemetry receipts. OA's existing owner may associate an
export under its original identity; this product performs no OA import or task
mutation and cannot claim that downstream integration was observed.

Version 0.1.1 keeps detailed exports and producer quality observations together,
even for the same logical outcome or equal version labels. Each carries its own
source ID/version and observation time; exact repeats collapse. `outcome_coverage.returned`
counts distinct outcome IDs in the selected Project; `observations_returned` counts
source/version observations. The supplied denominator and producer recent total
retain their own scope and are never added. `outcome_conflicts` lists differing
known facts and observation digests; null remains unknown, not a disagreement or
an inherited value. Source identity collisions within one exported version still
refuse qualification.

Decision relevance uses the latest timezone-qualified observation time per logical
outcome, retaining all unordered observations when clocks are absent/invalid. This
ranks evidence without asserting authoritative supersession or dropping history.
Current or unordered contrary reviews lead to investigating the named result and
obtaining linked correction/check/re-review evidence. Every current observation's
digest stays in recommendation evidence, including unknown human acceptance/benefit.
The original receipt and decision source hashes preserve all relevant versions.

Requested native sessions are shown separately with their original exact session
observation and project linkage. Exact session observation never upgrades an
unattributed/correlated Project join; its tokens are not added to Project totals.

Version 0.1.2 qualifies `source.conflicts` explicitly. The producer's object has
an integer `total` and a bounded `items` list. `{ "total": 0, "items": [] }`
is known zero. Positive totals or returned items disclose conflicts; an empty
bounded list with a positive total is still positive. Missing or malformed
coverage stays unknown. Explicit legacy lists remain supported. The additive
`source.conflict_summary` gives status, total, returned item count, completeness
and reason; the original conflict value (including null/absence as null) stays
in `source.conflicts`. Contradictory count/items never become known zero.

Source issues name stale status, genuinely missing project/period or conflict
coverage separately. A valid period remains inspectable even with a source
conflict or unknown coverage; only dependent claims require qualification. A
zero-conflict object never invents a missing/conflicting period. Allocation
comparison still requires an account token denominator and same-account usage;
human acceptance/usefulness and comparable baseline remain separate evidence.
