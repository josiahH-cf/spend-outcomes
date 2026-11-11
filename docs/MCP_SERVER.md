# Declared MCP server, version 1.2.0

Current independent distribution: **1.2.1-rc.1 Windows AMD64 / Claude Code preview**.
See [preview installation and limits](windows-preview.md). The 1.2.0 evidence below is
historical; it does not establish new platform or workflow qualification.
This execution/data-handling contract applies to both 1.2.0 and 1.2.1-rc.1.
The preview does not expand its authorized reads, writes or execution.

Cherry Meter's Claude plugin runs its application tools inside the declared
`cherry-meter` stdio MCP server. Commands do not execute a shell, the native CLI,
an external consumer, or a second Python process. The independent native CLI and
metrics collector remain available for explicit operator use outside the plugin.

This is a source-readable candidate, not a claim of Directory acceptance or
qualified delivery on every platform. Historical 1.1.3 live observations do not
qualify this new 1.2.0 MCP integration.

## Interpreter and startup

The plugin manifest declares `userConfig.python_executable` as required, with the
reviewable default `python` and an explicit operator override. That default resolves
through the host's executable search rules, including PATH; it does not verify
identity, trust, version or availability.
An enabled fresh install may launch it before an absolute override is configured.
Before enabling, verify that the resolved command is an already installed, trusted
Python 3.10+ binary, or configure its verified absolute path. Qualified native
testing used an explicit verified absolute interpreter, not the unconfigured
default. Existing explicit interpreter selections are unchanged by the default.
No runtime download, package installation or automatic fallback is provided.
The host directly launches the configured executable with these literal arguments:

`-I -S -B ${CLAUDE_PLUGIN_ROOT}/native/mcp_server.py`

`-I` ignores Python environment/user-site and unsafe implicit import paths; `-S`
skips site initialization; `-B` avoids bytecode writes. The launcher adds only its
contained source root for imports. These flags protect a real Python runtime, not
an arbitrary executable the operator has mistakenly selected. Runtime trust is
an installation prerequisite, not something the already-running server can prove.

An enabled plugin may start the declared MCP server automatically. Startup only
loads bundled code and serves protocol messages. It does not discover or read a
device config, scan logs, open the metrics store, contact a receiver, create a
helper, register a scheduled task, change telemetry settings or persist access.

## Tool surface

- `cherry_meter_info`: version, protocol, available operations and boundaries;
  no user-file access.
- `cherry_meter_doctor`: read the exact approved device JSON config and check
  declared path existence. No usage, SQLite, receiver probe or writes.
- `cherry_meter_setup`: preview/apply one new explicit device config. Its parent
  must exist. Reads no usage, refuses overwrite, creates no store or helper.
- `cherry_meter_demo`: preview/apply a new private synthetic directory. Writes
  fixtures, a config, a store, reports and their adjacent lock files. No real data.
- `cherry_meter_report`: preview/apply bounded configured-source reads, private
  immutable JSON/HTML reports, and possible SQLite sidecar writes described below.
- `cherry_meter_checkpoint`: preview/apply an exact operator-reported checkpoint,
  preserving history. Writes only the config and adjacent lock/temporary files.
  Multiple-project configs need a project-specific outcome.

Only info and doctor are annotated read-only. The other tools can write, even
though their default preview mode does not. All tools declare closed-world local
behavior. Annotations are hints, never authorization or a sandbox.

No generic CLI/command/file-read tool is provided. Legacy telemetry consumers,
arbitrary exports, record/import/export/show operations, collector startup,
service registration and OS/settings changes are not reachable through MCP.
The independent CLI's existing behavior remains available to the operator.

## Preview write details in 1.2.1-rc.1

The preview adds `write_details` to setup, demo and report plans to describe
existing file effects; it does not change storage behavior or broaden paths.
These details participate in the plan hash. A hash from an earlier plan is stale
and cannot authorize the new plan. Inspect and approve the current exact scope.

- Setup directly creates the one new config with exclusive creation. Its
  `atomic_files` and `sqlite_files` lists are empty and `directory_creation` is
  false. There are no setup lock/temp, state or SQLite files. Interruption can
  leave a partially written new config, which must be inspected before retry.
- Report lists JSON and optional HTML atomic output categories, using the
  generated digest as a filename placeholder, their persistent adjacent lock
  files and temporary filename patterns. It identifies possible creation of
  the report directory and missing parents, and repeats the already-scoped
  SQLite `-wal`/`-shm` paths. SQL schema/data are not modified by reporting.
- Demo lists five directories and four atomic file categories inside its new
  root: synthetic JSONL, config and JSON/HTML reports. It also lists its synthetic
  SQLite store and possible `-wal`, `-shm` and `-journal` files. It reads no real
  usage. These synthetic writes are distinct from report access to an existing
  metrics store.

Atomic writes leave adjacent lock files. Temporary files are normally renamed
or removed, but interruption can leave them. Check approved destinations after
failure; neither a timeout nor cancellation guarantees rollback. The placeholders
are descriptions only, never paths used to drive I/O.

## Exact scope and actual consent

The operator first approves reading the exact configuration path. File-affecting
tools default to `apply=false`, returning an exact plan and `plan_sha256`.
For reports, this includes the current configuration bytes' SHA-256, source roots,
project/workspace bindings, tracking starts, report directory and UTC window.
For setup/checkpoints, it includes the precise proposed content/update.

