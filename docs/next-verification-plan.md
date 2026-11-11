# Remaining verification and directory plan

## Current independent preview track (2026-11-11)

Version 1.2.1-rc.1 prepares an independent Windows AMD64 / Claude Code marketplace.
Complete isolated clean-profile install, update/rollback, package/MCP checks and
independent review before publishing. Keep actual public Git acquisition separate
from local-catalog testing. Do not retry denied network or PowerShell operations,
change security settings or copy credentials to make a test pass.

The 1.2.0 source was published and validated; its Directory submission was refused
on organization eligibility for local MCP/file capabilities. Preserve that
submission and source branch. No repeat submission or eligibility claim is part
of this preview. See [preview guide](windows-preview.md) and
[Directory status](directory-readiness.md). Native Mac/ARM, a fresh independent
OS, other client surfaces and daily continuous capture remain separate tracks.

The dated 1.2.0 plan below preserves its evidence and execution boundaries; its
publication/submission checklist is historical, superseded by the status above.

## Historical execution gates (2026-11-10)

The 1.2.0 implementation declares six MCP tools. The interpreter setting now
defaults to `python` on the host PATH, which is not trust-verified and can launch
on a fresh enabled install before an override is configured. Before enabling,
verify trusted Python 3.10+, preferably with its explicit absolute path. The
qualified native path used that override. Launch arguments remain `-I -S -B`.
The server can start with the enabled plugin but reads no usage automatically.
All plugin commands are MCP-only. Installing/managing the native helper and
changing exporter settings remain separate human-controlled tasks.

The latest permitted core regression executed 142 tests: 141 passed and one
existing symlink test was skipped. The previously denied PowerShell invocation
test was separately excluded, not retried. All 21 focused MCP tests passed;
independent review earlier passed 20 MCP tests and four package tests. Bind the
permitted test results, package hashes and audit to the final integrated revision
before publication. These synthetic checks are separate from the actual client
result below.

A controlled 1.2.0 native Windows test on audited commit
`ca7ce5499aa48cd984c7438b34c356eded1a7912` naturally loaded the declared server.
Info, doctor, report preview and one approved report apply passed with zero
denials, no shell fallback and no unrelated tool calls. Source/cache/config
remained unchanged. Independent reconciliation at 20:58:07 UTC held 131,852 =
113,083 Claude + 18,769 Codex across three direct post-export reads. The MCP
report itself was 112,131 before the apply session's 19,721-token final export.
Attribution remained unassigned, coverage partial and nine historical collector
gaps visible. This does not qualify actual-client setup/demo/checkpoint workflows,
other clients/platforms, continuous capture or full ongoing native acquisition.

Before testing additional actual-client workflows, settle their scope and permission:
candidate path/version, trusted interpreter, synthetic private destinations,
allowed Cherry Meter tools and existing authentication. Normal existing client
configuration may initialize unrelated MCP servers; do not invoke their tools
or change client configuration as a workaround. Record host initialization
separately. Exercise the still-unqualified setup, demo and checkpoint workflows
with explicit approvals (existing pre-approval may cover an exact plan) and stable
synthetic totals. Preserve historical receipts. Stop at any denied action rather
than substituting shell or CLI fallback.

Preview hashes are stale-scope guards, not authenticated consent. Report approval
must include the listed SQLite `-wal`/`-shm` writes as well as report destinations.
Read/path/time bounds and cancellation are cooperative, not an OS sandbox or
guaranteed rollback. Inspect approved destinations after failure before retrying.

Source publication for review must bind the final audited tree to the dedicated
`directory/cherry-meter-1.2.0` branch and verify the public URLs. The browser draft
is unsubmitted and every compliance checkbox remains unchecked. No 1.1.3 branch
was published. Source publication is not Directory acceptance.

The initial portal validation blocked the missing interpreter default and held
the dynamic command, unread-through Python source and a development-test
credential heuristic. Keep the repository-root plugin path and version 1.2.0.
Audit and test the explicit default plus synthetic no-environment-access test
guard, publish only the reviewed forward change, and revalidate its exact commit.
Do not move source merely to suppress holds or promise automated scan clearance.

## Historical 1.1.x deployment and test evidence

