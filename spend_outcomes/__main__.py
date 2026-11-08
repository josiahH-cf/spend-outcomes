import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import os
import re
import shlex
from pathlib import Path
import subprocess
import sys
from . import __version__
from .core import digest, encoded, immutable, inspect, read_export, save_record


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_bound(spec, config_dir):
    if not isinstance(spec,dict) or spec.get('permitted') is not True:
        raise ValueError('source requires explicit permitted=true binding')
    p=Path(spec['path']).expanduser()
    if not p.is_absolute():p=config_dir/p
    b=p.read_bytes()
    if not spec.get('sha256') or hashlib.sha256(b).hexdigest()!=spec['sha256']:
        raise ValueError('source digest mismatch')
    return json.loads(b.decode('utf-8'))


def refresh(config, config_dir, binding, days):
    spec=config['telemetry']
    if spec.get('permitted') is not True:raise ValueError('telemetry binding is not permitted')
    if 'export' in spec:
        value=load_bound(spec['export'],config_dir)
        if value.get('scope',{}).get('days') not in (None,days):raise ValueError('export period differs from selection')
        return value
    consumer=Path(spec['consumer']).expanduser().resolve()
    if consumer.name!='consumer.py' or not consumer.is_file():raise ValueError('expected configured Agent Telemetry consumer.py')
    scope={'days':days,'project_id':binding['telemetry_project_id'],'outcome_project_id':binding['project_id']}
    if 'reporting' in config:scope['reporting']=config['reporting']
    if 'sessions' in binding:scope['sessions']=binding['sessions']
    argv=[sys.executable,str(consumer),'--json','--scope',json.dumps(scope)]
    if spec.get('state_root'):argv+=['--state-root',str(Path(spec['state_root']).expanduser())]
    r=subprocess.run(argv,capture_output=True,text=True,timeout=180,check=True)
    return json.loads(r.stdout)


