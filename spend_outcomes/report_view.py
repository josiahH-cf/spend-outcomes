"""Static device presentation. No execution, network, storage or inferred progress."""
import html

from .core import digest, encoded


STYLE = '''
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#172b36;background:#fafbf9}
*{box-sizing:border-box}body{margin:0;font-size:1rem;line-height:1.6;overflow-wrap:anywhere}
header,main,footer{max-width:72rem;margin:auto;padding:1.5rem}header{padding-top:2.5rem}
h1,h2,h3{line-height:1.25}h1{font-size:clamp(1.8rem,5vw,2.8rem);margin:.4rem 0 1rem}
h2{font-size:1.5rem;margin:0 0 1rem}h3{font-size:1.2rem;margin:.2rem 0 .8rem}
p{margin:.5rem 0}.eyebrow{font-weight:700;color:#8c193a}.muted{color:#445763}
.badge{display:inline-block;padding:.2rem .7rem;border:1px solid #8d9da4;border-radius:1rem;font-weight:600}
.notice{border-left:4px solid #8c193a;padding:.7rem 1rem;background:#f9edf0}
.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,19rem),1fr))}
article,.panel,details{border:1px solid #bdcacf;border-radius:.7rem;padding:1.2rem;background:#fff}
section{margin-bottom:2.5rem}article p:last-child{margin-bottom:0}.number{font-size:2.3rem;font-weight:700;line-height:1.2}
nav{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;margin-top:1.2rem}a{color:#075d88;text-underline-offset:.2em}
a,summary{min-height:2.75rem}nav a{display:inline-flex;align-items:center}summary{cursor:pointer;font-weight:650}
details{margin:1rem 0}details[open]>summary{margin-bottom:1rem}li{margin:.4rem 0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;background:#edf2f3;padding:1rem;border-radius:.4rem}
code{font-size:.9em}dl{margin:.5rem 0}dt{font-weight:600}dd{margin:0 0 .5rem}
.source{padding:.8rem 0;border-bottom:1px solid #d7dfe2}.source:last-child{border:0}
:focus-visible{outline:3px solid #8c193a;outline-offset:4px}.skip{position:absolute;left:1rem;top:-5rem;background:#fff;padding:.5rem}.skip:focus{top:1rem}
@media(max-width:36rem){header,main,footer{padding:1rem}header{padding-top:1.5rem}article,.panel,details{padding:1rem}.number{font-size:2rem}}
@media print{.skip,nav{display:none}body{font-size:11pt}header,main,footer{padding:.5rem}article{break-inside:avoid}}
'''