The 1.1.3 `e85aff3` helper deployment passed: healthy runtime 1.1.3, verified
31-file package, all eight Claude points and 25 config/report files preserved,
and the same 41,026-token checkpoint. Existing `pythonw.exe` and task settings
were retained. A controlled deployment gap is recorded in `qualification.md`.

The normal update now installed plugin 1.1.3, with all 31 source/cache files
matching the reviewed package. The operator supplied a passing validator result.
The corrected installed guide executed exactly the version/help/report PowerShell
commands in `dontAsk` mode, without permission denials, broader tools, root
injection or fallback. That restricted report workflow passed. Independent OTLP
reconciliation at 19:22:39 UTC on 2026-11-10 matched 52,645 new tokens exactly:
8 input + 1,398 output + 32,481 cache-read + 18,758 cache-creation. Eight new
delta points brought the store to 16 Claude points with no ingestion issues.
Three post-export direct reports held 93,671 = 74,902 Claude + 18,769 Codex;
project attribution remained unassigned. The plugin's own report showed 41,026
before its final export. A separate authorized direct refresh, without further
inference, produced the later snapshot; automatic refresh and continuous coverage
are not established. Keep the earlier network denial as historical evidence and do not
infer authority to override future restrictions.

Earlier preflight suites passed 122 tests on Windows (one skip) and WSL (four
skips), but the exact-commit native rerun failed on nine hardcoded `python3`
alias errors (WinError 1920) and one PowerShell AuthorizationManager denial.
A test-only correction to `sys.executable` resolved the alias errors. The
permitted rerun recorded 120 passes and one symlink-privilege skip among 121
executed tests. The previously
denied PowerShell test was explicitly excluded and remains blocked, not passed.
Use an existing permitted Python runtime for the normal
`python -m unittest discover -s tests -v` check, without execution-policy or
privilege changes. A fresh WSL launch was denied with `Wsl/E_ACCESSDENIED` and
was not retried. WSL revalidation remains a human/environment prerequisite,
not evidence of a current suite pass. Keep these gates separate from the earlier
live-provider reconciliation, which remains valid within its documented scope.

## 1. Retain the reported policy approval and its scope

Jo reports Directory policy approval received through outside communications.
The underlying communication and its exact scope have not been independently
reviewed here. No repeat inquiry is required by this plan. Record the reported
approval separately from technical qualification and final listing approval.

Keep the applicable scope with the release evidence: approved Codex JSONL
metadata access, the prospective loopback collector, and readable-source packaging
with an existing Python runtime. Do not assume the report covers unrelated
architectures or future changes. It does not establish a completed Directory
security scan, submission, reviewer decision or publication. Preserve the
Codex-and-Claude goal and the existing privacy boundaries.

## 2. Retain the first live Windows pair and qualify remaining paths

The Codex half passed for one controlled native CLI session: 18,769 tokens matched
CLI output, its exact new JSONL and the installed report, with repeated reads
remaining stable. The selected source contains only this session. On 2026-11-10,
one native Claude Code 2.1.287 low-effort noninteractive `sdk-cli` turn on
`claude-sonnet-5-5` also passed: independent usage and actual OTLP delta matched
500 input + 13 output + zero cache read/creation = 513. Three reports retained
19,282 = 18,769 Codex + 513 Claude at that checkpoint. This is not a fixed total
for future reports. Claude project attribution remained unassigned.

A collector termination/gap was detected and recovered before that test; no
uninterrupted-capture claim is supported. A second actual session matched 21,744
Claude tokens including nonzero cache-read/creation, bringing the later stable
checkpoint to 41,026 combined tokens. Installed-plugin report-command loading
passed, but its nested version check was denied before execution; direct reports
are separate evidence. A later corrected 1.1.3 guide passed the restricted
version/help/report workflow; its independent metrics reconciliation passed at
19:22:39 UTC with the later 93,671-token checkpoint described above.
Interactive CLI variants, GUI/IDE, Mac/ARM and ongoing full native source
acquisition remain open.
The procedure below applies to additional approved client/launch paths, not a
requirement to repeat the completed controlled pair.

These are separate operator/native tasks, not actions for a plugin command.
The 1.2.0 plugin must use its declared MCP tools and never invoke this CLI path.

**Prerequisites supplied/approved by the operator:** exact provider and account,
one benign test prompt/workspace, permitted source roots, prospective start,
private config/state paths, and the specific launch/settings scope. Approve any
inference cost limit when API billing applies. Existing authentication must work;
new credentials, purchases and billing changes are outside this plan.

