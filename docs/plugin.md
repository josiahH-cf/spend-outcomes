# Cherry Meter 1.2.0 source plugin candidate

The repository root is the plugin root. Keep `.claude-plugin/plugin.json`,
`commands/`, `native/` and `spend_outcomes/` together. The candidate contains
readable Python and no downloaded runtime, opaque archive or external source
checkout dependency.

## Install and execution boundaries

Version 1.2.0 declares the `cherry-meter` stdio MCP server.
`userConfig.python_executable` defaults to `python` resolved through the host's
PATH, not a verified runtime. A fresh enabled plugin may start it before an
override is configured. Before enabling, verify a trusted existing Python 3.10+
runtime, preferably by setting its verified absolute path. Native qualification
used the explicit absolute override, not unconfigured PATH startup.
The host launches the configured executable directly with
`-I -S -B` and the contained `native/mcp_server.py`. The server can start with the
enabled plugin, but startup reads no usage or device config. It makes no network
requests and starts no child process or collector.

The five commands are `/cherry-meter:setup`, `/cherry-meter:demo`,
`/cherry-meter:report`, `/cherry-meter:checkpoint`, and `/cherry-meter:doctor`.
They use only declared MCP tools. Missing prerequisites and held operations must
be reported; shell, PowerShell, native-launcher, arbitrary file-read and external
consumer fallbacks are prohibited.

The separate native metrics helper and provider exporter settings remain explicit
human-controlled installation tasks. Enabling, updating or removing the plugin
does not install, update, stop or remove that helper. See
[MCP contract](MCP_SERVER.md) and [native helper instructions](native-candidate.md).

## Permission and data boundaries

Setup, demo, report and checkpoint use preview/apply. Review the returned plan,
obtain actual user permission for its exact reads and writes, unless valid existing
explicit pre-approval already covers that scope, then apply matching arguments
with `expected_plan_sha256`. The hash binds scope and stale config
bytes; it does not authenticate consent, authorize new data, or persist a grant.

Reporting reads bounded approved sources in-process and writes private snapshots.
Claude SQLite is opened SQL read-only with no schema/data migration, but the
explicitly scoped `-wal` and `-shm` sidecars may be created or updated. Diagnostics
read only the selected config and path existence. Tool output may enter Claude's
hosted conversation under the user's Anthropic settings and policies.

Paths must be ordinary absolute local paths; symlinks/reparse points, traversal,
UNC/device syntax and Windows mapped network drives are rejected. These checks
are not an OS sandbox. Same-user path races, undetected POSIX network mounts and
OS-blocked reads remain limitations. Processing limits and cancellation are
cooperative; completed writes may survive a failed or cancelled operation.
Inspect the approved destinations before retrying.

## Package and qualification

Build a new deterministic source directory outside the checkout with:

```text
python scripts/build_candidate.py --output NEW_DIRECTORY
```

The builder records file hashes in `CANDIDATE_SOURCE.json`, refuses existing
destinations and does not install or publish. Do not submit the legacy pyz as a
hidden dependency. Keep private config, stores and reports outside source/cache
directories.

Earlier 1.1.x local installation, upgrade/rollback and restricted shell-guided
report results are historical. The 1.1.3 live checkpoint was 93,671 = 74,902 Claude
+ 18,769 Codex in three direct post-export reports; the plugin itself showed the
earlier 41,026 snapshot before its final export. Those results do not qualify
1.2.0 MCP startup, configuration, tool selection or reporting in an actual client.
A separate controlled 1.2.0 native Windows test naturally loaded the declared
server and passed info, doctor, report preview and one approved report apply,
with zero denials and no shell or unrelated tool calls. It left source/cache/config
unchanged. Other actual-client command workflows and platforms remain unqualified.
See the complete [qualification record](qualification.md), including the dated
131,852-token post-export checkpoint and its partial-coverage limits.

A local-directory marketplace can load mutable source in place. Keep it reviewed
and stable, verify the exact version/cache and restart the client when required.
Do not substitute the old 1.1.3 cache for the distinct 1.2.0 candidate. Source
publication for review does not complete portal validation, security scanning,
attestations or Directory acceptance.