def render(report, refresh_command=None, *, config_path=None, receipt_path=None):
    def esc(value):
        return html.escape(str(value if value is not None else 'Unknown'), quote=True)

    def amount(value):
        return esc(format(value, ',') if type(value) is int else value)

    def para(label, value):
        return '<p><strong>' + esc(label) + ':</strong> ' + esc(value) + '</p>'

    def name(source):
        return {'spend-outcomes-codex': 'Codex', 'cherry-meter-claude': 'Claude Code'}.get(source.get('producer'),
            {'codex': 'Codex', 'claude-otel': 'Claude Code'}.get(next(iter(source.get('sources', [])), {}).get('kind'), 'Configured source'))

    c = report['consumption']
    identity = digest(report)
    pieces = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>Cherry Meter: ' + esc(report['device']['label']) + '</title><style>' + STYLE + '</style></head><body>',
        '<a class="skip" href="#main">Skip to report</a><header><p class="eyebrow">Cherry Meter · Device report</p>',
        '<h1>' + esc(report['device']['label']) + '</h1>',
        '<p><strong>Observation window:</strong> ' + esc(c.get('from_day')) + ' to ' + esc(c.get('to_day')) + ' (inclusive UTC)</p>',
        para('Tracking start', report['tracking_start']), para('Generated', report['generated_at']),
        '<p class="badge">Saved snapshot</p><p class="muted">Opening this report does not refresh it. Later activity and checkpoints need a new report.</p>']
    if report.get('synthetic'):
        pieces.append('<p class="notice"><strong>Synthetic demonstration only.</strong> No real usage was read or measured. Sample progress and decisions are not your results.</p>')
    pieces.extend(['<nav aria-label="Report sections"><a href="#coverage">Coverage</a><a href="#projects">Projects and progress</a>',
        '<a href="#providers">Providers and models</a><a href="#next">Next steps</a></nav></header><main id="main">',
        '<section id="coverage" aria-labelledby="coverage-heading"><h2 id="coverage-heading">What this report covers</h2><div class="grid">',
        '<article><h3>Device observations</h3><p class="number">' + amount(c['tokens']) + '</p><p>Observed tokens</p>',
        '<p><strong>Coverage: ' + esc(report['coverage']['status']) + '</strong></p>',
        '<p class="muted">Known observations from configured local sources. Unknown is not zero. Token volume is not benefit or billed spending.</p></article>',
        '<article><h3>Source coverage</h3>'])
    for source in report['sources']:
        coverage = source.get('coverage', {})
        pieces.append('<div class="source"><p><strong>' + esc(name(source)) + '</strong> · ' + esc(coverage.get('status', source.get('status'))) + '</p>')
        counts = [('unassigned_sessions', 'unassigned sessions'), ('unassigned_events', 'unassigned metric events'),
                  ('ambiguous_sessions', 'ambiguous sessions'), ('ambiguous_events', 'ambiguous metric events')]
        found = [str(coverage[key]) + ' ' + label for key, label in counts if key in coverage]
        pieces.append('<p>' + esc('; '.join(found) if found else 'Project attribution counts unknown for this source.') + '</p>')
        for row in source.get('sources', []):
            if 'last_received' in row:
                pieces.append(para('Last metric received', row['last_received']))
        issues = coverage.get('issues', [])
        if issues:
            pieces.append('<ul>' + ''.join('<li>' + esc(str(issue).replace('_', ' ')) + '</li>' for issue in issues) + '</ul>')
        pieces.append('</div>')
    pieces.extend(['</article></div><p class="muted">Unassigned usage remains in device observations. Attribution counts retain source units; they are not token totals.</p></section>',
        '<section id="projects" aria-labelledby="projects-heading"><h2 id="projects-heading">Projects and reported progress</h2>',
        '<p>Device totals and project views are non-additive. Project views may overlap; do not sum them or subtract them to estimate unassigned tokens.</p><div class="grid">'])
    for receipt in report['projects']:
        selection = receipt['selection']
        pieces.append('<article><h3>' + esc(selection.get('label', selection['project_id'])) + '</h3>')
        outcome = receipt.get('operator_outcome')
        if outcome:
            pieces.extend([para('Operator-reported outcome', outcome['statement']), para('Success criterion', outcome['success_criterion'])])
            progress = outcome.get('progress', {})
            pieces.append(para('Operator-reported progress', str(progress.get('complete', 'Unknown')) + ' of ' + str(progress.get('total', 'Unknown')) + ' checkpoints complete'))
            if outcome.get('checkpoints'):
                pieces.append('<ul>' + ''.join('<li><strong>' + esc(cp['text']) + '</strong>: ' + esc(cp.get('status', 'pending')) +
                    ' <span class="muted">(' + esc(cp['id']) + ')</span></li>' for cp in outcome['checkpoints']) + '</ul>')
            if outcome.get('history'):
                pieces.append('<details><summary>Operator-reported checkpoint history</summary><pre>' + esc(encoded(outcome['history']).decode('utf-8')) + '</pre></details>')
        else:
            pieces.append('<p>No operator-reported outcome is configured. Usage alone cannot establish progress.</p>')
        pieces.append('<p><strong>Observed project tokens:</strong> ' + amount(receipt['consumption']['tokens']) + '</p>')
        pieces.append(para('Project coverage', receipt['consumption'].get('coverage_status')))
        if receipt['comparisons']:
            for comparison in receipt['comparisons']:
                target = comparison['target']
                pieces.append('<p><strong>Advisory target:</strong> ' + amount(target.get('amount')) + ' ' + esc(target.get('unit')) +
                    ' · ' + esc(comparison['status']) + '</p><p>' + esc(comparison['reason']) + '</p>')
        else:
            pieces.append('<p>No advisory target configured.</p>')
        pieces.append('<p class="muted">Progress is operator-reported. Usage never advances a checkpoint or proves acceptance.</p></article>')
    pieces.extend(['</div></section><section id="providers" aria-labelledby="providers-heading"><h2 id="providers-heading">Providers and models</h2>',
        '<p>Device observations, separate from project views. Codex input includes cached input; Claude input, output, cache read and cache creation are disjoint classes. Volume is not a billing comparison.</p><div class="grid">'])
    for row in c['provider_models']:
        pieces.extend(['<article><h3>' + esc(row.get('client')) + ' · ' + esc(row.get('model')) + '</h3>',
            para('Provider', row.get('provider')), '<p><strong>Observed tokens:</strong> ' + amount(row.get('tokens')) + '</p>',
            '<details><summary>Service and launch details</summary>'])
        for label, value in [('Service', row.get('service_name', row.get('service'))), ('Service route', row.get('service_route')),
                ('Account', row.get('account')), ('Request category', row.get('query_source')), ('Entrypoint', row.get('entrypoint')),
                ('App version', row.get('app_version')), ('Service version', row.get('service_version'))]:
            pieces.append(para(label, value))
        pieces.append('</details></article>')
    if not c['provider_models']:
        pieces.append('<p>No provider/model observations available. Check the named source limitations.</p>')
    pieces.extend(['</div></section><section id="next" aria-labelledby="next-heading"><h2 id="next-heading">Choose your next step</h2>',
        '<p>These are instructions for your installed Cherry Meter plugin. Select the text and run the command in Claude Code. This static page runs nothing and saves nothing.</p>'])
    if config_path:
        pieces.append('<details><summary>Private config and snapshot identity</summary><dl><dt>Config</dt><dd>' + esc(config_path) +
            '</dd><dt>Report SHA256</dt><dd>' + esc(identity) + '</dd><dt>Saved JSON</dt><dd>' + esc(receipt_path) + '</dd></dl></details>')
    config_text = str(config_path) if config_path else 'Select your exact approved device config path.'
    report_text = '/cherry-meter:report\nConfig: ' + config_text + '\nWindow: ' + str(c['days']) + ' days'
    report_text += '\nThis snapshot ends on: ' + str(c.get('to_day')) + ' UTC. Choose the current date for later activity, or explicitly retain this historical end date.'
    pieces.extend(['<div class="grid"><article><h3>Refresh this snapshot</h3><pre><code>' + esc(report_text) + '</code></pre>',
        '<p>Review and approve the exact report plan. Open the returned new HTML and check its generated time and identity; this old report stays unchanged.</p></article>',
        '<article><h3>Report a checkpoint</h3><pre><code>' + esc('/cherry-meter:checkpoint\nConfig: ' + config_text) + '</code></pre>'])
    for receipt in report['projects']:
        for cp in (receipt.get('operator_outcome') or {}).get('checkpoints', []):
            pieces.append(para('Project / checkpoint', receipt['selection']['project_id'] + ' / ' + cp['id']))
    pieces.extend(['<p>Supply the status, actor and note yourself. After the approved update, generate a new report to see it. This snapshot cannot show a later checkpoint.</p></article>',
        '<article><h3>Investigate coverage</h3><pre><code>' + esc('/cherry-meter:doctor\nConfig: ' + config_text) + '</code></pre>',
        '<p>Diagnose the configured paths. Doctor does not read usage, probe or restart the collector, repair provider settings or discover new sources. Missing sources remain unknown; good observations remain usable.</p></article>',
        '<article><h3>Record your decision</h3><pre><code>' + esc('/cherry-meter:decision\nConfig: ' + config_text + '\nSaved report: ' +
            (str(receipt_path) if receipt_path else 'Select this saved JSON by its SHA256: ' + identity)) + '</code></pre>',
        '<p>Choose keep, change, investigate or hold, with your reason, next action, review trigger, actor and a new stable decision ID. Recording starts no work. Retrieve history with <code>/cherry-meter:decisions</code> and the same config.</p></article></div>',
        '<p class="notice">If a plan changes, preview it again. After cancellation or failure, inspect the approved destination before retrying: completed writes may remain.</p>'])
    if refresh_command:
        from .__main__ import command_text
        pieces.append('<details><summary>Independent native CLI refresh</summary><pre><code>' + esc(command_text(refresh_command)) + '</code></pre><p>Operator use only; plugin commands never execute a shell fallback.</p></details>')
    pieces.extend(['</section><details><summary>Source diagnostics and qualifications</summary>'])
    for source in report['sources']:
        pieces.append('<h3>' + esc(name(source)) + '</h3>')
        for row in source.get('sources', []):
            for key, label in [('tracking_start', 'Tracking start'), ('files', 'Files examined'), ('last_received', 'Last metric received'),
                               ('entrypoint_qualification', 'Client launch-path qualification')]:
                if key in row:
                    pieces.append(para(label, row[key]))
        lifecycle = source.get('collector_lifecycle')
        if lifecycle:
            pieces.append(para('Collector lifecycle', str(lifecycle.get('status', 'unknown')).replace('_', ' ')))
            if lifecycle.get('gaps'):
                pieces.append(para('Unobserved intervals between collector runs', len(lifecycle['gaps'])))
    pieces.extend('<p>' + esc(item) + '</p>' for item in report['qualifications'])
    pieces.append('</details><details><summary>Private measurement record</summary><pre>' +
        esc(encoded(report).decode('utf-8')) + '</pre></details></main><footer><p>Private saved evidence · Human judgment stays explicit.</p></footer></body></html>')
    return ''.join(pieces)
