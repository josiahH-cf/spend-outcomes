# Windows AMD64 / Claude Code preview

## Scope and prerequisites

This is the independent **1.2.1-rc.1** preview of Cherry Meter, distributed through
the project-owned `cherry-meter-preview` marketplace. It is not an Anthropic
Directory listing, endorsement or stable cross-platform release. The original
1.2.0 Directory branch and existing stable releases remain separate.

Use native Windows AMD64, an existing compatible Claude Code CLI, and trusted
existing Python 3.10+. The reference client is Claude Code 2.1.287. The public Git
marketplace route also requires existing trusted Git available on PATH; Claude
Code rejects Git found only in the current directory. An already extracted local
source directory does not require a Git download. Stop at missing prerequisites;
this preview installs no software or credentials for you. Review the
readable source and [privacy policy](../PRIVACY.md) before enabling it. Its
`python_executable` setting defaults to `python`, resolved using host executable
search rules. This is not a trust or version check. A fresh enabled plugin can
start that executable before an override is configured. Use the explicit install-time interpreter option below before starting a
session. Do not rely on an unverified default. Do not guess an interpreter or weaken machine policy.

The declared server uses `-I -S -B` and loads contained Python source. No runtime
download, package installation, credential creation or network access is part of
the plugin. It reads no usage at startup. The separate collector and provider
export settings are operator-controlled tasks, never plugin installation effects.
See [MCP contract](MCP_SERVER.md) for the full boundary and limitations.

## Install the reviewed preview

Check the first command for an existing Cherry Meter installation before running
the subsequent commands. Do not enable two copies; decide how to switch an existing
copy before installing.

The intended public source is the dedicated `preview/windows-1.2.1-rc.1` branch.
Use these commands only after its publication and exact revision are confirmed
in the release record. They are operator shell commands, not plugin skills:

```text
claude plugin list
claude plugin marketplace add "josiahH-cf/spend-outcomes#preview/windows-1.2.1-rc.1"
claude plugin install cherry-meter@cherry-meter-preview --scope user --config 'python_executable=C:\path to trusted Python\python.exe' --json
claude plugin list
```

Replace the example Python path with the verified absolute path to your existing
trusted Python 3.10+ executable. Quote the complete `key=value` argument as shown
in PowerShell, including when the path contains spaces. On the tested Claude Code
2.1.287 client, installation stores this setting before a model session starts;
confirm `configApplied: true` in its JSON result and inspect the saved option before
enabling a session. If your client does not support `--config`, stop and consult
its documented configuration workflow instead of starting the default executable.

The marketplace-add command downloads public source using the client's normal Git path.
Network or organization policy may prevent it; stop at that restriction rather
than changing security settings or using another route to evade a denial. The
marketplace entry points at `./`, the readable plugin at the repository root.
Do not add the raw `marketplace.json` URL: a URL-only catalog does not bring along
the files needed by its relative source.

An independently obtained, checksum-verified source directory can instead be
registered with `claude plugin marketplace add "C:\path\to\reviewed-source"`,
then the same install command with the verified absolute Python option. This local-directory route loads source in place;
retain it at that stable path and do not treat it as immutable cache pinning.
It is not evidence that public Git acquisition works.

Do not enable a second Cherry Meter copy alongside an existing installation.
Review `claude plugin list` first. A switch from another marketplace requires an
explicit decision about that existing copy and its interpreter configuration;
do not delete its source, private data or registered helper. The preview does
not silently migrate the production installation or enable auto-update.

