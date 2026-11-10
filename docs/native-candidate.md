# Native helper and 1.2.0 declared-MCP plugin candidate

## Status and boundaries

Version 1.2.0 is a declared-MCP source candidate, not a stable release or a marketplace-approved listing. One native Windows Claude Code path passed natural server discovery, info, doctor, report preview and one approved report apply, without denials, shell fallback or unrelated tool calls. Other actual-client setup/demo/checkpoint workflows remain unqualified. Earlier 1.1.x controlled measurements, shell-guided reporting and collector registration/restart remain separate historical evidence. Interactive CLI variants, desktop/IDE emission, macOS Intel/Apple Silicon, Windows ARM64, lifecycle after sleep, independent clean-machine installation and Directory acceptance remain gaps. WSL testing is not macOS testing. See `qualification.md` for the exact evidence and limits.

The package is independent of Agent Telemetry. Do not connect its database, registry, scheduler or outcome integrations. Existing project commands and private reports remain compatible. Device mode is additive and uses an explicitly separate device config.

## Plugin execution boundary

The interpreter setting defaults to `python` on the host PATH, which is not a
trust or version check. A fresh enabled plugin may start that default before an
override is configured. Before enabling, verify trusted installed Python 3.10+,
preferably by configuring its explicit absolute path. The qualified native
workflow used that absolute override; unconfigured PATH startup remains unqualified.
The host runs the declared `cherry-meter` stdio MCP server
with that executable and `-I -S -B`. It can start with the enabled plugin but reads
no usage or device config at startup. All five plugin commands call only the
declared tools. They must not execute the native CLI, start the helper, call a
shell, or use arbitrary file-read tools as a fallback.

Setup, demo, report and checkpoint use preview/apply. Show the exact plan and
obtain actual user permission unless valid existing explicit pre-approval covers
that exact scope, then repeat identical scope with the plan hash.
The hash guards stale scope, not authenticated consent. Reporting may write
private snapshots and scoped SQLite `-wal`/`-shm` sidecars; it is SQL read-only,
not filesystem-write-free. Paths, bounded processing, cancellation and partial
write limitations are documented in [MCP_SERVER.md](MCP_SERVER.md).

The separate metrics helper survives plugin sessions and is installed or managed
only as an explicit human-controlled task. The plugin does not perform any of
the following native CLI, export or lifecycle instructions.

## Human-controlled native CLI, without installing a runtime

Keep `native/` beside the matching readable `spend_outcomes/` source package inside the plugin root. The source launcher does not use an adjacent archive. No wrapper downloads Python, installs packages, edits PATH, changes execution policy, creates credentials or registers a service. An existing Python 3.10+ must be on PATH. The compatibility pyz builder remains separate from the directory-source package.

Windows PowerShell:

```powershell
& 'C:\path with spaces\cherry-meter\native\cherry-meter.ps1' --version
```

An alternative CMD entrypoint is also included. Respect local execution restrictions; do not use it to bypass a denied action:

```cmd
"C:\path with spaces\cherry-meter\native\cherry-meter.cmd" --version
```

Untested macOS invocation for an operator with an existing runtime (invocation through `sh` needs no executable-bit change; this is not platform qualification):

```sh
sh '/absolute/path/cherry-meter/native/cherry-meter' --version
```

The wrappers pass arguments as arguments, preserve application exit status and work from an unrelated working directory. Commands printed by the Python engine are authoritative for that installed version. Do not concatenate user data into shell command strings; use a shell argument array or quote each path appropriately.

## Human-controlled helper setup

Ask the operator to confirm private paths outside the repository, the execution-device label, project workspace and every Codex source root. Never infer permission from a default path. Suggested state destinations are user-chosen folders under Windows LocalAppData or macOS Application Support, but no directory is created automatically merely because it is conventional. Retain the state directory across code/plugin upgrades.

For the operator's separate native CLI task after approval, the interface is:

```text
device-init --config CONFIG --state STATE --project KEY --workspace WORKSPACE
  [--codex-root APPROVED_ROOT ...] [--claude] [--name LABEL]
  [--device-name LABEL] [--target-tokens N]
  [--outcome TEXT --success-criterion TEXT --checkpoint ID=TEXT]
```

This creates only the config. It does not inspect source logs, change provider settings, install a collector service or read historic Claude transcripts. Review the generated tracking start and bindings before collection. Legacy project configuration is not overwritten or implicitly migrated.

```text
doctor --config CONFIG
collect --config CONFIG [--port 4318]
device-inspect --config CONFIG [--days 7|30|90] [--through YYYY-MM-DD] [--html]
```

`doctor` only checks the configuration and explicit binding existence. It does not prove metrics emission. `collect` is a foreground loopback metrics receiver with single-store exclusion, heartbeat/run evidence and crash/restart accounting. Start it only with permission and keep it independent of the reporting conversation. Closing the report does not stop an independently running collector; stopping the collector or sleeping/restarting the machine can lose exports. `collector-health` identifies the selected store and running runtime version without reading user usage sources.

`lifecycle-plan` generates reviewable user-level Windows Task Scheduler XML or a Mac LaunchAgent plist in a staging directory. The command returns manual commands but never registers, starts, stops or removes an OS task. A separately approved Windows registration, controlled restart, relocation and 1.1.1-to-1.1.2 upgrade/rollback were tested; real logon/reboot and sleep behavior remain unqualified. This version pair has no schema change. Generated plans require a stable source path; plugin synchronization does not update a separately registered helper automatically. Do not claim unattended continuity or complete coverage.

`device-inspect` uses the config's private state destination. Retain client/model/service identity and separate per-source tracking-start, freshness and error states. Zero observed usage is not unavailable usage. Remote SSH/container/cloud execution is another device, not automatically included in the local report. Legacy `checkpoint`, `target` and `outcome` commands still require explicit project selection and operator-authored decisions.