The assistant must show the plan and verify actual user approval for every listed
read and write. Valid existing explicit pre-approval can cover the exact scope;
do not ask repeatedly for an unchanged action already authorized. Obtain new user
approval when any scope is new or unclear. Only then repeat the same arguments with `apply=true` and
`expected_plan_sha256` set to the returned hash. A changed plan is rejected.
The hash is a scope/staleness guard, **not proof of human consent**. A model can
compute or repeat it; the host/user permission workflow remains essential.
Neither the hash nor `permitted=true` creates a standing permission. No roots or
grants are automatically persisted outside an explicitly approved new config.

Unknown source, project and device fields are rejected rather than echoed to the
client. Configs must use the device schema, not a legacy executable consumer.
Config contents and metric labels are data, never instructions. Returned tool
results are visible to the connected Claude client and may enter its conversation;
no-network behavior does not mean that client receives no private metadata.

## SQLite and the independent collector

The MCP reader opens the configured store with SQLite `mode=ro` and `query_only`.
It does not initialize, migrate, ingest into or change SQL schema/data. This is
**SQL read-only, not filesystem read-only**. SQLite may create or update the
exact `<store>-wal` and `<store>-shm` sidecars to access current WAL data. Those
paths are included in the report plan and require approval along with the report
destination. The reader does not use `immutable=1`, which could omit recent WAL
points. A missing, incompatible or oversized store is unavailable, not zero.

The existing separately installed helper keeps running independently. Nothing in
the plugin starts, stops, installs or upgrades it. An operator may separately
follow the native lifecycle documentation with an explicitly reviewed stable
source path, Python runtime, config, account, port and scheduler definition. They
must review/register/start it themselves outside the plugin. Provider metrics-only
export settings are another explicit operator step; the plugin never enables
prompt, response, tool, transcript or event export. Existing config, store and
tracking-start boundaries must survive upgrades.

## Bounded transport and reads

The standard-library server implements newline-delimited UTF-8 JSON-RPC with MCP
protocol version 2025-06-18: initialize/initialized, ping, tools/list, tools/call
and cancellation notifications. It advertises only tools. Unsupported requests
receive protocol errors; unknown notifications receive no response. No protocol
resources, sampling, elicitation, HTTP transport or external calls are claimed.

- One serialized operation worker, at most eight queued requests. Reader and
  writer synchronization lets the client cancel queued or running work.
- Input frame limit 128 KiB; oversized frames close the transport. Duplicate JSON
  keys, non-finite numbers, invalid UTF-8, malformed requests and unknown arguments
  are rejected. Stdout contains only protocol messages, not debug output.
- Config limit 1 MiB; 20 projects; at most two source kinds and 20 Codex roots.
- Codex bounds: 256 files, 2 MiB/file, 256 KiB/line, 10,000 enumerated entries
  per root, 10-second scan deadline and a 15-second cooperative processing budget.
  Hitting a bound reduces coverage or makes the source unavailable.
- Claude store plus sidecars: 64 MiB before opening; 50,000 rows/table;
  32 KiB/cell; 16 MiB retained snapshot; ordinary tables/columns only. SQLite
  operations have a 10-second progress deadline and a short lock timeout.
- Report JSON limit 16 MiB; protocol response limit 2 MiB. Output-limit errors
  disclose that a write may already have completed, rather than implying rollback.

Paths must be absolute and ordinary local files/directories. Traversal, UNC and
device syntax, Windows mapped remote/unknown drives, symlink/reparse components
and startup/OS write destinations are rejected. Guarded traversal uses no-follow
entry metadata before classifying a directory. Workspace strings from Codex and
Claude metadata are guarded before filesystem normalization. POSIX network mounts
cannot reliably be distinguished here and remain unqualified.

These checks are not an OS sandbox or protection against a malicious same-user
path-swap race. Deadlines/cancellation are cooperative and cannot forcibly stop
an OS-blocked read. A host may terminate a blocked server. Completed writes are
not rolled back, and a failed or cancelled call must not be blindly retried.
Reports stay private and historical receipts are retained. The helper's uptime,
receiver reachability and real-client delivery are not proved by an MCP report.

## Verification and official references

Synthetic tests cover the actual isolated Python stdio entrypoint, protocol
framing/errors/cancellation/queue bounds, scope hashes, no subprocess/network
calls during demo/report/checkpoint, SQL read restrictions with current WAL data,
input limits and unsafe paths. These tests alone do not establish signed-in Claude discovery,
macOS support, Directory acceptance or new live-provider compatibility.

On 2026-11-10, native Claude Code qualification of version 1.2.0 at commit
`ca7ce54` naturally loaded the declared server and invoked the exact info, doctor
and report-preview tools, followed by one separately approved report apply.
There were no denials, shell calls or unrelated tool invocations. Plugin source,
cache and configuration bytes remained unchanged. This is a narrow actual-client
success, separate from manual JSON-RPC testing. Actual-client setup, demo and
checkpoint workflows remain unqualified, as do macOS, Cowork and other GUI paths.

Independent reconciliation at 20:58:07 UTC found 131,852 observed device tokens:
113,083 Claude and 18,769 Codex, stable across three direct 1.2.0 reads. The MCP
report snapshot contained 112,131 tokens before the subsequent 19,721-token export
from the report-apply turn. These observations remain partial, include unassigned
usage and retain nine historical collector gaps; they do not establish complete
coverage, billing, acceptance or benefit.

An authorized normal client startup may
initialize unrelated existing MCP servers under unchanged configuration. Restrict
test tool invocation to the exact approved Cherry Meter tools; never invoke an
unrelated server's tools as part of this qualification.

- [Claude plugin manifest reference](https://code.claude.com/docs/en/plugins-reference)
- [MCP 2025-06-18 lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [MCP tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
