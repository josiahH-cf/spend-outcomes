# Cherry Meter customer setup prompt

You are helping me configure the versioned Cherry Meter archive that I
downloaded on WSL. Work only inside the boundaries below. Do not install system
packages, discover log roots, broaden permissions, edit my project repository,
or use an external orchestration service or Agent Telemetry.

The product was previously called Spend & Outcomes. Its archive is still named
`spend-outcomes.pyz`, and existing config and state paths remain valid.

Guide me one decision at a time:

1. Ask for the paths to `spend-outcomes.pyz`, `SHA256SUMS`, and this prompt.
   Confirm that all three came from the same versioned GitHub release. Run
   `sha256sum -c SHA256SUMS` from their directory and stop if the archive does
   not match. Run `python3 spend-outcomes.pyz --version` and show me the version.
2. Confirm that this is WSL and that `python3 --version` is 3.10 or newer. If a
   prerequisite is missing, name it and stop; do not install it for me.
3. Ask for one project display name and its exact WSL workspace. Resolve and show
   the path, confirm it exists, and ask me to approve it. Do not inspect the
   project’s files.
4. Propose a Codex JSONL root, normally `$HOME/.codex/sessions`, but do not scan
   it yet. Ask me to confirm that exact root and permission to read only JSONL
   files below it. Ask separately before adding any other root or checkout.
5. Ask what successful use of this project would look like. Ask for one success
   criterion and whether named checkpoints would help. Make clear that all
   checkpoint status is operator-reported and never inferred from usage.
6. Ask for an advisory observed-token target for a rolling seven-day UTC window,
   or offer to start without a target and establish a baseline first. Explain
   that the target cannot pause, gate, or change work.
7. Propose a short local project key and private config/state paths under
   `$HOME/.config/spend-outcomes` and `$HOME/.local/state/spend-outcomes`. Keep
   both outside the project Git tree. Show the complete `init` command with all
   chosen values and ask for approval before running it.
8. Run the approved `init` command once. It must create only the config and must
   not read logs. Show me the generated config with source paths and private
   values summarized, not copied into chat unnecessarily. Do not overwrite an
   existing config; ask whether I want a different path or an explicit update.
9. Show the exact printed `inspect_argv`, ask permission, then run it. Report the
   saved HTML path, observed window, token amount, coverage, target status, and
   operator-reported checkpoint status. Do not paste raw logs or complete private
   receipt JSON into chat.
10. If the source is absent, malformed, ambiguous, partial, or refused, preserve
    the config and existing reports. Name the affected source and give one
    corrective step. Do not call partial coverage a complete comparison.

Before finishing, remind me that opening a saved HTML file performs no refresh;
the report’s refresh command reads the approved source again. Show the manual
`checkpoint` command for one checkpoint, but run it only after I explicitly say
that checkpoint happened. Usage and assistant activity must never advance it.

If I have no eligible Codex log source, offer this isolated synthetic alternative
without claiming it measures my project:

```sh
python3 /path/to/spend-outcomes.pyz demo \
  --root "$HOME/.local/state/spend-outcomes-demo"
```
