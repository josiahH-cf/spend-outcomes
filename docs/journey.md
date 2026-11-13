# Cherry Meter public journey and backend

The intended user is an individual builder using Claude Code and Codex on one execution device. The outcome is qualified usage beside explicitly reported progress, sufficient to support a human keep/change/investigate/hold decision. Forward collection is sufficient. Attribution is explicit and may be unassigned. There is no productivity score, billed spending/ROI claim, team administration or automatic outcome completion.

The implementation basis is [CM-J01](specs/CM-J01.md) through [CM-J05](specs/CM-J05.md), revision 1. Their ready status is specification readiness. Verification, installation, publication and human acceptance require their own evidence.

## Existing backend at the 1.2.1-rc.1 source boundary

| Journey | Actual owner/path | State and boundary |
| --- | --- | --- |
| Install/start | `.claude-plugin/plugin.json`, `native/mcp_server.py` | Existing Python loads contained source with `-I -S -B`; no usage/config read on startup, no helper start |
| Setup | `commands/setup.md` -> `mcp.execute` -> `device.initialize(write=False/True)` | Exact config preview, exclusive new config creation; no source reads; independent helper/export installation |
| Diagnose | `cherry_meter_doctor` -> `read_config`, `device.doctor` | Config/path existence only; no receiver probe or settings repair |
| Report | `cherry_meter_report` -> bounded `observer` -> `device.device_report` -> `core.inspect` | Configured Codex metadata/Claude SQL reads; one captured source for all views; immutable JSON and HTML in device-reports; approved SQLite sidecars |
| Progress | `cherry_meter_checkpoint` -> guarded config replacement | Operator-only status/history; config byte guard and lock/temp writes; old snapshots unchanged |
| Render | `device.render_device` | Static private HTML; source metadata escaped; old MCP path omitted refresh instructions |
| Legacy decision | `__main__.py record` -> `core.save_record` -> `storage.atomic_bytes` | `pv-decision-v1` immutable decisions; only `pv-receipt-v1` accepted by old CLI |

CM-J02/03 change the real renderer and supported command guidance without changing report accounting. CM-J04 adds a narrow declared device-report compatibility adapter to the existing decision store, plus bounded retrieval; this is an explicitly authorized backend extension. It reads no usage and starts no work.

## Audit and verification boundary

Pre-change source audit established metadata-before-outcome hierarchy (UX-002, P03/P06/P08/P10/P11, AP-04), absent MCP refresh guidance (UX-003, P02/P04/P05/P09/P12/P13), and absent device decision compatibility (UX-004). Public docs already distinguish preview and legacy, and the Resources card already links to `/resources/spend-outcomes`; preserve and refine them (UX-001, P01/P07/P16).

SC-01/02/03/04/06/08 were partial by source inspection. SC-05 is not applicable to the original form-free static report. SC-07/09 require rendered overflow, keyboard, focus and contrast checks; SC-10 retains ordinary browser exit with no automatic action. No customer findability, time-to-success or human value is inferred. A local `file://` browser inspection was refused by the browser protocol policy; no alternate route was used to evade that refusal. Rendered verification remains separate from markup/source tests.

Keep historical live-provider and hosted Windows evidence in [qualification](qualification.md) separate from new candidate checks. Installation, clean consumer Windows, Mac/ARM and actual Jo usefulness are independent claims.
