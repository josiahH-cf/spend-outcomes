"""Pure qualification and immutable local decision records; no execution authority."""
import datetime as dt
import copy
import hashlib
import json
import math
import re
from pathlib import Path


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read_export(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def immutable(path, value):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data=encoded(value)
    try:
        with path.open('xb') as f:
            path.chmod(0o600);f.write(data);f.flush()
            import os
            os.fsync(f.fileno())
    except FileExistsError:
        if path.read_bytes()!=data:
            raise ValueError('immutable identity conflict: '+path.name)
    return path


def save_record(root, record):
    if record.get('contract')!='pv-decision-v1' or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',record.get('id','')):
        raise ValueError('invalid decision contract or identity')
    for key in ('actor','receipt','decision','provenance'):
        if not record.get(key):raise ValueError('decision requires '+key)
    if record['provenance']!='operator-reported':raise ValueError('decision provenance must remain operator-reported')
    if record['decision'] not in ('investigate','change','hold','keep'):raise ValueError('invalid decision')
    return immutable(Path(root)/(record['id']+'.json'),record)


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0


def conflict_summary(raw):
    """Qualify coverage without treating a metadata container as a conflict.

    Producer totals cover all conflicts; returned items can be bounded. Keep
    malformed/absent coverage unknown and preserve positive evidence even when
    its total is absent or inconsistent. Raw metadata stays beside this summary.
    """
    if isinstance(raw,list):
        total=len(raw);returned=total;complete=True
    elif isinstance(raw,dict):
        count=raw.get('total');items=raw.get('items')
        total=count if type(count) is int and count>=0 else None
        returned=len(items) if isinstance(items,list) else None
        complete=total is not None and returned is not None and total==returned
    else:
        total=None;returned=None;complete=False
    positive=(total is not None and total>0) or (returned is not None and returned>0)
    status='positive' if positive else ('zero' if complete and total==0 else 'unknown')
    if status=='positive':
        reason='Producer reports source conflicts; inspect source.conflicts items and their source/detail metadata before claims depending on conflict-free coverage.'
        if total is None or returned is None or returned>total:
            reason+=' Conflict coverage is incomplete or inconsistent; the full count/list needs owner qualification.'
        elif returned<total:
            reason+=' Returned items are bounded; they are not the full conflict count.'
    elif status=='unknown':
        reason='Source conflict coverage is unknown: a nonnegative integer total with an items list, or an explicit conflict list, is required.'
    else:
        reason='Source explicitly reports zero conflicts.'
    return {'status':status,'total':total,'returned':returned,'complete':complete,'reason':reason}


def comparison(target, consumption, binding):
    kind=target.get('kind');r={'target':target,'actual':None,'excess':None,'remainder':None,'status':'unknown'}
    if kind=='qualitative':return {**r,'status':'qualitative','reason':'A stated aim has no numeric denominator.'}
    if kind=='allocation':
        if not number(target.get('percent')) or target['percent']>100:raise ValueError('invalid allocation')
        return {**r,'absolute_target':None,'reason':'A qualified account token denominator and same-account attributed usage are required; remaining percentages and subscription prices supply neither.'}
    if kind!='numeric' or not number(target.get('amount')):raise ValueError('invalid target')
    if consumption.get('coverage_status') not in (None,'complete'):
        return {**r,'reason':'Observed source coverage is partial or unavailable; a full-window comparison is not qualified.'}
    same=all(target.get(k)==consumption.get(k) and target.get(k) is not None for k in ('from','to'))
    same=same and target.get('project_id',binding['project_id'])==binding['project_id']
    if not same:return {**r,'reason':'Target scope or UTC period differs or is unknown.'}
    if target.get('unit')=='tokens' and target.get('meaning')=='observed':actual=consumption.get('tokens')
    elif target.get('unit')=='USD' and target.get('meaning')=='api-equivalent':
        actual=consumption.get('api_equivalent_cost_usd') if consumption.get('unpriced_tokens')==0 else None
    elif target.get('unit')=='USD' and target.get('meaning')=='billed-cash':actual=None
    else:raise ValueError('unsupported unit/meaning')
    if actual is None:return {**r,'reason':'Same-basis total is unavailable: billed project cash is unobserved; estimates exclude unknown pricing.'}
    return {**r,'status':'comparable','actual':actual,'excess':max(0,actual-target['amount']),
            'remainder':max(0,target['amount']-actual),'reason':'Same selected scope and inclusive UTC period; advisory only.'}


OUTCOME_FIELDS=('id','version','intended_result','artifact','revision','checks','delivered','installed','acceptance','benefit','corrections','rework','association','source_id','observed_at','denominator','acceptance_basis','review_verdict')


def observation_time(observation):
    value=observation.get('observed_at')
    if not isinstance(value,str):return None
    try:
        stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return stamp.astimezone(dt.timezone.utc) if stamp.tzinfo is not None else None
    except ValueError:
        return None


def operator_outcome(value):
    if value is None:return None
    if not isinstance(value,dict) or not isinstance(value.get('statement'),str) or not value['statement'].strip():
        raise ValueError('operator outcome requires a statement')
    if not isinstance(value.get('success_criterion'),str) or not value['success_criterion'].strip():
        raise ValueError('operator outcome requires a success criterion')
    checkpoints=value.get('checkpoints',[])
    if not isinstance(checkpoints,list):raise ValueError('operator outcome checkpoints must be a list')
    seen=set()
    for checkpoint in checkpoints:
        if not isinstance(checkpoint,dict) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',checkpoint.get('id','')):
            raise ValueError('invalid checkpoint identity')
        if checkpoint['id'] in seen:raise ValueError('duplicate checkpoint identity')
        seen.add(checkpoint['id'])
        if not isinstance(checkpoint.get('text'),str) or not checkpoint['text'].strip():raise ValueError('checkpoint text required')
        if checkpoint.get('status','pending') not in ('pending','in-progress','complete','blocked'):
            raise ValueError('invalid checkpoint status')
        if checkpoint.get('provenance','operator-reported')!='operator-reported':
            raise ValueError('checkpoint provenance must remain operator-reported')
    result=copy.deepcopy(value)
    result['provenance']='operator-reported'
    result['progress']={'complete':sum(item.get('status','pending')=='complete' for item in checkpoints),
                        'total':len(checkpoints),'basis':'operator-reported; usage does not advance checkpoints'}
    return result


def inspect(telemetry, binding, targets, *, outcomes=None, baseline=None, local_outcome=None):
    supported=((telemetry.get('contract')=='telemetry-consumer-v1' and telemetry.get('producer')=='agent-telemetry') or
               (telemetry.get('contract')=='spend-outcomes-observation-v1' and telemetry.get('producer')=='spend-outcomes-codex'))
    if not supported:raise ValueError('only a direct Codex observation or supported telemetry-consumer-v1 export is permitted')
    if binding.get('association') not in ('exact','owner-attested','correlated','unattributed'):
        raise ValueError('explicit project association required')
    rows=[p for p in telemetry.get('projects',[]) if binding.get('telemetry_project_id') in (p.get('project_id'),p.get('project_code'))]
    if len(rows)>1:raise ValueError('ambiguous telemetry project binding')
    row=rows[0] if rows else {};period=row.get('period') or {}
    if period and period.get('days')!=binding.get('days'):
        raise ValueError('source project period differs from selected days')
    for key in ('tokens','unpriced_tokens','api_equivalent_cost_usd'):
        if period.get(key) is not None and not number(period[key]):raise ValueError('invalid consumption '+key)
    if period.get('unpriced_tokens') is not None and period.get('tokens') is not None and period['unpriced_tokens']>period['tokens']:
        raise ValueError('unpriced tokens exceed total')
    c={k:period.get(k) for k in ('from','to','days','tokens','api_equivalent_cost_usd','unpriced_tokens','sessions','session_days','basis',
                                 'coverage_status','daily','provider_models','token_classes','events')}
    # Never fall back to lifetime or whole-session window values.
    c['from']=period.get('from_day',period.get('from'))
    c['to']=period.get('to_day',period.get('to'))
    c['basis']=period.get('basis') or ('provider daily usage events; inclusive UTC dates' if period else None)
    if c.get('coverage_status') is None and telemetry.get('contract')=='spend-outcomes-observation-v1':
        c['coverage_status']=telemetry.get('coverage',{}).get('status','unknown')
    c.update({'billed_cash_usd':None,'subscription_charge_usd':None,'attribution':row.get('attribution','unattributed'),
              'cost_meaning':'API-list-price equivalent for known token classes; not invoice or subscription allocation'})
    source={'contract':telemetry['contract'],'producer':telemetry.get('producer'),'generation':telemetry.get('generation'),
            'as_of':telemetry.get('generation',{}).get('finished_at'),'status':telemetry.get('status','unknown'),
            'coverage':telemetry.get('coverage',{}),'sources':telemetry.get('sources',[]),
            'conflicts':telemetry.get('conflicts'),'conflict_summary':conflict_summary(telemetry.get('conflicts')),
            'units':telemetry.get('units',{}),
            'scope':telemetry.get('scope',{}),'freshness':telemetry.get('freshness',{}),
            'collection':telemetry.get('collection',{}),'pricing':telemetry.get('pricing',{})}
    facts=[];limitations=['Human effort, causal ROI and quality preservation are not established by activity.',
                          'Native/session, project, accounting and executor views are non-additive.']
    if not rows:limitations.append('Selected telemetry project was not observed; consumption is unknown.')
    if not period:limitations.append('Source project period is unavailable; lifetime totals were not substituted.')
    if telemetry.get('status')!='current':limitations.append('Source is '+str(telemetry.get('status','unknown'))+'; regeneration does not refresh observation time.')
    source_issues=[]
    if source['status']!='current':source_issues.append('Source status is '+str(source['status'])+'; a current producer observation is needed for current-source claims.')
    for issue in telemetry.get('coverage',{}).get('issues',[]):
        if isinstance(issue,str):
            source_issues.append(issue)
            limitations.append(issue)
    if not rows:source_issues.append('Selected telemetry project is not observed; its selected-project period is unavailable.')
    elif not period:source_issues.append('The selected-project period is unavailable; request its supported UTC period from the producer.')
    if source['conflict_summary']['status']!='zero':
        source_issues.append(source['conflict_summary']['reason'])
        limitations.append(source['conflict_summary']['reason'])
    if c['unpriced_tokens'] is None or c['unpriced_tokens']>0:limitations.append('Unpriced portion is unknown or positive; estimated dollars are not a fully priced total.')
    if outcomes is not None:
        if outcomes.get('contract')!='pv-outcomes-v1' or outcomes.get('permitted') is not True or outcomes.get('project_id')!=binding['project_id']:
            raise ValueError('disallowed outcome export or project mismatch')
        if not outcomes.get('source_id') or not outcomes.get('version'):raise ValueError('outcome source/version required')
        seen={}
        for o in outcomes.get('outcomes',[]):
            if not o.get('id') or not o.get('version') or o.get('association') not in ('exact','owner-attested','correlated','unattributed','shared'):
                raise ValueError('outcome identity/version/association required')
            key=(o['id'],o['version'])
            if key in seen:
                if seen[key]!=o:raise ValueError('outcome version conflict')
                continue
            seen[key]=o
            facts.append({**{k:o.get(k) for k in OUTCOME_FIELDS},'source_id':outcomes['source_id'],'source_version':outcomes['version']})
    # Consumer quality metadata is already owner-produced and scoped to a canonical
    # Project. It supplies delivery/review facts, not artifact or benefit evidence.
    for o in telemetry.get('quality',{}).get('outcomes',[]):
        if o.get('project_id')!=binding['project_id']:continue
        if not o.get('outcome_id'):
            limitations.append('Producer quality observation lacks an outcome identity; logical association is unknown.')
            continue
        facts.append({'id':o.get('outcome_id'),'version':o.get('last_at'),
                      'source_id':'agent-telemetry:quality','source_version':digest(telemetry.get('generation',{})),
                      'association':'owner-attested','delivered':o.get('delivered'),
                      'acceptance':o.get('verdict') if o.get('acceptance_basis')=='human' else None,
                      'acceptance_basis':o.get('acceptance_basis'),'review_verdict':o.get('verdict'),
                      'benefit':None,'installed':None,'artifact':None,'checks':None,
                      'rework':o.get('repairs'),'observed_at':o.get('last_at'),
                      'usage_attribution':o.get('usage_attribution'),
                      'basis':'Whole outcomes by last receipt; recent consumer metadata is bounded, not a complete artifact export.'})
    # Exact observation replay collapses; source/version differences never do.
    facts=list({digest(o):o for o in facts}.values())
    grouped={}
    for o in facts:grouped.setdefault(o['id'],[]).append(o)
    conflicts=[];current=[]
    for identity,observations in grouped.items():
        fields={}
        for field in ('delivered','installed','acceptance','benefit','review_verdict','rework','corrections'):
            values={digest(o[field]):o[field] for o in observations if o.get(field) is not None}
            if len(values)>1:fields[field]=list(values.values())
        if fields:
            conflicts.append({'id':identity,'fields':fields,'observations':[digest(o) for o in observations],
                              'basis':'Different source/version observations; no automatic supersession or acceptance equivalence.'})
        # Clocks rank decision relevance only, never delete historical evidence.
        dated=[(observation_time(o),o) for o in observations]
        known=[t for t,o in dated if t is not None]
        latest=max(known) if known else None
        current.extend(o for t,o in dated if t is None or t==latest)
    contrary=[o for o in current if o.get('review_verdict') in ('needs-changes','rejected') or o.get('acceptance') in ('needs-changes','rejected')]
    if conflicts:limitations.append('Outcome observations disagree across sources or versions; inspect outcome_conflicts before claiming accepted quality.')
    if not facts:limitations.append('No approved detailed result export: delivery, acceptance and benefit remain unknown.')
    normalized_targets=[]
    for target in targets:
        target=copy.deepcopy(target)
        if target.get('window')=='rolling-7-days' and target.get('kind')=='numeric':
            target.setdefault('from',c.get('from'));target.setdefault('to',c.get('to'))
            if c.get('days')!=7:target['from']=target['to']=None
        normalized_targets.append(target)
    comp=[comparison(t,c,binding) for t in normalized_targets]
    qualified_outcome=operator_outcome(local_outcome)
    if contrary:
        recommendation={'action':'investigate','next':'Inspect contrary needs-changes/rejected review for '+', '.join(sorted({o['id'] for o in contrary}))+'; reconcile the review with its artifact and check the required correction before a workflow change.',
                        'evidence':[digest(o) for o in contrary]+[digest(conflicts)],
                        'missing':'Owner-linked rework/check evidence and human re-review; unknown observation clocks require source ordering before claiming a current acceptance.',
                        'alternative':'Keep the existing approach while investigating; historical delivery and independent usage remain usable.'}
    elif source_issues:
        recommendation={'action':'investigate','next':'Inspect the selected producer generation for these specific issues: '+' '.join(source_issues),
                        'evidence':[digest(source)],'missing':' '.join(source_issues), 'alternative':'Keep the existing approach while independent observations remain usable; hold only claims depending on these source qualifications.'}
    elif any(x.get('excess',0) and x['excess']>0 for x in comp):
        recommendation={'action':'change','next':'Propose one bounded workflow test; compare the same UTC token/cost basis and record result acceptance and contrary feedback before adopting it.',
                        'evidence':[digest(comp)],'missing':'Comparable accepted result and operator feedback for the proposed test.', 'alternative':'Keep the existing approach; exceeding a target authorizes no execution.'}
    else:
        recommendation={'action':'hold','next':'Hold the claim that the workflow saved money or preserved quality; obtain same-scope prior evidence and an attributed acceptance/usefulness observation.',
                        'evidence':[digest(c)],'missing':'Comparable baseline and human usefulness evidence.', 'alternative':'Keep the existing approach or investigate a specific source limitation.'}
    recommendation['evidence']=list(dict.fromkeys(recommendation['evidence']+[digest(o) for o in current]))
    if current and any(o.get('acceptance') is None or o.get('benefit') is None for o in current):
        recommendation['missing']+=' Current human acceptance/usefulness evidence remains incomplete; an agent verdict supplies no human acceptance.'
    prior={'status':'unavailable','reason':'No comparable prior/manual receipt supplied.'}
    if baseline:
        same=baseline.get('selection')==binding and baseline.get('consumption',{}).get('basis')==c.get('basis')
        old=baseline.get('consumption',{})
        # Period dates differ for prior periods, but durations and declared changed conditions must match.
        same=same and old.get('days')==c.get('days') and baseline.get('changed_conditions')==[]
        prior={'status':'comparable' if same else 'unsupported','previous':old,'changed_conditions':baseline.get('changed_conditions'),
               'reason':'Same declared scope, duration, units and source basis; no causal saving or acceptance equivalence inferred.' if same else 'Scope, duration, source basis or changed conditions not qualified.'}
    return {'contract':'pv-receipt-v1','selection':binding,'source':source,'consumption':c,'targets':normalized_targets,'comparisons':comp,
            'other_views':{k:telemetry.get('accounting',{}).get(k) for k in ('shared','totals','coverage_gaps','repositories')},
            'native_sessions':telemetry.get('sessions',[]),
            'capacity':telemetry.get('capacity',[]),'outcomes':facts,'outcome_conflicts':conflicts,
            'outcome_coverage':{'returned':len(grouped),'observations_returned':len(facts),
                                'count_basis':'Distinct logical outcome IDs in the selected Project; source/version observations are non-additive.','denominator':outcomes.get('denominator') if outcomes else None,
                                'telemetry_recent_total':telemetry.get('quality',{}).get('outcomes_total')},
            'operator_outcome':qualified_outcome,'human_benefit':None,'limitations':limitations,'prior_comparison':prior,'recommendation':recommendation,
            'advisory_only':True,'execution_effects':[]}
