"""Privacy-bounded Codex JSONL metadata reader.

Only timestamps, session/workspace identity, models, and token counters leave
this module. Prompt, response, instruction, and tool content is never retained.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path


TOKEN_KEYS=("input_tokens","cached_input_tokens","cache_write_tokens",
            "output_tokens","reasoning_output_tokens")


def _stamp(value):
    if not isinstance(value,str):return None
    try:
        parsed=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:return None
    return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo is not None else None


def _iso(value):return value.replace(microsecond=0).isoformat().replace("+00:00","Z") if value else None


def _count(value):return value if type(value) is int and value>=0 else None


def _model(value):
    if not isinstance(value,str) or not value or len(value)>160 or any(ord(char)<32 for char in value):return "unknown"
    return value


def _classes(raw):
    if not isinstance(raw,dict):return None
    values={key:_count(raw.get(key,0)) for key in TOKEN_KEYS}
    if any(value is None for value in values.values()):return None
    total=_count(raw.get("total_tokens"))
    if total is None:total=values["input_tokens"]+values["output_tokens"]
    if values["input_tokens"]+values["output_tokens"]!=total:return None
    if values["cached_input_tokens"]>values["input_tokens"]:return None
    if values["reasoning_output_tokens"]>values["output_tokens"]:return None
    return values


def _event(identity, timestamp, model, classes, kind):
    return {"identity":identity,"timestamp":_iso(timestamp),"day":timestamp.date().isoformat(),
            "model":_model(model),"classes":classes,"tokens":classes["input_tokens"]+classes["output_tokens"],
            "kind":kind}


def parse_codex_file(path):
    """Return one metadata-only session record and explicit coverage issues."""
    session=None;workspace=None;model="unknown";events=[];issues=[]
    responses={};compactions=set();previous=None;previous_total=None;latest_counter=None
    try:
        handle=Path(path).open("rb")
    except OSError as error:
        return {"session":None,"workspace":None,"events":[],"issues":[type(error).__name__]}
    with handle:
        for line_number,line in enumerate(handle,1):
            if not line.endswith(b"\n"):
                issues.append("partial_trailing_line");continue
            try:obj=json.loads(line)
            except (json.JSONDecodeError,UnicodeDecodeError):
                issues.append("malformed_jsonl");continue
            if not isinstance(obj,dict):continue
            payload=obj.get("payload") if isinstance(obj.get("payload"),dict) else {}
            timestamp=_stamp(obj.get("timestamp"))
            kind=obj.get("type")
            if kind=="session_meta":
                if isinstance(payload.get("id"),str) and payload["id"]:session=payload["id"]
                if isinstance(payload.get("cwd"),str) and os.path.isabs(payload["cwd"]):workspace=payload["cwd"]
            elif kind=="turn_context" and isinstance(payload.get("model"),str):model=_model(payload["model"])
            elif kind=="token_usage_record":
                classes=_classes(payload.get("usage"));response=payload.get("response_id")
                if (classes is not None and timestamp is not None and isinstance(response,str) and response
                        and isinstance(session,str) and payload.get("thread_id")==session):
                    identity=hashlib.sha256(("codex\0"+session+"\0response\0"+response).encode()).hexdigest()
                    responses[response]=_event(identity,timestamp,model,classes,"compaction-response")
            elif kind=="compacted" and isinstance(payload.get("compaction_response_id"),str):
                compactions.add(payload["compaction_response_id"])
            elif kind=="event_msg" and payload.get("type")=="token_count":
                info=payload.get("info") if isinstance(payload.get("info"),dict) else {}
                total=_classes(info.get("total_token_usage"));last=_classes(info.get("last_token_usage"))
                if total is None or timestamp is None:
                    if info:issues.append("invalid_token_counter")
                    continue
                cumulative=total["input_tokens"]+total["output_tokens"]
                replay=(latest_counter is not None and timestamp<latest_counter) or cumulative==previous_total
                if not replay:
                    reset=previous_total is not None and cumulative<previous_total
                    if last is None:
                        if previous is None or reset:last=total
                        else:last={key:max(0,total[key]-previous[key]) for key in TOKEN_KEYS}
                    session_key=session or "unknown-session"
                    signature=json.dumps([session_key,_iso(timestamp),cumulative,last],sort_keys=True,separators=(",",":"))
                    identity=hashlib.sha256(signature.encode()).hexdigest()
                    events.append(_event(identity,timestamp,model,last,"counter"))
                    latest_counter=timestamp
                    previous=total;previous_total=cumulative
    for response in sorted(compactions):
        if response in responses:events.append(responses[response])
        else:issues.append("compaction_usage_unavailable")
    if session is None:
        session="file-"+hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:24]
        issues.append("session_identity_unavailable")
    # Repeated markers and copied rows collapse by their private metadata identity.
    events=list({event["identity"]:event for event in events}.values())
    return {"session":session,"workspace":workspace,"events":events,"issues":sorted(set(issues))}


def _normal(path):return os.path.normcase(os.path.realpath(os.path.expanduser(str(path))))


def _inside(value,root):
    try:return os.path.commonpath((_normal(value),_normal(root)))==_normal(root)
    except (ValueError,TypeError):return False


def _project_roots(project):
    values=[]
    if project.get("workspace"):values.append(project["workspace"])
    values.extend(project.get("additional_workspaces",[]))
    return [_normal(value) for value in values]


def observe_codex(roots, projects, selected, days=7, through=None):
    """Normalize explicitly permitted Codex roots to the source-neutral receipt shape."""
    if type(days) is not int or days<=0:raise ValueError("direct Codex observations require a positive day window")
    end=dt.date.fromisoformat(through) if through else dt.datetime.now(dt.timezone.utc).date()
    start=end-dt.timedelta(days=days-1)
    mappings={key:_project_roots(value) for key,value in projects.items() if value.get("permitted") is True}
    if selected not in mappings or not mappings[selected]:raise ValueError("selected project requires an explicit workspace")
    records=[];source_rows=[];global_issues=[];available=0
    for raw_root in roots:
        root=Path(raw_root).expanduser();resolved=Path(_normal(root))
        if not resolved.is_dir():
            source_rows.append({"kind":"codex","root":str(root),"status":"missing","files":0})
            global_issues.append("configured Codex root is missing: "+str(root));continue
        available+=1;files=0;root_issues=[]
        try:paths=sorted(resolved.rglob("*.jsonl"))
        except OSError:
            paths=[];root_issues.append("source_enumeration_failed")
        for path in paths:
            try:
                if path.is_symlink() or not _inside(path.resolve(),resolved):continue
                records.append(parse_codex_file(path));files+=1
            except OSError:root_issues.append("source_file_unreadable")
        if root_issues:global_issues.extend(root_issues)
        source_rows.append({"kind":"codex","root":str(root),"status":"partial" if root_issues else "current","files":files})
    # Consolidate copied histories by session and event identity without assigning
    # sessions whose workspace evidence conflicts.
    sessions={}
    for record in records:
        target=sessions.setdefault(record["session"],{"workspaces":set(),"events":{},"issues":set()})
        if record.get("workspace"):target["workspaces"].add(_normal(record["workspace"]))
        target["issues"].update(record.get("issues",[]))
        target["events"].update({event["identity"]:event for event in record.get("events",[])})
    selected_events={};selected_sessions=0;ambiguous=0;out_of_scope=0;unassigned=0;relevant_issues=[]
    for session,value in sessions.items():
        if len(value["workspaces"])!=1:
            unassigned+=1;relevant_issues.extend(value["issues"]);continue
        workspace=next(iter(value["workspaces"]))
        matches=[key for key,workspace_roots in mappings.items() if any(_inside(workspace,root) for root in workspace_roots)]
        if len(matches)>1:
            ambiguous+=1;continue
        if matches!=[selected]:
            out_of_scope+=1;continue
        selected_sessions+=1
        selected_events.update(value["events"]);relevant_issues.extend(value["issues"])
    in_window=[event for event in selected_events.values() if start.isoformat()<=event["day"]<=end.isoformat()]
    daily={};models={};classes={key:0 for key in TOKEN_KEYS}
    for event in in_window:
        day=daily.setdefault(event["day"],{"date":event["day"],"tokens":0,**{key:0 for key in TOKEN_KEYS}})
        model=models.setdefault(event["model"],{"provider":"openai","model":event["model"],"tokens":0,**{key:0 for key in TOKEN_KEYS}})
        day["tokens"]+=event["tokens"];model["tokens"]+=event["tokens"]
        for key in TOKEN_KEYS:
            day[key]+=event["classes"][key];model[key]+=event["classes"][key];classes[key]+=event["classes"][key]
    partial=bool(global_issues or relevant_issues or ambiguous or unassigned)
    coverage_status="unavailable" if not available else "partial" if partial else "complete"
    conflicts=[]
    if ambiguous:conflicts.append({"source":"codex","detail":f"{ambiguous} session(s) matched more than one explicit project workspace"})
    period=None
    if available:
        period={"from_day":start.isoformat(),"to_day":end.isoformat(),"days":days,
                "tokens":sum(event["tokens"] for event in in_window),"unpriced_tokens":sum(event["tokens"] for event in in_window),
                "api_equivalent_cost_usd":None,"basis":"Codex token counter events; inclusive UTC dates",
                "coverage_status":coverage_status,"daily":sorted(daily.values(),key=lambda value:value["date"]),
                "provider_models":sorted(models.values(),key=lambda value:value["model"]),"token_classes":classes,
                "sessions":selected_sessions,
                "events":len(in_window)}
    now=_iso(dt.datetime.now(dt.timezone.utc))
    status="unavailable" if not available else "partial" if partial else "current"
    issues=global_issues+sorted(set(relevant_issues))
    project_rows=[{"project_id":selected,"project_code":selected,
                   "attribution":"workspace-evidence","period":period}] if period else []
    return {"contract":"spend-outcomes-observation-v1","producer":"spend-outcomes-codex","status":status,
            "generation":{"finished_at":now},"projects":project_rows,
            "sources":source_rows,"coverage":{"status":coverage_status,"issues":issues,"ambiguous_sessions":ambiguous,
                "unassigned_sessions":unassigned,"out_of_scope_sessions":out_of_scope,
                "privacy":"metadata-only; prompt, response, instruction, and tool content excluded"},
            "conflicts":{"total":len(conflicts),"items":conflicts},"units":{"tokens":"observed input plus output; cache/reasoning are subsets"},
            "collection":{"triggered":False,"roots":"explicit-only"},"pricing":{"status":"unavailable"},
            "accounting":{"shared":None,"totals":None,"coverage_gaps":issues,"repositories":None}}