def render(receipt, *, receipt_path=None, command=None, refresh_command=None, state=None, project_label=None):
    """Human view of existing facts; complete receipt stays byte-for-byte available."""
    def value(v):
        if v is None:return 'Unknown'
        if v is True:return 'Yes'
        if v is False:return 'No'
        if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False)
        return str(v)

    def esc(v):return html.escape(value(v),quote=True)
    def paragraph(label,v):return '<p>'+html.escape(label)+': '+esc(v)+'</p>'
    def heading(title):return '<h2>'+title+'</h2>'
    def cmd(identity,argv):return '<pre id="'+identity+'">'+html.escape(shlex.join(list(map(str,argv))))+'</pre>'

    selection=receipt['selection'];c=receipt['consumption'];source=receipt['source']
    label=selection.get('label') or selection.get('name') or project_label or selection.get('telemetry_project_id') or selection.get('project_id')
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>Spend &amp; Outcomes — '+esc(label)+'</title>',
           '<style>body{font:17px/1.5 system-ui;max-width:60rem;margin:auto;padding:1.5rem;color:#172b36;background:#fafbf9}h1,h2,h3{line-height:1.2}h2{margin-top:1.8rem}p{margin:.5rem 0}article,details{border:1px solid #ccd6d8;border-radius:.5rem;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f2;padding:.8rem}summary{cursor:pointer;font-weight:600}a{color:#075d88}</style>',
           '<h1>'+esc(label)+' · Spend &amp; Outcomes</h1>',
           '<p>Period: '+esc(c.get('from'))+' to '+esc(c.get('to'))+' (inclusive UTC). Source as of: '+esc(source.get('as_of'))+'.</p>',
           '<p>Saved observations; opening this view makes no new measurement. Advisory only: reading and recording decisions start no work and change no Stop.</p>',
           heading('Observed consumption'),paragraph('Observed tokens',c.get('tokens')),
           paragraph('API-equivalent estimate (USD)',c.get('api_equivalent_cost_usd')),
           paragraph('Billed cash',c.get('billed_cash_usd')),paragraph('Subscription charge',c.get('subscription_charge_usd')),
           '<p>API-equivalent is a list-price estimate for known token classes, not cash billed to this Project or a subscription allocation.</p>',
           paragraph('Unpriced tokens',c.get('unpriced_tokens')),paragraph('Usage association',c.get('attribution')),
           heading('Results')]
    coverage=receipt.get('outcome_coverage',{})
    parts.append('<p>Distinct results: '+esc(coverage.get('returned'))+'; source/version observations: '+esc(coverage.get('observations_returned'))+'; result denominator: '+esc(coverage.get('denominator'))+'. Observations are non-additive.</p>')
    if not receipt['outcomes']:parts.append('<p>Delivery, installation, human acceptance and helpfulness: Unknown. No approved result observation available.</p>')
    for o in receipt['outcomes']:
        parts.extend(['<article><h3>'+esc(o.get('intended_result') or 'Result observation')+'</h3>',
                      paragraph('Delivered',o.get('delivered')),paragraph('Installed',o.get('installed')),
                      paragraph('Human acceptance',o.get('acceptance')),paragraph('Helpfulness / benefit',o.get('benefit')),
                      paragraph('Review verdict (source observation)',o.get('review_verdict')),
                      paragraph('Result association',o.get('association'))])
        # Artifact references stay inert text; arbitrary schemes never become links.
        if o.get('artifact'):parts.append(paragraph('Artifact',o['artifact']))
        if o.get('corrections'):
            for correction in o['corrections']:
                text=correction.get('text',correction) if isinstance(correction,dict) else correction
                parts.append(paragraph('Correction / contrary feedback',text))
            parts.append('<p>Correction reports retain their source provenance in details; they do not establish a causal link to this result.</p>')
        parts.extend([paragraph('Rework',o.get('rework')),'</article>'])
    if receipt.get('outcome_conflicts'):parts.append('<p>Outcome observations disagree across sources or versions. Inspect the complete differences below before claiming accepted quality.</p>')
    parts.append(heading('Declared targets'))
    if not receipt['comparisons']:parts.append('<p>No declared target. No numeric comparison is available.</p>')
    for comparison in receipt['comparisons']:
        target=comparison['target'];kind=target.get('kind')
        if kind=='allocation':
            description=value(target.get('percent'))+'% '+value(target.get('period'))+' subscription-token allocation for '+value(target.get('account'))+'; advisory, not cash spending'
        elif kind=='qualitative':description='Qualitative aim: '+value(target.get('aim'))
        else:description=value(target.get('amount'))+' '+value(target.get('unit'))+' ('+value(target.get('meaning'))+'); '+value(target.get('from'))+' to '+value(target.get('to'))
        parts.extend(['<article><h3>'+esc(description)+'</h3>',paragraph('Comparison',value(comparison.get('status')).capitalize()),
                      paragraph('Reason',comparison.get('reason'))])
        for key,title in [('actual','Same-basis actual'),('absolute_target','Absolute token target'),('excess','Excess'),('remainder','Remainder')]:
            if key in comparison:parts.append(paragraph(title,comparison[key]))
        parts.append('</article>')
    rec=receipt['recommendation']
    parts.extend([heading('Next move'),paragraph('Recommendation',rec.get('action')),paragraph('Next action',rec.get('next')),
                  paragraph('Missing evidence',rec.get('missing')),paragraph('Alternative',rec.get('alternative')),
                  '<p>A hold concerns the named claim. Usage and targets never gate proposals or execution. Earlier decisions are not attributed to this product.</p>',
                  heading('Read and record feedback')])
    if receipt_path is not None and command is not None:
        path=Path(receipt_path).resolve();state=Path(state).resolve()
        parts.extend(['<p>Read this exact saved receipt:</p>',cmd('read-command',[*command,'show',path]),
                      '<p>Optional feedback example: replace the example actor, decision, feedback and review trigger with your own facts before running. Choose a new decision ID for a new observation; the same ID is an immutable retry.</p>',
                      cmd('feedback-command',[*command,'record','--state',state,'--receipt',path,
                          '--id','decision-'+digest(receipt)[:16]+'-1','--actor','operator',
                          '--decision','keep','--feedback','Replace with your actual observation',
                          '--review-trigger','Replace with your next review trigger'])])
        if refresh_command:
            parts.extend(['<p>Explicitly read the configured sources again (opening this saved HTML does not refresh them):</p>',cmd('refresh-command',refresh_command)])
    else:parts.append('<p>Command context unavailable in this rendering. Use the inspect command’s saved receipt path with the documented show and record interface.</p>')
    parts.append(heading('Source qualifications'))
    parts.extend([paragraph('Source status',source.get('status')),paragraph('Period basis',c.get('basis')),
                  paragraph('Project association',selection.get('association')),
                  paragraph('Source conflicts',source.get('conflict_summary',{}).get('reason')),
                  paragraph('Prior/manual comparison',receipt.get('prior_comparison',{}).get('status')),
                  paragraph('Comparison qualification',receipt.get('prior_comparison',{}).get('reason'))])
    for limitation in receipt.get('limitations',[]):parts.append('<p>'+esc(limitation)+'</p>')
    parts.append('<p>Shared, unassigned, native/session, Project, accounting and executor views are non-additive; unknown coverage is not zero. Complete coverage, source clocks, pricing, capacity, checks and versions remain below. Machine delivery/checks supply no human acceptance or benefit.</p>')
    data=encoded(receipt)
    download='data:application/json;base64,'+base64.b64encode(data).decode('ascii')
    parts.extend(['<details><summary>Complete machine JSON and evidence (private)</summary>',
                  '<p>This complete saved receipt contains source identities and all evidence. Keep it private.</p>',
                  '<a download="'+digest(receipt)+'.json" href="'+download+'">Download complete receipt JSON</a>',
                  '<pre id="machine-json">'+html.escape(data.decode('utf-8'))+'</pre></details></html>'])
    return ''.join(parts)


