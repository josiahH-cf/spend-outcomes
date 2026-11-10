# Directory preparation: 1.2.0 declared-MCP candidate

## Current status

Version 1.2.0 is a source candidate for review, not a stable release or an approved
Directory listing. Its dedicated publication branch is
`directory/cherry-meter-1.2.0`; verify the actual remote commit before submission.
No `directory/cherry-meter-1.1.3` branch was published.
The public repository's default `main` branch still contains the legacy 1.0.1
release. Do not submit that default branch as the new plugin.

Use the repository root as the plugin path after publication. The contained
readable runtime includes a declared local stdio MCP server, started by the host
with the configured interpreter. The default `python` resolves through the host
PATH and is not trust-verified. A fresh enabled install may launch it before an
override is set; verify trusted Python 3.10+ before enabling, preferably with its
explicit verified absolute path. The qualified native test used that override. It can
start with the enabled plugin, but reads no usage at startup. All plugin commands
use only declared MCP tools; helper installation is separate and human controlled.
See [MCP contract](MCP_SERVER.md), [native helper setup](native-candidate.md),
[data handling](../PRIVACY.md) and [support](support.md).

The verified public support route is the
[repository issue tracker](https://github.com/josiahH-cf/spend-outcomes/issues).
Policy and documentation pages are prepared locally. Publish and verify their
actual HTTPS URLs before adding `privacyPolicyUrl`, `supportUrl` and
`documentationUrl` to the manifest. A prepared URL is not a live page.

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

## Portal preparation and remaining steps

Initial validation of commit `2546538d096b0c61bf7f59277e47ab1facef4a17`
reported one blocking interpreter-default finding, three reviewer holds and
four warnings. The holds concerned a dynamic MCP command, Python source the
scanner did not follow, and a credential heuristic combining a development
test's environment snapshot with that dynamic command. The warnings concerned
the missing icon and the three Directory-only URL fields. A warning is not a
failed native test, and a hold is not approval or rejection.

The remediation keeps version 1.2.0 and the repository-root plugin path. It adds
an explicit, documented `python` default and changes the preflight test to a
synthetic no-environment-access guard. Runtime code and existing absolute
interpreter overrides are unchanged. Development tests remain public in place;
no nested package is used to hide a finding. The changed source must be validated
again. Do not claim these edits clear the scan or avoid manual Python review.

A local browser draft was prepared with no existing submission found. No
compliance box was checked and no submission was completed. Recheck portal state
before continuing; drafts and duplicate submissions count toward limits.

1. Bind integrated source review and the scoped native-client result to the
   final revision. Do not replace historical evidence with broader claims.
2. Publish the reviewed source to a dedicated version-matching branch, preserving
   existing releases. Verify its exact commit, public links and applicable checks.
3. Reuse the draft for this repository/root. Enter the final branch explicitly,
   especially when its name contains a slash. Run Validate again after every
   source change; results apply only to the commit read.
4. Confirm listing ownership and a reachable publisher contact without inferring
   legal identity from a LICENSE author or a GitHub display name.
5. Review data handling. The plugin reads and stores selected local metadata.
   Tool plans/results may enter Claude's hosted conversation even though the MCP
   server makes no network requests. Local state is retained until operator
   deletion, potentially longer than 30 days; that is not a hosted retention
   service. The listing is not intended for people under 18.
6. Keep all attestations unchecked until their exact facts and authority are
   settled. The portal asks whether the plugin executes code outside declared
   MCP servers. The redesign is intended to move plugin operations into the
   declared server, but implementation intent is not an accepted attestation.
   Review the actual source, runtime behavior and applicable approval first.
7. Review [Directory Terms](https://support.claude.com/en/articles/13145338-anthropic-software-directory-terms)
   and compliance requirements. Prepared update preferences are scheduled checks
   only and auto-publish off; do not create a webhook or expand permissions.
8. Submit only after required approval, then follow security/reviewer outcomes
   and a separate publication decision. Validation alone does not make it live.

Official workflow: [submit a plugin](https://claude.com/docs/plugins/submit).
Structural and security checks: [pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist).

## Updates remain separate

Plugin synchronization does not update a separately registered helper. Retain
private state, verify the helper's exact runtime and startup path separately,
and do not remove a runtime directory still referenced by a startup definition.
