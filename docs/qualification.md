# Local qualification record: Windows preview and prior evidence

Checked on 2026-11-10. This is a development record, not platform certification,
provider endorsement or Directory approval. Automated tests use synthetic inputs.
Separately authorized native Codex and Claude live sessions are recorded below,
with their exact scope and reconciliation. No earlier private session contents
were read for these controlled tests.

## 1.3.0-rc.1 journey candidate (2026-11-13, delivery held)

The five revision-1 [journey specs](journey.md) were authored before implementation
at `a7e086b`. Application checkpoint `f075581` adds the actual device renderer,
static supported next steps, and the narrow existing-store decision adapter.

Eleven new synthetic journey checks passed: snapshot/checkpoint continuity,
observed zero versus unavailable, complete/partial/unavailable rendering fixtures,
unassigned counts and hostile/long text, effect-free decision preview, exact and
concurrent retries, conflict refusal, supersession/history, canonical snapshot
binding, cancellation and bounded retrieval. This is source evidence, not human
usability or acceptance. A preceding 23-check MCP run passed 22 checks and failed
the old read-only annotation expectation after adding decision history; that test
expectation was corrected before the checkpoint. It has not been fully rerun.

The normal regression suite did **not run**. Automatic approval review twice
rejected its launch because the runner omitted the previously denied PowerShell
wrapper test. The denied test remained unrun and the rejection was not bypassed
with another test selection. Full regression approval remains a delivery gate.
Compilation, source-package validation and the installed Claude Code 2.1.287
marketplace and plugin-manifest validators passed independently.

A new isolated Claude profile installed the candidate with `configApplied: true`
and the explicit existing Python 3.12 interpreter before any model session.
Readback verified all 46 package source files and source digest
`0e98e8713a9aa8f6067d335a87e651ba920064cd84f76a8bc5ba121c1453ab0e`.
Direct stdio launched from that installed manifest returned version 1.3.0-rc.1
and all eight declared tools (seven slash commands plus info). No usage, inference,
credentials or production writes were part of this check. Five production
config/registry/catalog hashes stayed unchanged. This installed package belongs
to the application checkpoint above; subsequent documentation commits have their
own source/package identities. It does not prove a new authenticated-client journey.

The browser policy refused local file:// report inspection and prohibited a
workaround. Local report visual, narrow-width, zoom, keyboard, focus and contrast
checks remain unverified. Static markup and escaping checks do not replace them.
Actual Jo acceptance/usefulness, a new live canary, clean consumer/non-admin
Windows, native Mac/ARM and full client/IDE coverage also remain unverified.
Release publication, JO production update and the dependent website rollout are
held while the required regression/browser gates remain unresolved. No stable,
Directory or human-value claim follows from this candidate.

## 1.2.1-rc.1 independent Windows preview (2026-11-11)

The preview retains the declared-MCP I/O behavior and adds a self-hosted
marketplace, a distinct prerelease version to avoid reusing the 1.2.0 cache, and
more accurate existing-write descriptions in setup/demo/report plans. Those
new descriptions change plan hashes, not authorized paths or storage effects.
Runtime bytes are not identical to 1.2.0; historical native evidence stays separate.
Its scope is Windows AMD64 and Claude Code with existing trusted Python 3.10+.
The initial frozen preview package passed a fresh isolated Claude Code 2.1.287
profile installation, with an explicit absolute Python option saved before any
model session. A separate synthetic catalog passed 1.2.0 -> 1.2.1-rc.1 -> 1.2.0
-> 1.2.1-rc.1 transitions through supported marketplace/plugin update commands;
all source/cache hashes matched at each step and 15 retained synthetic files
remained unchanged. Direct installed-manifest stdio demo/report calls returned
300 synthetic tokens. No credentials were copied or model inference performed,
and production settings/registry/catalog hashes remained unchanged.

After the narrow plan-description and package-guard refinements, the final
permitted regression ran 148 tests: 147 passed, one existing symlink-privilege
check was skipped and one previously denied PowerShell-wrapper test was excluded.
All 23 focused MCP tests passed. Canonical source/artifact parity and final
fresh-profile package verification must be bound to the release identity
before publication. See [preview guide](windows-preview.md).
These checks are not a clean operating-system installation, an authenticated
fresh-client model/tool session, or GitHub network acquisition. Local-directory
startup loads source in place even when registry/cache updates are recorded.