**We can do after approval:** inspect only the approved settings/source scope,
review `export-plan`, and prepare the smallest isolated launch configuration.
Never expose secret headers, override a managed destination, read unrelated
history or alter an existing instrumentation setup without separate permission.
Use a new private store for the 1.1.1 identity schema rather than migrating an old
store implicitly.

1. Have the operator start the foreground collector independently of the report
   conversation and confirm `collector-health`, runtime version and selected store identity.
2. Run one explicitly authorized small activity through existing Claude Code
   CLI, then allow an export interval. Separately exercise the intended Codex
   path with approved logs, ideally a new isolated test session.
3. Confirm observed token classes, model, request category, entrypoint and
   versions, and compare available provider diagnostics. Unknown account/project
   attribution stays unknown. Token accounting is not a bill or quota balance.
4. Produce a tandem report, repeat the read without replay double counting, and
   verify reports do not own or terminate the collector. Stop only the test
   collector and restore only the exact approved temporary configuration.

**Exit condition:** retain a versioned result for each client/launch path with
expected versus observed fields, permitted inputs and gaps. A synthetic receiver
POST, manifest validation or working CLI alone does not qualify an IDE or app.

## 3. Verify native Mac and remaining launch paths

**Operator prerequisite:** provide access to a native Mac with existing Python
3.10+, Git and the already installed clients to be tested. Intel and Apple Silicon
are separate targets. No suitable Mac was available for this pass; WSL cannot
stand in for either. Windows ARM64 is also a separate untested target.

**We can do when available:** stage the reviewed candidate in an isolated local
directory, inspect platform/runtime versions, run the full test suite and
synthetic demo, and verify the contained launcher from another working directory.
If a required runtime is missing, stop at that prerequisite rather than install
it. Source transfer must preserve the exact candidate revision.

Then repeat the approved live procedure for every intended surface, one at a
time: native CLI, Claude Desktop's Code tab, VS Code, and JetBrains or other
advertised IDE integrations. Each needs its actual supported configuration path
and separate evidence. A terminal environment variable does not prove an
app-launched client inherited it. Do not claim ordinary Claude chat or Cowork
coverage from Code-tab tests.

**Exit condition:** a platform/client/version matrix that clearly separates
passed, failed and never-run cases. If an architecture is unavailable, leave it
unqualified rather than implying cross-platform certification.

## 4. Qualify unattended startup separately

**Operator decision:** approve the exact user-level Task Scheduler or LaunchAgent
definition, stable source path and private state destination. Review the generated
`lifecycle-plan` before registration. A separately approved Windows user-level
collector is now installed; controlled stop/restart, source relocation and
1.1.1-to-1.1.2 upgrade/rollback passed without a schema change. Schema-changing
upgrades and real logon/reboot/sleep checks remain distinct evidence requirements.

**Operator action outside the plugin:** review the exact definition and register
only the approved task. Separately test logon, graceful stop, failure/restart,
sleep/wake and an upgrade. Check `collector-health` after each transition, including runtime version,
and inspect gaps without claiming uninterrupted delivery. Keep private stores and
old immutable receipts. Remove only the approved test registration if requested.

Plugin synchronization and collector upgrades remain separate operations. An
account-installed plugin can sync to Claude Code; a direct CLI installation stays
local. Neither guarantees that a registered helper now executes the new version.

## 5. Prepare and submit only after the gates are resolved

**We can prepare:** scoped claims, reviewed source, tests, three working reviewer
examples, and the privacy/support/documentation content. Fix gaps identified by
the applicable reported policy approval scope and rerun affected checks.

**Publisher decisions/actions:** choose listing ownership and verified contact;
verify the published source, policy, support and documentation URLs for the
exact submitted revision; connect the appropriate GitHub identity; review compliance and legal
terms; submit and request publication. These remain gated actions, not side
effects of development.

Follow `directory-readiness.md`: repository-root plugin path, exact release ref,
Validate, fix/revalidate, listing/data-handling fields and reviewer evidence, then
review submission. Every tracked version is scanned. Default publication requires
a publisher request and Anthropic reviewer; later auto-publication depends on
listing mode. Do not call the candidate Directory-ready before the required
evidence and approvals exist.
