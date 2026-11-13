# Directory status and independent Windows preview

## Current status (2026-11-11)

The 1.2.0 source was published for Directory review at
`2a56314fbb69f0c707a3be18e904d09afc67e1bd` on
`directory/cherry-meter-1.2.0`, with the repository root as plugin path.
Validation passed with zero blockers, four warnings and three policy holds.
The subsequent submission was automatically refused because local MCP/file
capabilities require an eligible verified organization. It was not accepted or
listed. Preserve the submission and source branch; no resubmission is part of
the independent preview work.

Version **1.2.1-rc.1** is a separate Windows AMD64 / Claude Code preview using a
project-owned marketplace. See [preview installation](windows-preview.md).
Self-hosted distribution does not change the Directory's eligibility decision,
confer verification or authorize bypassing an organization's plugin policies.
The public default `main` branch and stable releases remain at the earlier
release line. Do not present the preview as a new stable cross-platform release.

The contained readable runtime declares a local stdio MCP server. All plugin
commands use only its tools; helper installation is separate and operator
controlled. The interpreter default `python` follows host executable search
rules, without checking trust or version. A fresh enabled install may launch it
before an override is configured. Verify trusted Python 3.10+ before enabling,
preferably through its verified absolute path. The native-qualified workflow
used that explicit override. See [MCP contract](MCP_SERVER.md),
[native setup](native-candidate.md), [data handling](../PRIVACY.md) and
[support](support.md).

The issue tracker and the 1.2.0 privacy/documentation pages were published and
verified before their manifest URLs were added. The preview manifest names its intended version-specific documentation and
privacy pages. Verify that those exact resources resolve to the audited source
immediately after publication, before distributing an install recommendation.
The matching documentation is included in the source. No private device config, reports or session identifiers belong
in public support requests.

## Reviewer examples

These examples use a new approved private sample directory, not real usage,
credentials or provider settings. They are prospective 1.2.0 integration cases;
source tests alone do not establish that an actual Claude host runs them correctly.

1. "Use Cherry Meter's demo command to preview a synthetic tandem example in this
   new private directory. Do not read real usage." The declared
   `cherry_meter_demo` tool shows its plan. After approval, applying it should
   return a clearly synthetic 120 Codex + 180 Claude = 300-token result.
2. "Preview a report for that demo config and explain every read and write."
   After approval, `cherry_meter_report` should preserve synthetic labeling and
   coverage gaps and identify private report and possible SQLite sidecar writes.
3. "I reviewed the synthetic report. Preview marking its review checkpoint
   complete with my note." Apply `cherry_meter_checkpoint` only after approval
   of the exact operator-authored change, then separately preview/apply a refresh.
   Prior immutable receipts must remain unchanged.

Preview/apply hashes guard stale or changed scope. They do not authenticate human
consent. The assistant must obtain actual approval unless valid existing explicit
pre-approval covers the exact plan, and must not turn a hash into a standing
data-access permission. New or unclear scope requires approval. No plugin command may use shell or native CLI
fallback to repair a missing tool or bypass a held operation.

## Evidence and unresolved checks

The [qualification record](qualification.md) separates 1.2.0 synthetic/protocol
checks from historical 1.1.x installed-helper and actual-provider evidence.
The historical 93,671-token checkpoint is not a native-client MCP result.
A separate controlled 1.2.0 native Windows test naturally loaded the declared
server and passed info, doctor, report preview and one approved report apply,
with zero denials and no shell or unrelated tool calls. Source/cache/config
were unchanged. Independent post-export reconciliation at 20:58:07 UTC on
2026-11-10 held 131,852 = 113,083 Claude + 18,769 Codex over three direct reads.
The MCP report itself showed 112,131 before its final 19,721-token export.
Attribution stayed unassigned, coverage partial and nine historical collector
gaps remained visible. Other actual-client setup/demo/checkpoint flows,
independent clean-machine installation, native Mac/ARM, other client/IDE
entrypoints and continuous capture remain unqualified. Bounds, cancellation and
path checks do not make the MCP server an OS sandbox.

The owner reports policy approval through outside communications. Keep its
applicable scope distinct from technical validation and final Directory
acceptance. Do not infer that a prior approval automatically covers a changed
architecture or new attestations.

## Scan and submission record

Initial validation of `2546538d096b0c61bf7f59277e47ab1facef4a17` found one
interpreter-default blocker, three policy holds and four warnings. The 1.2.0
remediation documented the `python` default and replaced the development test's
real environment snapshot with a synthetic no-access guard. Runtime code and
existing absolute interpreter overrides were unchanged; development tests
remained public at the repository root.

Revalidation of `2a56314fbb69f0c707a3be18e904d09afc67e1bd` had no blockers.
Four warnings remained: no icon and the three Directory-only URL fields. Three
holds remained for interpreter/script manual review and a heuristic combining
the synthetic environment guard with documentation containing an HTTP string.
A passing validator did not clear those holds or establish organizational
eligibility. The later automated eligibility refusal is the current result.

Any future Directory action must use the actual current publisher eligibility
and explicit authority for the required acknowledgments. Existing reported
policy correspondence is distinct from Directory acceptance. Do not alter the
submitted source or create duplicate submissions merely to suppress a finding.