The 1.2.0 remediation was independently audited and tested at local commit
`ee5c673ac41a5b7eae2f684472157b20d66d22e1`: 141 tests passed, one symlink-privilege
test was skipped and one previously denied PowerShell-wrapper test was excluded.
Public commit `2a56314fbb69f0c707a3be18e904d09afc67e1bd` has the identical tree
`aeab71e0b28ed21a85b1fbeb38c4d6842b991a87`; public and local commit identities differ.
Its runtime and command source matched the earlier native-qualified ca7ce54
except later distribution metadata. This preview does not relabel that native
qualification as a new integration run.

The Directory subsequently validated that 1.2.0 source with zero blockers,
four warnings and three policy holds, but refused the submission on organization
eligibility for local MCP/file capabilities. This is not Directory acceptance.
See [Directory status](directory-readiness.md) and [preview guide](windows-preview.md).
Dated descriptions below preserve what was known at each earlier checkpoint.

## Historical 1.2.0 declared-MCP qualification (2026-11-10)

Version 1.2.0 changes plugin execution to six declared stdio MCP tools. The
interpreter setting defaults to `python` resolved through the host PATH, without
a trust or version check. A fresh enabled install may launch it before an
override is configured. Before enabling, verify trusted installed Python 3.10+,
preferably with an explicit verified absolute path. The host launches it with
`-I -S -B`. The server can start with the enabled plugin but reads no usage or
device config at startup. The native collector remains a separate human-controlled
helper. All plugin commands use only MCP tools, without shell/CLI fallback.

Development checks are synthetic. The latest core regression executed 142 tests:
141 passed and one existing symlink-privilege test was skipped. The previously
denied PowerShell wrapper invocation test was separately excluded, not retried
or passed. All 21 focused MCP tests passed, including the final broken-stdout
regression: transport closure cancels queued operations and exits with failure
rather than silently continuing. Independent review earlier passed 20 MCP tests
plus four package tests. The exact integrated commit
`ca7ce5499aa48cd984c7438b34c356eded1a7912` was independently audited; the permitted
full regression was rerun with the same 141-pass, one-skip and one-excluded
result. Its source tree was `2aed661857cd71a2a7b2c7c5973aa0e7fa7e2e54` and
35-file package SHA-256 was
`a595746e85b4b6f4680471d1266246cf98029d56f4b2fa886d14b0ac6b8738fb`.
Publication documentation and manifest-link changes need their own final binding.

Coverage includes the isolated stdio entrypoint, protocol handling, bounded
reads, preview/apply scope hashes, SQL read-only access to current WAL data,
explicit sidecar-write scope, and cooperative cancellation. Hashes do not prove
human consent. Path checks are not an OS sandbox; same-user races, undetected
POSIX mounts and OS-blocked reads remain limitations. Failed/cancelled calls can
retain completed writes. See [MCP contract](MCP_SERVER.md) for exact bounds.

The native Windows Claude Code test naturally loaded the declared server from
that audited package. It completed exactly info, doctor and report preview,
followed by one separately approved report apply. There were zero permission
denials, no shell fallback and no unrelated tool calls. Plugin source/cache and
configuration remained unchanged. Normal existing client configuration can
initialize unrelated servers; that does not authorize using their tools and is
not the same as a fully isolated host. The existing helper stayed at 1.1.3.

Independent real-usage reconciliation completed at 20:58:07 UTC on 2026-11-10:

- Preview session: **4 input + 1,093 output + 7,349 cache-read + 10,014
  cache-creation = 18,460** tokens.
- Apply session: **4 input + 948 output + 10,829 cache-read + 7,940
  cache-creation = 19,721** tokens.
- Three direct post-export 1.2.0 reads were stable at **131,852 = 113,083 Claude
  + 18,769 Codex**. There were 32 stored Claude points, unchanged schema,
  successful SQLite quick check and no ingestion issues.
- The MCP-produced report showed **112,131** before its own apply session's
  final export. The later direct refresh differed by exactly 19,721. That
  direct verification is distinct from the report generated inside the session.

Attribution remained unassigned, coverage partial and nine historical collector
gaps remained visible. These are dated checkpoints, not automatic refresh,
continuous capture or complete ongoing native acquisition. Actual-client
setup/demo/checkpoint flows, other client/IDE paths, native Mac/ARM and independent
clean-machine installation remain unqualified. The historical 1.1.3 results
below are retained rather than being relabeled as MCP evidence.

