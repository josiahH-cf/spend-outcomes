# Cherry Meter support and troubleshooting

Use the [project issue tracker](https://github.com/josiahH-cf/spend-outcomes/issues)
for public bug reports and setup questions. This route promises no response time.

## Version 1.2.0 plugin checks

1. Read [MCP prerequisites](MCP_SERVER.md). Select a verified absolute path to a
   trusted, already installed Python 3.10+ executable in plugin configuration.
   If it is missing or cannot start, stop at that prerequisite. Do not download
   a runtime, guess a path or change OS policy.
2. Use the declared `cherry_meter_info` tool for version and boundaries.
   Version 1.2.0 uses MCP-only plugin commands. Do not run the native launcher,
   shell or an arbitrary file reader as a fallback. Historical 1.1.3 client
   success is not proof that the 1.2.0 integration works.
3. For an approved device config, `cherry_meter_doctor` reads that config and
   checks path existence only. It does not read usage, inspect SQLite, probe the
   receiver or repair anything.
4. If a report is held, review its exact preview scope. Use absolute local paths
   without symlinks/reparse points or UNC/device syntax. Do not broaden roots or
   change permissions merely to make a report pass. Plan hashes reject stale
   scope; they do not grant consent.
5. Reports can write private snapshots and explicitly listed SQLite `-wal`/
   `-shm` sidecars. Cancellation is cooperative and completed writes may remain.
   Inspect approved destinations before retrying a failed or cancelled operation.
6. A report is a saved snapshot. After approved exports arrive, preview/apply
   `cherry_meter_report` again with the same approved config. Reopening HTML
   does not refresh data, prove continuous capture or recover earlier gaps.

## Separate human-controlled helper

Missing prospective Claude metrics may mean the independent helper is stopped,
the actual client did not receive approved exporter settings, or a source exceeds
the supported schema. The operator can inspect the helper through the separate
[native workflow](native-candidate.md); the plugin must not execute that workflow.
Do not replace existing telemetry settings, expose a receiver beyond loopback or
create startup registrations as a troubleshooting side effect.

Plugin updates and registered-helper updates are separate. Keep private config,
stores and reports, check exact runtime versions, and retain old source paths
while startup definitions still reference them.

## What to include in a public issue

Include version, operating system/architecture, relevant Python/Claude Code
versions, tool name, expected behavior and a short error with private values
removed. A synthetic demo reproduction is preferable to real data.

Do not attach raw provider logs, reports, config files, stores, session IDs,
workspace paths, account information, credentials or telemetry headers. Describe
a suspected security/privacy issue generally and request a suitable private
route before sharing details; do not post secrets or an exploit publicly.

See [data handling](../PRIVACY.md) and [qualification](qualification.md).
One controlled 1.2.0 native Windows info/doctor/report path passed; other client
paths, clean-machine installation and Directory acceptance remain unverified.
Earlier 1.1.x results retain their separate historical scope.
