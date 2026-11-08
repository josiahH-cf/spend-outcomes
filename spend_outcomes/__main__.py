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
import tempfile
from . import __version__
from .codex import observe_codex
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


def refresh(config, config_dir, binding, days, through=None):
    if 'sources' in config:
        sources=config.get('sources')
        if not isinstance(sources,list) or not sources:raise ValueError('at least one explicit source binding is required')
        codex=[source for source in sources if source.get('kind')=='codex']
        if len(sources)!=1 or len(codex)!=1 or codex[0].get('permitted') is not True:
            raise ValueError('one permitted Codex source binding is required; mixed live sources are unsupported')
        if days=='all':raise ValueError('direct Codex observations require a bounded UTC day window')
        roots=[]
        for value in codex[0].get('roots',[]):
            path=Path(value).expanduser();roots.append(str(path if path.is_absolute() else config_dir/path))
        return observe_codex(roots,config['projects'],binding['local_project_key'],days,through)
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
    daily=c.get('daily') or []
    parts.append(heading('Daily observed usage'))
    if not daily:parts.append('<p>No dated observed usage events are available for this window.</p>')
    else:
        peak=max((item.get('tokens') or 0 for item in daily),default=0) or 1
        parts.append('<div class="daily-usage">')
        for item in daily:
            width=min(100,round(100*(item.get('tokens') or 0)/peak))
            parts.append('<p>'+esc(item.get('date'))+': '+esc(item.get('tokens'))+
                         ' tokens <span aria-hidden="true" style="display:inline-block;background:#3b7f77;height:.7rem;width:'+str(width)+'%"></span></p>')
        parts.append('</div>')
    parts.append(heading('Provider and model breakdown'))
    models=c.get('provider_models') or []
    if not models:parts.append('<p>No provider/model observations are available.</p>')
    for item in models:
        parts.append('<p>'+esc(item.get('provider'))+' · '+esc(item.get('model'))+': '+esc(item.get('tokens'))+' observed tokens</p>')
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
    parts.append(heading('Operator-reported outcome'))
    outcome=receipt.get('operator_outcome')
    if not outcome:parts.append('<p>No local outcome has been defined. Usage never supplies an outcome status.</p>')
    else:
        parts.extend([paragraph('Outcome',outcome.get('statement')),paragraph('Success criterion',outcome.get('success_criterion')),
                      paragraph('Progress',str(outcome.get('progress',{}).get('complete',0))+' of '+str(outcome.get('progress',{}).get('total',0))+' checkpoints complete'),
                      '<p>Progress is operator-reported. Observed usage does not advance it.</p>'])
        for checkpoint in outcome.get('checkpoints',[]):
            parts.extend(['<article><h3>'+esc(checkpoint.get('text'))+'</h3>',paragraph('Checkpoint status',checkpoint.get('status')),
                          paragraph('Reported by',checkpoint.get('actor')),paragraph('Reported at',checkpoint.get('reported_at')),
                          paragraph('Operator note',checkpoint.get('note')),'</article>'])
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
    if not isinstance(args.project,str) or not args.project.strip():raise ValueError('project must not be blank')
    config_path=args.config.expanduser().absolute()
    direct=bool(args.codex_root);legacy=args.telemetry_export is not None or args.consumer is not None
    if direct==legacy:raise ValueError('choose direct --codex-root or one compatible Agent Telemetry source')
    if direct:
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',args.project):raise ValueError('direct local project key is invalid')
        if args.project_id or args.telemetry_project_id or args.association:
            raise ValueError('direct Codex setup uses a local project key, not compatible-export identities')
        if args.sha256 or args.state_root:raise ValueError('--sha256 and --state-root apply only to compatible sources')
        if args.outcome is None and (args.success_criterion is not None or args.checkpoints):
            raise ValueError('--success-criterion and --checkpoint require --outcome')
        if args.workspace is None:raise ValueError('direct Codex setup requires --workspace')
        workspace=args.workspace.expanduser().absolute()
        if not workspace.is_dir():raise ValueError('workspace must be an existing directory: '+str(workspace))
        additional=[path.expanduser().absolute() for path in (args.additional_workspace or [])]
        missing=[str(path) for path in additional if not path.is_dir()]
        if missing:raise ValueError('additional workspace must be an existing directory: '+', '.join(missing))
        project={'permitted':True,'workspace':str(workspace),'label':args.name or args.project,
                 'additional_workspaces':[str(path) for path in additional]}
        config={'sources':[{'id':'codex-local','kind':'codex','permitted':True,
                            'roots':[str(path.expanduser().absolute()) for path in args.codex_root]}],
                'projects':{args.project:project},'targets':{}}
        if args.target_tokens is not None:
            if args.target_tokens<=0:raise ValueError('--target-tokens must be positive')
            config['targets'][args.project]=[{'kind':'numeric','unit':'tokens','meaning':'observed',
                                              'amount':args.target_tokens,'window':'rolling-7-days'}]
        if args.outcome is not None:
            if not args.outcome.strip() or not args.success_criterion or not args.success_criterion.strip():
                raise ValueError('--outcome requires a nonblank --success-criterion')
            checkpoints=[]
            for value in args.checkpoints or []:
                if '=' not in value:raise ValueError('--checkpoint must use ID=description')
                identity,text=value.split('=',1)
                if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',identity) or not text.strip():
                    raise ValueError('invalid checkpoint ID or description')
                checkpoints.append({'id':identity,'text':text.strip(),'status':'pending','provenance':'operator-reported'})
            config['outcome']={'statement':args.outcome.strip(),'success_criterion':args.success_criterion.strip(),
                               'provenance':'operator-reported','checkpoints':checkpoints,'history':[]}
    else:
        if any(value is not None for value in (args.workspace,args.name,args.target_tokens,args.outcome,args.success_criterion)) or args.additional_workspace or args.checkpoints:
            raise ValueError('direct setup options cannot be combined with a compatible source')
        for name in ('project_id','telemetry_project_id','association'):
            value=getattr(args,name)
            if not isinstance(value,str) or not value.strip():raise ValueError(name+' must not be blank')
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
            'next_steps':['Config created; no sources read.',
                          'Run the inspect command to read only your explicitly permitted source: '+shlex.join(inspect_argv),
                          'Keep config and generated receipts private. Targets are advisory; checkpoint updates are operator-reported.'],
            'execution_effects':[]}