def invocation():
    """Use the executing archive/wrapper, or an absolute source module binding."""
    if sys.argv[0]!='-c' and Path(sys.argv[0]).resolve()!=Path(__file__).resolve():
        return [sys.executable,str(Path(sys.argv[0]).resolve())]
    root=str(Path(__file__).resolve().parents[1])
    return [sys.executable,'-c','import sys; sys.path.insert(0,'+repr(root)+'); from spend_outcomes.__main__ import main; raise SystemExit(main())']


def initialize(args):
    """Create an explicit access declaration without reading a source."""
    for name in ('project', 'project_id', 'telemetry_project_id'):
        if not getattr(args,name).strip():raise ValueError(name+' must not be blank')
    config_path=args.config.expanduser().absolute()
    telemetry={'permitted':True}
    if args.telemetry_export is not None:
        if not args.sha256 or not re.fullmatch('[0-9a-f]{64}',args.sha256):
            raise ValueError('--telemetry-export requires --sha256 (64 lowercase hex characters)')
        if args.state_root is not None:raise ValueError('--state-root requires --consumer')
        telemetry['export']={'permitted':True,'path':str(args.telemetry_export.expanduser().absolute()),'sha256':args.sha256}
    else:
        if args.sha256:raise ValueError('--sha256 requires --telemetry-export')
        telemetry['consumer']=str(args.consumer.expanduser().absolute())
        if args.state_root is not None:telemetry['state_root']=str(args.state_root.expanduser().absolute())
    config={'telemetry':telemetry,'projects':{args.project:{'permitted':True,'project_id':args.project_id,
            'telemetry_project_id':args.telemetry_project_id,'association':args.association}},'targets':{}}
    inspect_argv=[*invocation(),'inspect','--config',str(config_path),'--project',args.project,
                  '--state',str(args.state.expanduser().absolute()),'--html']
    # Exclusive creation refuses regular files and symlinks, including dangling ones.
    # Set private mode at creation, independent of umask; do not create parents.
    with os.fdopen(os.open(config_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:
        f.write(encoded(config));f.flush();os.fsync(f.fileno())
    return {'config':str(config_path),'inspect_argv':inspect_argv,
            'next_steps':['Config created; no sources read. No targets or outcomes supplied.',
                          'Run the inspect command to read only your explicitly permitted source: '+shlex.join(inspect_argv),
                          'Keep config and generated receipts private. Add only your actual targets and approved outcome bindings.'],
            'execution_effects':[]}


def share(record):
    if record.get('contract')=='pv-decision-v1':
        return {k:record.get(k) for k in ('contract','id','actor','receipt','decision','feedback','next_action','review_trigger','created_at','provenance','source_versions','supersedes')}
    raise ValueError('only attributed decision records can be exported; receipts remain private')


def main(argv=None):
    p=argparse.ArgumentParser(description='Local advisory consumption, results and decisions')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('init',help='Create a private config from explicit source and Project bindings; never overwrite',
                     description='Create only the selected config. Declares permission to read the selected source on a later inspect; init reads no sources. Parent directory must exist.')
    i.add_argument('--config',type=Path,required=True)
    i.add_argument('--project',required=True,help='Your local workflow selection key')
    i.add_argument('--project-id',required=True,help='Canonical beneficiary Project identity')
    i.add_argument('--telemetry-project-id',required=True,help='Producer Project ID or code')
    i.add_argument('--association',choices=['exact','owner-attested','correlated','unattributed'],required=True,
                   help='Your supported association basis; matching names alone is not exact')
    source=i.add_mutually_exclusive_group(required=True)
    source.add_argument('--consumer',type=Path,help='Your permitted Agent Telemetry consumer.py')
    source.add_argument('--telemetry-export',type=Path,help='Your permitted complete telemetry-consumer-v1 export')
    i.add_argument('--sha256',help='Exact export bytes digest, required for --telemetry-export')
    i.add_argument('--state-root',type=Path,help='Optional explicit producer state root for --consumer')
    i.add_argument('--state',type=Path,required=True,help='Product receipt directory for the printed inspect command; not created by init')
    s=sub.add_parser('inspect');s.add_argument('--config',type=Path,required=True);s.add_argument('--project',required=True)
    s.add_argument('--days',choices=['7','30','90','all'],default='7');s.add_argument('--state',type=Path,required=True)
    s.add_argument('--baseline',type=Path);s.add_argument('--html',action='store_true')
    d=sub.add_parser('record');d.add_argument('--state',type=Path,required=True);d.add_argument('--receipt',type=Path,required=True)
    d.add_argument('--id',required=True);d.add_argument('--actor',required=True);d.add_argument('--decision',choices=['investigate','change','hold','keep'],required=True)
    d.add_argument('--feedback');d.add_argument('--next-action');d.add_argument('--review-trigger');d.add_argument('--supersedes')
    for command in ['export','import']:
        q=sub.add_parser(command);q.add_argument('--input',type=Path,required=True)
        q.add_argument('--output' if command=='export' else '--state',type=Path,required=True)
    q=sub.add_parser('show');q.add_argument('path',type=Path)
    args=p.parse_args(argv)
    try:
        if args.cmd=='init':answer=initialize(args)
        elif args.cmd=='inspect':
            config=read_export(args.config);binding=dict(config['projects'][args.project]);days='all' if args.days=='all' else int(args.days)
            binding['days']=days
            if binding.get('permitted') is not True:raise ValueError('project binding not permitted')
            unavailable=[]
            try:telemetry=refresh(config,args.config.resolve().parent,binding,days)
            except (OSError,subprocess.SubprocessError) as e:
                telemetry={'contract':'telemetry-consumer-v1','producer':'agent-telemetry','status':'unavailable','coverage':{'missing':[{'source':'configured-consumer','status':type(e).__name__}]}}
            outcomes=None
            if config.get('outcomes'):
                try:outcomes=load_bound(config['outcomes'],args.config.resolve().parent)
                except OSError as e:unavailable.append({'source':'outcomes','status':type(e).__name__})
            receipt=inspect(telemetry,binding,config.get('targets',{}).get(args.project,[]),outcomes=outcomes,
                            baseline=read_export(args.baseline) if args.baseline else None)
            receipt['unavailable_sources']=unavailable
            receipt['source_versions']={'telemetry':digest(telemetry),'outcomes':digest(outcomes) if outcomes else None}
            receipt['product_version']=__version__
            receipt_id=digest(receipt)
            path=immutable(args.state/'receipts'/(receipt_id+'.json'),receipt)
            if args.html:
                hp=path.with_suffix('.html')
                command=invocation()
                refresh_command=[*command,'inspect','--config',str(args.config.resolve()),'--project',args.project,
                                 '--days',args.days,'--state',str(args.state.resolve()),'--html']
                if args.baseline:refresh_command+=['--baseline',str(args.baseline.resolve())]
                content=render(receipt,receipt_path=path,command=command,refresh_command=refresh_command,state=args.state,
                               project_label=args.project[:1].upper()+args.project[1:]).encode('utf-8')
                try:
                    with hp.open('xb') as f:os.chmod(hp,0o600);f.write(content)
                except FileExistsError:
                    if hp.read_bytes()!=content:raise ValueError('HTML receipt conflict')
            answer={'receipt':str(path),'sha256':receipt_id,'html':str(path.with_suffix('.html')) if args.html else None,'view':receipt}
        elif args.cmd=='record':
            receipt=read_export(args.receipt)
            if receipt.get('contract')!='pv-receipt-v1':raise ValueError('invalid receipt')
            record={'contract':'pv-decision-v1','id':args.id,'actor':args.actor,'receipt':digest(receipt),'source_versions':receipt.get('source_versions'),
                    'decision':args.decision,'feedback':args.feedback,'next_action':args.next_action,'review_trigger':args.review_trigger,
                    'supersedes':args.supersedes,'provenance':'operator-reported'}
            if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',args.id):raise ValueError('invalid decision identity')
            # Stable retry bytes: timestamp belongs to the first save only.
            existing=args.state/'decisions'/(args.id+'.json')
            if existing.exists():
                old=read_export(existing);record['created_at']=old['created_at']
            else:record['created_at']=utc()
            answer={'record':str(save_record(args.state/'decisions',record)),'execution_effects':[]}
        elif args.cmd=='export':
            record=read_export(args.input);public=share(record)
            # Refuse stripping unknown fields: original identity and exact content must survive.
            if public!=record:raise ValueError('unsupported decision fields; export must preserve exact record')
            answer={'export':str(immutable(args.output,public)),'identity':record['id']}
        elif args.cmd=='import':
            record=read_export(args.input)
            if share(record)!=record:raise ValueError('unsupported imported decision fields')
            answer={'record':str(save_record(args.state/'decisions',record)),'execution_effects':[]}
        else:answer=read_export(args.path)
        print(json.dumps(answer,ensure_ascii=False,sort_keys=True,allow_nan=False));return 0
    except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as e:
        print(json.dumps({'status':'held','reason':str(e),'execution_effects':[]}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