## Prospective Claude configuration

Use only the exact exporter protocol and token metric schema supported by this candidate. The receiver is not a general OTLP collector. Show any proposed environment/settings patch separately and obtain approval before applying it. Never overwrite existing instrumentation, enable logs/events/prompts, expose a listener beyond loopback, or reuse unrelated project telemetry. This candidate does not apply any such settings itself.

The receiver accepts uncompressed OTLP HTTP/JSON `resourceMetrics` at
`http://127.0.0.1:4318/v1/metrics`, and only retains the `claude_code.token.usage`
monotonic sum and its allowed metadata. Protobuf, logs, trace endpoints, browser
origins and compressed bodies are rejected. Exports require model, token type,
session ID and service name. Official query_source, model speed/effort and named
agent/skill/plugin/MCP dimensions keep independent streams separate. Explicit
entrypoint and version observations remain visible; missing values stay unknown.
Known user/account/repository identity fields are fingerprinted rather than stored
raw, which is not a claim of anonymity. Unknown dimensions fail closed with a
visible issue. Workspace attribution needs an observed workspace
attribute or explicit session/service-to-workspace binding in the source config.
Without it, activity remains in device totals and is marked unassigned to projects.

The loopback receiver does not authenticate local exporters. Any process on the
same machine can submit synthetic data, so service/model labels are observations,
not proof of provider identity. Use only on a trusted local host. No token or
credential is created by this candidate. Configure the actual client's supported
metrics-only HTTP/JSON exporter only after checking its installed version; this
historical 1.1.x builds verified one controlled native Windows Claude Code 2.1.287
noninteractive `sdk-cli` delivery under approved temporary launch configuration.
Independent usage output matched all four OTLP token classes (513 total).
A second controlled session matched 21,744 tokens including nonzero cache-read
and cache-creation. Later direct reports held 41,026 tokens across both providers.
An initial plugin application command was denied before execution. A subsequent
normal 1.1.3 update and corrected installed guide passed exactly the restricted
PowerShell version/help/report workflow without permission denials or fallback.
At 19:22:39 UTC on 2026-11-10 that session independently reconciled 52,645 new
tokens, including both cache classes, with no ingestion issues. Three post-export
direct reports held 93,671 = 74,902 Claude + 18,769 Codex. The plugin itself
reported 41,026 before its final export; a separate authorized direct refresh,
without further inference, produced the later snapshot. Attribution stayed
unassigned, and neither snapshot implies automatic refresh or continuous capture. These tests do not qualify
other launch paths or continuous capture. A collector termination/gap was detected and recovered before that test.
These are not 1.2.0 MCP integration results. See the dated tandem result in `qualification.md`; project attribution remained
unassigned rather than inferred.
`export-plan --entrypoint cli|vscode|desktop` prints the official metrics-only
proposal and required effective-absence checks. It never reads secret headers,
applies the plan, or overrides managed/launcher policy. Beta tracing and inherited
headers require separate review; a shell unset alone does not prove a setting is absent.

Terminal environment variables alone do not configure app-launched desktop or IDE sessions. Verify the actual supported client version and each launch path. Keep a recorded qualification matrix for CLI, desktop, VS Code, JetBrains and any Xcode integration before claiming coverage. A successful synthetic receiver test is not a successful provider integration test.

The initial common tracking start is prospective. Data predating it must not be backfilled accidentally, and cumulative exports may require a baseline before a meaningful delta. Unknown workspace/account attribution remains unknown. Estimates, token counts and remaining account allowance are different measures.

## Claude Code plugin

The repository root contains `.claude-plugin/plugin.json`, `commands/`, `native/mcp_server.py` and the readable source runtime. The declared MCP server can start when the plugin is enabled; there are no hooks or automatic usage reads. Submit the root rather than an inner folder. Local loading must follow the actual Claude Code version's supported plugin procedure. Verify the candidate with that client's validation tool when permitted; structural tests alone do not certify Directory acceptance or native-client integration.

The plugin guides explicit setup, synthetic demo, report, checkpoint and read-only diagnostics through MCP tools. It bundles readable application source, not the Python interpreter, and installs no helper itself. The controlled 1.2.0 native Windows test used an existing trusted runtime and left source/cache/config unchanged. It does not establish independent clean-machine usability, other actual-client command workflows or managed-listing delivery. A local directory marketplace loads source in place: keep that source reviewed and stable, rather than treating it as immutable version pinning. Managed-listing tests remain separate from the owner's reported policy approval. No opaque native binary is claimed to be signed/notarized.

## Updates, removal and recovery

Keep private config, store and receipts outside source/plugin directories. Updating or removing the plugin/wrappers does not delete those files. Back up private state before a separately approved schema migration. Do not promise rollback compatibility with a version that cannot read a newer schema. Removal of approved provider settings, collectors or services is a separate explicit action; never silently remove existing instrumentation or user data. No uninstall operation is executed by this candidate.

The 1.1.1 candidate introduces an explicit Claude stream-identity accounting
version. A nonempty older/unmarked store remains readable with a legacy
qualification, but new ingestion is held. Do not replay old observations into
the new identity format or silently retag the database. A reviewed prospective
cutover to a new private store and tracking start is required; retain old config,
store and immutable reports separately. No existing user store was migrated here.

## Verification

Run permitted tests on each target OS using an existing trusted runtime. Tests
use synthetic temporary files and protocol/CLI checks; they do not read user logs,
change telemetry settings, install software or start persistent services. The
previously denied PowerShell wrapper test remains excluded on this machine; do
not bypass the denial or call it passed. Actual Claude-host MCP startup and tool
use require a separately approved integration test. Test native macOS and Windows
ARM64 separately before claiming support.