Source publication for review is separate from Directory validation, security
scanning and acceptance. These tests alone establish neither submission nor acceptance; the later
Directory outcome is recorded above.

## Minimal portal remediation, still 1.2.0

The native-client qualification above used the explicit absolute interpreter
override before the manifest default was added. That installed override and the
runtime/command code remain unchanged; fresh unconfigured PATH resolution is
not qualified by that result. The root plugin path and version remain unchanged.
The default and synthetic preflight-test guard respond to the initial portal
findings described in [Directory readiness](directory-readiness.md). The later aggregate audit, exact-source tests and portal outcome are recorded
above. A source edit alone did not establish that a finding was resolved.

## Historical 1.1.3 deployment and verification (2026-11-10)

The helper from 1.1.3 commit `e85aff37ee03dce3804fb3c73a28f2f0e53a55ca`
was deployed through the normal approved path and reports healthy runtime 1.1.3.
Its 31-file package hash is
`39a552820382e93493f1989ca96e90a862aa94598008b52cfd5f93eac50b989d`.
All eight Claude points and 25 config/report files remained unchanged, with the
combined checkpoint still 41,026 tokens. Existing `pythonw.exe` and task settings
were preserved. Deployment involved a controlled gap, not uninterrupted capture.

The normal plugin update subsequently installed 1.1.3 with all 31 source/cache
files matching the package digest above. The operator supplied a passing validator
result. The corrected installed guide then executed exactly three PowerShell
commands: version, help and report, in `dontAsk` mode with no permission denials,
broader tools, root injection or fallback. This qualifies that restricted report
workflow, not every plugin command or client surface. Independent OTLP
reconciliation passed at 19:22:39 UTC on 2026-11-10: **8 input + 1,398 output +
32,481 cache-read + 18,758 cache-creation = 52,645** new tokens, matching the
independent usage result exactly. Eight new real delta points brought the store
to 16 Claude points, with no ingestion issues. Identity remained
`claude-sonnet-5-5`, `main`, `sdk-cli`, low effort, client 2.1.287; project
attribution remained unassigned without config changes.

Three post-export direct reports were stable at **93,671 = 74,902 Claude +
18,769 Codex**. The plugin's own report showed the earlier **41,026** snapshot
before its final usage export. The 93,671 result came from a separately authorized
direct refresh after export, without further inference. This latest dated
checkpoint does not imply automatic refresh, complete source acquisition or
continuous coverage. Earlier logging-network denial remains historical evidence,
not a claim that restrictions were bypassed or changed.

The exact-commit native test rerun did **not** pass: nine errors came from a
hardcoded `python3` alias returning WinError 1920, and one PowerShell wrapper
check encountered an AuthorizationManager denial. The six legacy test launches
now use the already-running interpreter via `sys.executable`. The permitted
rerun recorded 120 passes and one symlink-privilege skip among 121 executed tests.
The previously denied PowerShell test was explicitly excluded and remains blocked, not passed. No
test or runtime policy was weakened. A fresh WSL
launch was denied with `Wsl/E_ACCESSDENIED` and was not retried. Earlier preflight
results are historical, not a substitute for a current full-suite pass. Do not
change execution policy, privileges or network restrictions to force these checks.

An earlier visible local report was regenerated using the installed 1.1.3
launcher at 18:08:23 UTC and showed 41,026 tokens. The later 19:22:39 UTC
post-export checkpoint is 93,671 as described above. Reports remain saved
snapshots, not automatic or complete ongoing acquisition.

## Historical 1.1.x passed checks and preflight evidence

- Earlier preflight on native Windows 11 AMD64, existing Python 3.12.10:
  the 122-test suite passed,
  with one test skipped because the runner lacked Windows symlink privilege.
  No privileges or security settings were changed to enable it.
- Earlier preflight on WSL Linux, existing Python 3.12.3: the 122-test suite
  passed, with four
  Windows-specific tests skipped. This is not native macOS qualification.
- Claude Code 2.1.287: `claude plugin validate .` passed without warnings on
  the preceding 1.1.2 candidate. A fresh 1.1.3 validation attempt returned a
  network-policy error for a logging endpoint; that attempt is not a recorded pass.
  Manifest validation does not prove installation, command behavior or export delivery.
- Readable-source candidate builds are deterministic, contained and hashed.
  The contained launcher runs from an unrelated working directory, creates the
  synthetic demo, and does not write bytecode into the plugin source directory.