def replace_config(path, original, config):
    data=encoded(config)
    descriptor,temporary=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as handle:
            os.fchmod(handle.fileno(),0o600);handle.write(data);handle.flush();os.fsync(handle.fileno())
        if path.read_bytes()!=original:raise ValueError('config changed during local update')
        os.replace(temporary,path)
    except Exception:
        try:os.unlink(temporary)
        except OSError:pass
        raise


def read_mutable_config(raw_path):
    path=raw_path.expanduser().absolute()
    if path.is_symlink():raise ValueError('refusing to update a symlinked config')
    original=path.read_bytes()
    return path,original,json.loads(original.decode('utf-8'))


def update_checkpoint(args):
    """Atomically apply one explicit local operator report; never read usage."""
    path,original,config=read_mutable_config(args.config)
    if not args.actor.strip():raise ValueError('actor must not be blank')
    if args.project not in config.get('projects',{}):raise ValueError('unknown project selection')
    outcome=config.get('outcome')
    if not isinstance(outcome,dict):raise ValueError('no local outcome is configured')
    checkpoints=outcome.get('checkpoints',[])
    if not isinstance(checkpoints,list):raise ValueError('configured checkpoints must be a list')
    matches=[item for item in checkpoints if isinstance(item,dict) and item.get('id')==args.id]
    if len(matches)!=1:raise ValueError('checkpoint identity not found or ambiguous')
    checkpoint=matches[0];reported_at=utc()
    update={'id':args.id,'status':args.status,'actor':args.actor,'note':args.note,
            'reported_at':reported_at,'provenance':'operator-reported'}
    checkpoint.update(update);outcome.setdefault('history',[]).append(dict(update))
    replace_config(path,original,config)
    return {'config':str(path),'checkpoint':update,'execution_effects':[]}


def update_target(args):
    path,original,config=read_mutable_config(args.config)
    if not args.actor.strip():raise ValueError('actor must not be blank')
    if args.project not in config.get('projects',{}):raise ValueError('unknown project selection')
    if args.tokens<=0:raise ValueError('--tokens must be positive')
    previous=config.setdefault('targets',{}).get(args.project,[])
    target={'kind':'numeric','unit':'tokens','meaning':'observed','amount':args.tokens,'window':'rolling-7-days'}
    config['targets'][args.project]=[target]
    update={'project':args.project,'previous':previous,'target':target,'actor':args.actor,'note':args.note,
            'reported_at':utc(),'provenance':'operator-reported'}
    config.setdefault('target_history',[]).append(update)
    replace_config(path,original,config)
    return {'config':str(path),'target':target,'execution_effects':[]}


