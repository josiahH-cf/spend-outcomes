# Windows preview synthetic CI qualification

This QA-only branch is not a release or an Anthropic Directory submission. The frozen release source and ZIPs remain unchanged.

## Scope and trigger

`.github/workflows/windows-preview-qa.yml` runs only for a push to `qa/windows-preview-1.2.1-rc.1` in `josiahH-cf/spend-outcomes`. It has one standard `windows-latest` x64 job, a 20-minute timeout, `contents: read`, and no repository secrets, login, inference, deployment, package publishing, dependency cache, artifact upload or persistent credential configuration. It does not change repository settings, main, tags or the Directory branch. The built-in short-lived read-only GitHub token is used by official checkout/setup actions, not exposed to the plugin harness.

The public repository's Actions setting already allows actions. No workflow or Actions policy existed at preparation time. Standard hosted runners are free for public repositories. No larger runner, paid storage or account change is requested. Results use job logs and a summary rather than artifact uploads. The branch trigger avoids adding a manual-dispatch workflow to main.

## Exact source binding

- Frozen preview local source: `7b5b10faaff685ed911e058856e03957c4d5d427`, tree `0e740a6ef1689b1db2db9f200f1199011b9e81cd`.
- Existing public baseline: `2a56314fbb69f0c707a3be18e904d09afc67e1bd`, tree `aeab71e0b28ed21a85b1fbeb38c4d6842b991a87`, equivalent locally to `ee5c673ac41a5b7eae2f684472157b20d66d22e1`.
- Preview package: 37 files, SHA256 `ed694f99885f1d9bc3c25f750dcb2e0441f7e0f8fea802a55ca03fa196d26673`.
- Baseline canonical LF package: 35 files, SHA256 `0b1ad726bbce6f695339f4c80b56a6c177c1f9f4684d5a90a79205fa4f37dff7`.

`expected-source.json` enumerates the 59 preview and 56 baseline tracked public files, modes, Git blob identifiers, lengths and SHA256 hashes. `materialize_sources.py` reconstructs each expected tree identifier and checks every actual Git blob before writing canonical bytes under the new runner-temp directory. This avoids Windows checkout CRLF conversions. Only QA files and this workflow may be added to the preview tree; no release-source file may differ. Each version's existing audited builder then creates a separate readable plugin fixture, including its generated `CANDIDATE_SOURCE.json`.

This is a supported CI checkout of public source for a newly scoped hosted test, not a retry of a denied local GitHub clone or proof that the public Git marketplace install route works. The harness installs from the resulting local directories. Do not describe local SHA `7b5b10f` as a public commit unless separately verified.

## Pinned prerequisites

- Official `actions/checkout` v6 commit `d23441a48e516b6c34aea4fa41551a30e30af803`.
- Official `actions/setup-python` v6 commit `ece7cb06caefa5fff74198d8649806c4678c61a1`, exact Python 3.12.10 x64, no package cache or pip installs. The official Python versions manifest lists that Windows version.
- Claude Code 2.1.287 portable Windows x64 executable, fetched only from Anthropic's versioned HTTPS URL. It is checked for exact size 247736480 bytes, SHA256 `6d5be51f0edfe3429cd1a9885950db31c1e59eb9a2c9a30a47e64179d2ff98b4`, and a valid Authenticode signature from Anthropic before execution. The checksum and URL were independently read from Anthropic's manifest and Microsoft's WinGet catalog on 2026-11-11. No downloaded installer script is executed. There is no version or download-source fallback.

The harness verifies exact executable versions again. It uses a fresh unauthenticated Claude profile and explicit absolute Python configuration. It checks install/cache bytes, direct declared-manifest stdio preview/apply with synthetic 300-token input, and the local-catalog sequence 1.2.0 -> preview -> 1.2.0 -> preview while checking retained synthetic data. No user data, real provider logs, private profiles, helper deployment or model call is involved.

## What a pass means

A pass demonstrates a fresh GitHub-hosted Windows x64 VM and fresh-profile local-directory installation/lifecycle with synthetic direct-MCP execution. GitHub's Windows VM is a preprovisioned developer image running as administrator with UAC disabled. This is not stock consumer Windows 11, non-admin installation, authenticated fresh-client MCP use, public Git marketplace acquisition, Mac/ARM or continuous collection qualification. Local-directory marketplaces can execute source in place; cache/registry updates do not prove immutable runtime pinning. Existing 1.2.0 signed-in client evidence remains historical.

No CI success is claimed until a run at the exact independently audited QA commit completes and its results are inspected. Previously denied PowerShell wrapper and WSL tests are not retried by this job.

## Official references

- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://github.com/actions/checkout/blob/d23441a48e516b6c34aea4fa41551a30e30af803/action.yml
- https://github.com/actions/setup-python/blob/ece7cb06caefa5fff74198d8649806c4678c61a1/action.yml
- https://github.com/actions/python-versions/blob/main/versions-manifest.json
- https://code.claude.com/docs/en/setup
- https://downloads.claude.ai/claude-code-releases/2.1.287/manifest.json
- https://github.com/microsoft/winget-pkgs/blob/master/manifests/a/Anthropic/ClaudeCode/2.1.287/Anthropic.ClaudeCode.installer.yaml