After verifying the interpreter configuration, start a new Claude Code session
(or follow that client's reload instructions). Confirm version `1.2.1-rc.1`
through `cherry_meter_info`. Never treat source inspection or a registry entry
alone as proof the MCP server started correctly. Start with a synthetic demo in a new private local
directory. Review its preview, approve that exact scope, then apply. An existing
explicit approval can cover a matching plan. A scope hash is not proof of consent.
Use only the declared Cherry Meter tools, with no shell or file-reader fallback.
The synthetic demo reports 120 Codex + 180 Claude = 300 tokens, not real usage.

## Verify source before the first session

Download a source/plugin ZIP and its `SHA256SUMS` from the same prerelease. Compare
`Get-FileHash -Algorithm SHA256` for the ZIP with its published checksum before
extracting it into a new stable directory. The full-source ZIP includes public
tests and development docs; the plugin ZIP contains the smaller readable install
bundle. Neither includes a Python runtime or private device data.

For the plugin bundle, `CANDIDATE_SOURCE.json` lists each source file's size and
SHA-256. Verify those rows against the extracted files and, for a cached install,
the installed path reported by `claude plugin list --json`. Confirm that version,
marketplace, interpreter and source path are the expected ones before starting a
session. A local-directory install instead reads its registered source in place,
so verify and retain that directory, not only its cache. If any hash differs,
stop before enabling and obtain the matching reviewed source.

The release record identifies the exact public commit and Git tree. The local
build commit can differ from the public publication commit while sharing that
tree; never substitute one SHA in a GitHub link. Published ZIP source bytes use
canonical Git blob bytes (LF), rather than assuming a Windows checkout's CRLF
bytes have the same digest. Verify the actual ZIP digest and its per-file manifest.

## Updates and rollback

The plugin manifest is the single source of its version; the marketplace entry
does not duplicate it. Every distributed change receives a new version. Reusing
1.2.0 or republishing changed bytes under an existing preview version can leave
users on cached code. A local-directory install is the exception: it loads the
directory's current files, regardless of the version string.

For a catalog that tracks a maintained branch, review the new source/version,
then run `claude plugin update cherry-meter@cherry-meter-preview`. Confirm the
reported version and reload only after checking its interpreter and scope.
A version-specific branch or tag does not automatically follow a future release
line. Changing the catalog source is a separate deliberate step. Custom-marketplace
auto-update is normally off; this preview does not enable it.

Retain the previously reviewed source, manifest, interpreter setting and package
hashes. For rollback, disable the affected plugin, restore the previously
reviewed catalog/source through the client's normal plugin controls, reinstall
and verify its exact version before enabling it. Do not assume uninstalling a
plugin removes or rolls back a separately registered helper. Preserve private
config, metrics, reports and receipts. No schema-changing rollback is qualified.

## Dated local packaging check (2026-11-11)

A fresh isolated Claude Code 2.1.287 configuration on the existing Windows AMD64
machine accepted the root-source marketplace and installed 1.2.1-rc.1 with the
explicit absolute Python option. `configApplied: true` and the saved interpreter
were checked before any model session. No authentication was copied and no model
inference was used. Production settings, plugin registry and catalog hashes were
unchanged.

A separate synthetic catalog exercised 1.2.0 -> 1.2.1-rc.1 -> 1.2.0 -> 1.2.1-rc.1.
After each approved test-catalog source switch, the normal commands were:

```text
claude plugin marketplace update TEST_MARKETPLACE --json
claude plugin update cherry-meter@TEST_MARKETPLACE --scope user --json
```

All three transitions updated the recorded version/path and verified every cached
source hash. Fifteen synthetic retained files stayed unchanged. These were local
catalog source switches and registry/cache updates; local startup still loads
source in place. They do not prove immutable pinning or a public Git download.
Direct stdio calls using the installed manifest's configured interpreter produced
a clearly synthetic 300-token demo/report. This was a protocol test, not an
authenticated Claude client invoking those tools.

After the plan-description and build-guard refinements, the final permitted
regression executed 148 tests: 147 passed and one existing symlink-privilege check
was skipped. The previously denied PowerShell-wrapper test was separately
excluded, not retried or passed. The canonical source and final-artifact checks
must be bound to the release identity before publication.

## Qualification and unresolved limits

See [qualification](qualification.md) for dated evidence and final preview checks.
The earlier 1.2.0 native Windows test exercised discovery, info, doctor, report
preview and one approved report apply with an explicit absolute Python override.
It is not a new 1.2.1-rc.1 client run. Isolated testing on an existing development machine
does not establish first installation on a clean independent operating system.

No native Mac Intel/Apple Silicon or Windows ARM64 support is qualified. Other
IDE/GUI/interactive paths, fresh unconfigured interpreter startup, sleep/reboot
continuity and complete daily capture remain unqualified. Existing reports show
partial coverage and unassigned Claude attribution; token totals are dated saved
snapshots. Selected tool output may enter Claude's hosted conversation even
though the measurement engine itself makes no remote requests.

## Official distribution references

Checked 2026-11-11. The catalog uses a required name, owner and plugin list, with
the plugin's source relative to the catalog root. See
[marketplace creation](https://code.claude.com/docs/en/plugin-marketplaces) and
[source reference](https://code.claude.com/docs/en/plugins/marketplace-reference).
GitHub catalog refs, installation scopes and updates are documented under
[plugin management](https://code.claude.com/docs/en/discover-plugins).
The install-time `--config` option is in the
[CLI reference](https://code.claude.com/docs/en/plugins/cli-reference).
The Windows Git prerequisite is documented in
[plugin troubleshooting](https://code.claude.com/docs/en/plugins/troubleshooting#command-git-not-found-or-is-in-an-unsafe-location).
Manifest version changes control cached updates, while local paths load in place;
see [hosting and versions](https://code.claude.com/docs/en/plugins/host-marketplace).