- Native PowerShell and CMD wrapper invocation passed. The synthetic HTML report
  rendered in native Edge, with 120 Codex plus 180 Claude tokens, explicit demo
  labeling and visible coverage qualifications.
- Foreground collector subprocess tests covered separate reporting, single-store
  exclusion, a forced stop of the test's own process, restart on the same port,
  duplicate replay without double counting, run identities and collection gaps.
  Graceful-stop and heartbeat-gap records are separately tested.
- An intermittent Windows HTTP rejection/reset was fixed with a bounded drain
  of safely framed rejected bodies, without parsing or retaining the content.
  The new delayed-body regression fails on the old handler; 60 repeated native
  HTTP tests passed after the fix. Malformed, oversized or stalled requests may
  still be disconnected rather than drained without a bound.
- Native Windows user-level Task Scheduler registration and initial health,
  duplicate-start prevention, controlled stop/restart, no-overwrite safeguards,
  same-version source relocation and rollback passed. Config identity, retained
  metrics and immutable receipts survived. Synthetic lifecycle input is confined
  to a separate test store and excluded from the live-provider report. Real
  logon/reboot/sleep was not exercised. Mac plist checks remain data-only.
- The installed collector passed 1.1.1 to 1.1.2, rollback to 1.1.1, and return to
  1.1.2. Health reported the expected version and the same store identity at each
  stage; 13 config/source/report/receipt hashes and all non-lifecycle SQLite data
  were preserved. This pair has no schema change and does not qualify a future
  schema migration. The earlier source remains available for rollback.
- Claude Code user-scope local plugin installation passed, with five commands,
  contained readable runtime and source hashes matched to the reviewed package.
  Same-version update/reinstall and 1.1.1-to-1.1.2 update/rollback preserved
  unrelated settings and synthetic test records. Both source and cache launchers
  matched the selected version. The local directory source loads in place; it is
  not immutable version pinning. The CLI requires a restart for activation, which
  was not exercised during those installation tests. Authenticated command loading
  subsequently passed, but application execution was denied as recorded below.
  No inference occurred during installation tests; the separate controlled Claude
  provider test below subsequently passed.
- Claude stream tests cover official query-source dimensions, version/entrypoint
  separation, delta and cumulative counters, duplicate conflicts in both orders,
  temporality changes, unit aliases, prospective boundaries and legacy-store
  ingest refusal. An independent focused review found no unresolved high- or
  medium-severity issue after the fixes.

## Controlled live Codex evidence

Native Codex CLI 0.160.0 with `gpt-6.1-sol` and low reasoning completed one benign
reply-only request without model tool calls. Three independent observations
agree: CLI usage output, its exact newly generated session JSONL and the installed
Cherry Meter device/project report.

- Total: **18,769** tokens.
- Input: **18,756**, including **12,416** cached-input tokens as a subset.
- Output: **13**; reasoning and cache-write counters: **0**.
- Workspace attribution matched the isolated test workspace.
- Repeated reports retained the same total, without replay double counting.
- Prompt/response text was absent from the measurement report.

Only that new session was copied to the explicitly permitted test source. This
qualifies controlled CLI ingestion, not automatic acquisition from all native
sessions, GUI/IDE clients or other devices. Expanding to the native sessions root
requires approval: the scanner reads historical file metadata before applying
the prospective accounting cutoff.

## Controlled real Claude and tandem evidence

Verified 2026-11-10 at 17:28:28 UTC on runtime 1.1.2. Native Claude Code 2.1.287
completed one controlled noninteractive `sdk-cli` reply-only turn, with low effort
and the Sonnet alias resolving to `claude-sonnet-5-5`.

- Independent JSON usage and actual OTLP delta metrics matched exactly: **500
  input + 13 output + 0 cache read + 0 cache creation = 513 tokens**.
- Four stored points retained `query_source=main`, `entrypoint=sdk-cli` and client
  version 2.1.287, with no ingest issues or fallback.
- Three reports remained stable at **19,282 = 18,769 real Codex + 513 real Claude**.
  This dated controlled-pair result is not a fixed forever total; later activity
  can legitimately increase it.
- Claude project attribution remained explicitly **unassigned**. No workspace
  mapping was inferred or changed to manufacture project attribution.
- A real collector termination/gap was detected and recovered before this test.
  The result does not establish uninterrupted capture or continuous coverage.