def update_outcome(args):
    path,original,config=read_mutable_config(args.config)
    if not args.actor.strip():raise ValueError('actor must not be blank')
    if args.project not in config.get('projects',{}):raise ValueError('unknown project selection')
    if not args.statement.strip() or not args.success_criterion.strip():raise ValueError('outcome values must not be blank')
    previous=config.get('outcome') if isinstance(config.get('outcome'),dict) else {}
    checkpoints=previous.get('checkpoints',[]);history=previous.get('history',[])
    if not isinstance(checkpoints,list) or not isinstance(history,list):raise ValueError('configured outcome history is malformed')
    outcome={'statement':args.statement.strip(),'success_criterion':args.success_criterion.strip(),
             'provenance':'operator-reported','checkpoints':checkpoints,'history':history}
    outcome['history'].append({'kind':'outcome-definition','statement':outcome['statement'],
        'success_criterion':outcome['success_criterion'],'actor':args.actor,'note':args.note,
        'reported_at':utc(),'provenance':'operator-reported'})
    config['outcome']=outcome;replace_config(path,original,config)
    return {'config':str(path),'outcome':{'statement':outcome['statement'],'success_criterion':outcome['success_criterion']},
            'execution_effects':[]}


def create_demo(args):
    """Create a clearly labelled synthetic first report without reading user logs."""
    root=args.root.expanduser().absolute()
    root.mkdir(parents=True,mode=0o700)
    workspace=root/'synthetic-workspace';logs=root/'synthetic-codex';state=root/'private-state'
    workspace.mkdir();logs.mkdir()
    now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    session='synthetic-spend-outcomes-demo'
    rows=[
        {'timestamp':now.isoformat(),'type':'session_meta','payload':{'id':session,'cwd':str(workspace)}},
        {'timestamp':now.isoformat(),'type':'turn_context','payload':{'model':'synthetic-demo-model'}},
        {'timestamp':now.isoformat(),'type':'event_msg','payload':{'type':'token_count','info':{
            'total_token_usage':{'input_tokens':600,'cached_input_tokens':100,'output_tokens':100,
                                 'reasoning_output_tokens':25,'total_tokens':700},
            'last_token_usage':{'input_tokens':600,'cached_input_tokens':100,'output_tokens':100,
                                'reasoning_output_tokens':25,'total_tokens':700}}}},
    ]
    log=logs/'synthetic-session.jsonl'
    log.write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in rows),encoding='utf-8')
    config_path=root/'config.json'
    config={'sources':[{'id':'synthetic-codex','kind':'codex','permitted':True,'roots':[str(logs)]}],
            'projects':{'demo':{'permitted':True,'workspace':str(workspace),'label':'Synthetic demo'}},
            'targets':{'demo':[{'kind':'numeric','unit':'tokens','meaning':'observed','amount':1000,'window':'rolling-7-days'}]},
            'outcome':{'statement':'Understand one project’s observed Codex usage',
                       'success_criterion':'Open a saved report and review its qualifications',
                       'provenance':'operator-reported','history':[],
                       'checkpoints':[{'id':'review-report','text':'Review the synthetic report','status':'pending',
                                       'provenance':'operator-reported'}]}}
    with os.fdopen(os.open(config_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as handle:
        handle.write(encoded(config));handle.flush();os.fsync(handle.fileno())
    binding=dict(config['projects']['demo']);binding.update({'local_project_key':'demo','project_id':'demo',
        'telemetry_project_id':'demo','association':'exact','days':7})
    observed=observe_codex([logs],config['projects'],'demo',7,now.date().isoformat())
    receipt=inspect(observed,binding,config['targets']['demo'],local_outcome=config['outcome'])
    receipt['unavailable_sources']=[];receipt['source_versions']={'codex':digest(observed),'outcomes':None}
    receipt['product_version']=__version__;receipt_id=digest(receipt)
    receipt_path=immutable(state/'receipts'/(receipt_id+'.json'),receipt)
    command=invocation();html_path=receipt_path.with_suffix('.html')
    refresh_command=[*command,'inspect','--config',str(config_path),'--project','demo','--state',str(state),'--html']
    content=render(receipt,receipt_path=receipt_path,command=command,refresh_command=refresh_command,
                   state=state,project_label='Synthetic demo').encode('utf-8')
    with html_path.open('xb') as handle:os.chmod(html_path,0o600);handle.write(content)
    checkpoint=[*command,'checkpoint','--config',str(config_path),'--project','demo','--id','review-report',
                '--status','complete','--actor','operator','--note','Reviewed the synthetic report']
    return {'demo':True,'config':str(config_path),'receipt':str(receipt_path),'html':str(html_path),
            'checkpoint_argv':checkpoint,'execution_effects':[]}


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
    i.add_argument('--name',help='Human-readable local project name')
    i.add_argument('--workspace',type=Path,help='Confirmed project workspace for direct Codex measurement')
    i.add_argument('--additional-workspace',type=Path,action='append',help='Explicit additional checkout for this project')
    i.add_argument('--project-id',help='Canonical beneficiary Project identity for a compatible export')
    i.add_argument('--telemetry-project-id',help='Producer Project ID or code for a compatible export')
    i.add_argument('--association',choices=['exact','owner-attested','correlated','unattributed'],
                   help='Your supported association basis; matching names alone is not exact')
    source=i.add_mutually_exclusive_group()
    source.add_argument('--consumer',type=Path,help='Your permitted Agent Telemetry consumer.py')
    source.add_argument('--telemetry-export',type=Path,help='Your permitted complete telemetry-consumer-v1 export')
    source.add_argument('--codex-root',type=Path,action='append',help='Explicit Codex JSONL root; repeat for another approved store')
    i.add_argument('--sha256',help='Exact export bytes digest, required for --telemetry-export')
    i.add_argument('--state-root',type=Path,help='Optional explicit producer state root for --consumer')
    i.add_argument('--state',type=Path,required=True,help='Product receipt directory for the printed inspect command; not created by init')
    i.add_argument('--target-tokens',type=int,help='Advisory observed-token target for each rolling seven-day UTC window')
    i.add_argument('--outcome',help='Plain-language intended outcome')
    i.add_argument('--success-criterion',help='Operator-defined evidence of success')
    i.add_argument('--checkpoint',dest='checkpoints',action='append',help='Optional ID=description checkpoint')
    s=sub.add_parser('inspect');s.add_argument('--config',type=Path,required=True);s.add_argument('--project',required=True)
    s.add_argument('--days',choices=['7','30','90','all'],default='7');s.add_argument('--state',type=Path,required=True)
    s.add_argument('--through',help='Inclusive UTC end date (YYYY-MM-DD); defaults to today')
    s.add_argument('--baseline',type=Path);s.add_argument('--html',action='store_true')
    c=sub.add_parser('checkpoint',help='Record one explicit operator-reported checkpoint update')
    c.add_argument('--config',type=Path,required=True);c.add_argument('--project',required=True);c.add_argument('--id',required=True)
    c.add_argument('--status',choices=['pending','in-progress','complete','blocked'],required=True)
    c.add_argument('--actor',required=True);c.add_argument('--note')
    target=sub.add_parser('target',help='Update the advisory rolling seven-day token target')
    target.add_argument('--config',type=Path,required=True);target.add_argument('--project',required=True)
    target.add_argument('--tokens',type=int,required=True);target.add_argument('--actor',required=True);target.add_argument('--note')
    outcome=sub.add_parser('outcome',help='Update the operator-reported local outcome definition')
    outcome.add_argument('--config',type=Path,required=True);outcome.add_argument('--project',required=True)
    outcome.add_argument('--statement',required=True);outcome.add_argument('--success-criterion',required=True)
    outcome.add_argument('--actor',required=True);outcome.add_argument('--note')
    demo=sub.add_parser('demo',help='Create a synthetic local report without reading user logs')
    demo.add_argument('--root',type=Path,required=True,help='New directory to create; existing paths are refused')
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
        elif args.cmd=='checkpoint':answer=update_checkpoint(args)
        elif args.cmd=='target':answer=update_target(args)
        elif args.cmd=='outcome':answer=update_outcome(args)
        elif args.cmd=='demo':answer=create_demo(args)
        elif args.cmd=='inspect':
            config=read_export(args.config);binding=dict(config['projects'][args.project]);days='all' if args.days=='all' else int(args.days)
            if 'sources' in config:
                binding.update({'local_project_key':args.project,'project_id':args.project,
                                'telemetry_project_id':args.project,'association':'exact'})
            binding['days']=days
            if binding.get('permitted') is not True:raise ValueError('project binding not permitted')
            unavailable=[]
            try:telemetry=refresh(config,args.config.resolve().parent,binding,days,args.through)
            except (OSError,subprocess.SubprocessError) as e:
                telemetry={'contract':'telemetry-consumer-v1','producer':'agent-telemetry','status':'unavailable','coverage':{'missing':[{'source':'configured-consumer','status':type(e).__name__}]}}
            outcomes=None
            if config.get('outcomes'):
                try:outcomes=load_bound(config['outcomes'],args.config.resolve().parent)
                except OSError as e:unavailable.append({'source':'outcomes','status':type(e).__name__})
            receipt=inspect(telemetry,binding,config.get('targets',{}).get(args.project,[]),outcomes=outcomes,
                            baseline=read_export(args.baseline) if args.baseline else None,local_outcome=config.get('outcome'))
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
                if args.through:refresh_command+=['--through',args.through]
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