- The report was visibly opened through a local snapshot viewer. That viewer is
  not an auto-refresh dashboard; later usage requires a new report.

The retained private reconciliation record uses contract
`cherry-meter-live-reconciliation-v1`. Session identifiers, machine paths and raw
provider content are not part of this portable guide. This first result alone
does not qualify nonzero cache classes; the second result below does for the
same noninteractive path. Neither qualifies interactive CLI variants, completed
plugin report execution, GUI/IDE clients, subagents, native Mac/ARM or full native
source acquisition.

### Second checkpoint: cache-bearing plugin activation

Verified 2026-11-10 at 17:39:25 UTC. A second actual noninteractive `sdk-cli`
session independently matched **4 input + 610 output + 10,298 cache-read +
10,832 cache-creation = 21,744 tokens**, across four actual OTLP points. Nonzero
cache classes are therefore live-qualified for this controlled path.

At this checkpoint the store had eight Claude points with no ingestion errors.
Three direct reports remained stable at **41,026 = 18,769 Codex + 22,257 Claude**.
This is a later dated checkpoint, not a correction of the earlier 19,282 total
or a promise that future totals stay fixed. Project attribution stayed unassigned.
The SDK reported skill and plugin names literally as `third-party`; no specific
plugin identity was inferred from those fields.

The installed plugin/report command loaded, but its nested `Join-Path` version
check was permission-denied before execution. That model call produced no Cherry
Meter report. Direct authorized `device-inspect` reporting is separate evidence.
The corrected 1.1.3 guide subsequently passed the restricted version/help/report
workflow described above. That later success does not change this earlier denial
or turn its direct report into a plugin-produced report.

The hidden background task now uses the existing `pythonw.exe`, changing only
the executable. It is healthy against the same store with all points preserved.
The earlier termination cause remains unknown; neither recovery nor this change
proves uninterrupted or future continuous capture. The private second record
uses contract `cherry-meter-live-plugin-reconciliation-v1`.

For an independent test environment where each invocation is permitted, the
generic development commands are below. They are not plugin commands. On the
current machine, keep the previously denied PowerShell test excluded and do not
repeat the denied WSL or validator invocation merely because it appears here:

```text
python -m unittest discover -s tests -v
python -m compileall -q spend_outcomes scripts tests
git diff --check
claude plugin validate .
```

The final command requires an already installed compatible Claude Code CLI.
Do not install it or change machine policy merely to execute this checklist.

## Not run; do not claim support from the checks above

- Claude interactive CLI variants, Desktop Code tab, VS Code, JetBrains or Xcode
  provider delivery; plugin workflows beyond the restricted version/help/report test;
  subagents and ongoing acquisition beyond the selected
  Codex test session. The controlled noninteractive tandem result above does not
  qualify these paths.
- Native macOS Intel, macOS Apple Silicon or Windows ARM64 execution.
- First installation on a clean independent machine without a developer checkout.
- Logon/reboot recovery, actual sleep/wake continuity or a schema-changing upgrade.
  A source/plugin update does not prove the separately registered collector
  changed version; verify its health and exact task action independently.
- Directory approval or listing publication. The later source publication and
  validation did not establish acceptance; organization eligibility blocked it.
  Jo reports policy approval through outside communications;
  the underlying communication and its scope have not been independently reviewed
  here. This report does not require repeat outreach or establish listing approval.

## Next controlled qualification

These are separate operator/native verification tasks. The 1.2.0 plugin must
not execute helper installation, native CLI or lifecycle commands itself.

1. On each intended native platform, use a stable source path and existing Python,
   run the suite and synthetic demo, and retain platform/version results.
2. Obtain explicit approval for the selected real source roots, prospective
   tracking start and provider launch/settings scope. Review `export-plan`
   without copying secret headers. Respect any managed destination policy.
3. Have the operator start the separate foreground collector and check
   `collector-health`, then run
   one authorized controlled provider activity. Confirm token classes, model,
   query source, entrypoint, versions and unknown attribution remain accurate.
   Repeat for each advertised desktop/IDE launch path; one path is not another.
4. After separate startup-registration approval, have the operator review
   `lifecycle-plan` and install only that user-level definition, then test logon,
   sleep/wake, restart and upgrade.
   Confirm both the helper runtime version and data retention. Stop and remove
   only the approved test registration afterward.
5. Retain the reported policy approval and complete publisher prerequisites in `directory-readiness.md`
   before publishing or submitting. Failed or missing stages stay visible.
