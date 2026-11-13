"""Privacy-bounded Codex JSONL metadata reader.

Only timestamps, session/workspace identity, models, and token counters leave
this module. Prompt, response, instruction, and tool content is never retained.
"""
import datetime as dt
import hashlib
import json
import os
import time
import math
import copy
import stat
from pathlib import Path


TOKEN_KEYS=("input_tokens","cached_input_tokens","cache_write_tokens",
            "output_tokens","reasoning_output_tokens")


def _stamp(value):
    if not isinstance(value,str):return None
    try:
        parsed=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:return None
    return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo is not None else None


def _iso(value):return value.isoformat().replace("+00:00","Z") if value else None


def _count(value):return value if type(value) is int and value>=0 else None


def _model(value):
    if not isinstance(value,str) or not value or len(value)>160 or any(ord(char)<32 for char in value):return "unknown"
    return value


def _classes(raw):
    if not isinstance(raw,dict):return None
    values={key:_count(raw.get(key,0)) for key in TOKEN_KEYS}
    if any(value is None for value in values.values()):return None
    if "total_tokens" in raw and _count(raw["total_tokens"]) is None:return None
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


def _lines(handle, issues, deadline, max_bytes, max_line_bytes):
    consumed = 0
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            issues.append("scan_deadline_exceeded"); return
        line = handle.readline(min(max_line_bytes + 1, max_bytes - consumed + 1))
        if not line: return
        consumed += len(line)
        if consumed > max_bytes:
            issues.append("source_size_limit_exceeded"); return
        if len(line) > max_line_bytes:
            issues.append("source_line_limit_exceeded"); return
        yield line


def _merge_event(events, conflicts, event):
    identity = event["identity"]
    if identity in conflicts: return
    if identity in events and events[identity] != event:
        conflicts.add(identity); events.pop(identity)
    else: events[identity] = event


def parse_codex_file(path, *, deadline=None, max_bytes=64*1024*1024, max_line_bytes=1024*1024, path_guard=None, cancel_check=None):
    """Return one metadata-only session record and explicit coverage issues."""
    session=None;workspace=None;model="unknown";events=[];issues=[]
    counter_snapshots={};counter_conflicts=set();counter_order=[];responses={};response_conflicts=set();compactions=set()
    try:
        handle=Path(path).open("rb")
    except OSError as error:
        return {"session":None,"workspace":None,"events":[],"issues":[type(error).__name__]}
    with handle:
        for line_number,line in enumerate(_lines(handle,issues,deadline,max_bytes,max_line_bytes),1):
            if cancel_check:cancel_check()
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
                if isinstance(payload.get("id"),str) and payload["id"]:
                    if session is not None and session!=payload["id"]:issues.append("conflicting_session_metadata")
                    else:session=payload["id"]
                if isinstance(payload.get("cwd"),str) and os.path.isabs(payload["cwd"]):
                    if path_guard:
                        try:path_guard(payload['cwd'])
                        except ValueError:
                            issues.append('unsupported_workspace_path');continue
                    if workspace is not None and _normal(workspace)!=_normal(payload["cwd"]):issues.append("conflicting_session_metadata")
                    else:workspace=payload["cwd"]
            elif kind=="turn_context" and isinstance(payload.get("model"),str):model=_model(payload["model"])
            elif kind=="token_usage_record":
                classes=_classes(payload.get("usage"));response=payload.get("response_id")
                if (classes is not None and timestamp is not None and isinstance(response,str) and response
                        and isinstance(session,str) and payload.get("thread_id")==session):
                    identity=hashlib.sha256(("codex\0"+session+"\0response\0"+response).encode()).hexdigest()
                    event=_event(identity,timestamp,model,classes,"compaction-response")
                    _merge_event(responses,response_conflicts,event)
            elif kind=="compacted" and isinstance(payload.get("compaction_response_id"),str):
                compactions.add(payload["compaction_response_id"])
            elif kind=="event_msg" and payload.get("type")=="token_count":
                info=payload.get("info") if isinstance(payload.get("info"),dict) else {}
                total=_classes(info.get("total_token_usage"));last=_classes(info.get("last_token_usage"))
                if total is None or timestamp is None:
                    if info:issues.append("invalid_token_counter")
                    continue
                signature=json.dumps([session or "unknown-session",_iso(timestamp),"counter"],sort_keys=True,separators=(",",":"))
                identity=hashlib.sha256(signature.encode()).hexdigest()
                snapshot={"identity":identity,"timestamp":timestamp,"total":total,"last":last,"model":model}
                if identity in counter_snapshots:
                    if counter_snapshots[identity]!=snapshot:
                        counter_conflicts.add(identity);issues.append("conflicting_event_observation")
                    continue
                counter_snapshots[identity]=snapshot;counter_order.append(identity)
    # Resolve all duplicate conflicts before using any cumulative value as a
    # baseline. Only sanitized counters are retained for this second pass.
    previous=None;previous_total=None;latest_counter=None;previous_identity=None
    quarantine=False
    conflict_times=[counter_snapshots[key]["timestamp"] for key in counter_conflicts]
    for identity in counter_order:
        if cancel_check:cancel_check()
        row=counter_snapshots[identity]
        timestamp=row["timestamp"];total=row["total"];last=row["last"];model=row["model"]
        if identity in counter_conflicts:
            # An old replay cannot invalidate a newer clean baseline.
            if latest_counter is None or timestamp>=latest_counter:
                previous=None;previous_total=None;previous_identity=None
                latest_counter=timestamp;quarantine=True
            continue
        cumulative=total["input_tokens"]+total["output_tokens"]
        if latest_counter is not None and timestamp<latest_counter:continue
        if previous is not None and cumulative==previous_total:continue
        crosses_conflict=(latest_counter is not None and
                          any(latest_counter<t<=timestamp for t in conflict_times))
        reset=previous_total is not None and cumulative<previous_total
        inferred=last is None
        inferred_baseline=inferred and (previous is None or reset)
        if inferred and (quarantine or crosses_conflict):
            issues.append("conflicted_counter_baseline_excluded")
            previous=total;previous_total=cumulative;latest_counter=timestamp
            previous_identity=identity;quarantine=False
            continue
        interval_start=latest_counter if inferred and previous is not None and not reset else None
        baseline_identity=previous_identity if interval_start is not None else None
        if inferred:
            if previous is None or reset:last=total
            else:last={key:total[key]-previous[key] for key in TOKEN_KEYS}
        if _classes(last) is None:
            issues.append("invalid_token_counter_delta")
        else:
            event=_event(identity,timestamp,model,last,"counter-inferred-baseline" if inferred_baseline else "counter")
            if interval_start is not None:
                event["interval_start"]=_iso(interval_start)
                event["baseline_identity"]=baseline_identity
            events.append(event)
        previous=total;previous_total=cumulative;latest_counter=timestamp
        previous_identity=identity;quarantine=False
    for response in sorted(compactions):
        identity=hashlib.sha256(("codex\0"+session+"\0response\0"+response).encode()).hexdigest() if session else None
        if identity in response_conflicts:issues.append("conflicting_event_observation")
        elif identity in responses:events.append(responses[identity])
        else:issues.append("compaction_usage_unavailable")
    if session is None:
        session="file-"+hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:24]
        issues.append("session_identity_unavailable")
    # Repeated markers and copied rows collapse by their private metadata identity.
    unique={};event_conflicts=set(counter_conflicts)|response_conflicts
    for event in events:_merge_event(unique,event_conflicts,event)
    if event_conflicts:issues.append("conflicting_event_observation")
    events=[] if "conflicting_session_metadata" in issues else list(unique.values())
    return {"session":session,"workspace":workspace,"events":events,"issues":sorted(set(issues)),"conflict_identities":sorted(event_conflicts)}


def _normal(path):return os.path.normcase(os.path.realpath(os.path.expanduser(str(path))))


def _inside(value,root):
    try:return os.path.commonpath((_normal(value),_normal(root)))==_normal(root)
    except (ValueError,TypeError):return False


def _project_roots(project):
    values=[]
    if project.get("workspace"):values.append(project["workspace"])
    values.extend(project.get("additional_workspaces",[]))
    return [_normal(value) for value in values]


def _validate_view(projects, selected, days, through, tracking_start):
    if type(days) is not int or days<=0:raise ValueError("direct Codex observations require a positive day window")
    tracking=_stamp(tracking_start) if tracking_start is not None else None
    if tracking_start is not None and tracking is None:raise ValueError("tracking_start must be a timezone-aware timestamp")
    end=dt.date.fromisoformat(through) if through else dt.datetime.now(dt.timezone.utc).date()
    start=end-dt.timedelta(days=days-1)
    mappings={key:_project_roots(value) for key,value in projects.items() if value.get("permitted") is True}
    if selected is not None and (selected not in mappings or not mappings[selected]):raise ValueError("selected project requires an explicit workspace")
    return tracking,end,start,mappings


def _walk_guarded(root, guard, deadline, issues, max_entries=10000):
    """MCP traversal: never follow entries merely to classify directories."""
    stack=[root]; entries=0
    while stack:
        directory=stack.pop();guard(directory)
        dirs=[];files=[]
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    if time.monotonic() >= deadline or entries >= max_entries:
                        issues.append('source_enumeration_limit_exceeded');return
                    entries+=1
                    info=entry.stat(follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                        issues.append('unsupported_source_path');continue
                    try:guard(entry.path)
                    except ValueError:
                        issues.append('unsupported_source_path');continue
                    if stat.S_ISDIR(info.st_mode):dirs.append(entry.name)
                    elif stat.S_ISREG(info.st_mode):files.append(entry.name)
        except OSError:
            issues.append('source_enumeration_failed');continue
        yield str(directory),dirs,files
        stack.extend(Path(directory,name) for name in reversed(sorted(dirs)))


def _scan_codex(roots, *, tracking_start=None, max_seconds=30, max_files=10000,
                max_file_bytes=64*1024*1024, max_line_bytes=1024*1024, path_guard=None, cancel_check=None):
    """Read each source into bounded, allowlisted metadata; never retain raw JSON."""
    if isinstance(max_seconds,bool) or not isinstance(max_seconds,(int,float)) or not math.isfinite(max_seconds) or max_seconds<=0:
        raise ValueError("max_seconds must be positive and finite")
    if any(type(value) is not int or value<=0 for value in (max_files,max_file_bytes,max_line_bytes)):
        raise ValueError("scan limits must be positive integers")
    deadline=time.monotonic()+max_seconds
    scanned=0
    records=[];source_rows=[];global_issues=[];available=0
    for raw_root in roots:
        if path_guard:
            path_guard(raw_root)
        root=Path(raw_root).expanduser();resolved=Path(_normal(root))
        if not resolved.is_dir():
            source_rows.append({"kind":"codex","root":str(root),"status":"missing","files":0})
            global_issues.append("configured Codex root is missing: "+str(root));continue
        available+=1;files=0;root_issues=[]
        def failed(error):root_issues.append("source_enumeration_failed")
        stop=False
        walking = _walk_guarded(resolved,path_guard,deadline,root_issues) if path_guard else os.walk(resolved,followlinks=False,onerror=failed)
        for directory, subdirs, filenames in walking:
            if path_guard:
                path_guard(directory)
            safe_dirs=[]
            for name in subdirs:
                child=Path(directory,name)
                if path_guard:
                    try:path_guard(child)
                    except ValueError:
                        root_issues.append('unsupported_source_path');continue
                if not child.is_symlink() and _inside(child,resolved):safe_dirs.append(name)
            subdirs[:]=sorted(safe_dirs)
            if time.monotonic()>=deadline:
                root_issues.append("scan_deadline_exceeded");break
            for name in sorted(filenames):
                if not name.endswith(".jsonl"):continue
                if time.monotonic()>=deadline or scanned>=max_files:
                    root_issues.append("scan_deadline_exceeded" if time.monotonic()>=deadline else "source_file_limit_exceeded")
                    stop=True;break
                path=Path(directory,name)
                try:
                    if path_guard:
                        try:path_guard(path)
                        except ValueError:
                            root_issues.append('unsupported_source_path');continue
                    if path.is_symlink() or not _inside(path.resolve(),resolved):continue
                    record=parse_codex_file(path,deadline=deadline,max_bytes=max_file_bytes,max_line_bytes=max_line_bytes,path_guard=path_guard,cancel_check=cancel_check)
                    records.append(record);files+=1;scanned+=1
                    root_issues.extend(record["issues"])
                except OSError:root_issues.append("source_file_unreadable")
            if stop:break
        if root_issues:global_issues.extend(root_issues)
        source_rows.append({"kind":"codex","root":str(root),"status":"partial" if root_issues else "current","files":files,"issues":sorted(set(root_issues)),"tracking_start":tracking_start})
    return {"records":records,"sources":source_rows,"issues":global_issues,"available":available,
            "finished_at":_iso(dt.datetime.now(dt.timezone.utc)),"max_seconds":max_seconds}


def _derive_codex(scan, projects, selected, days, through, tracking_start):
    """Derive a view without reading or mutating the metadata snapshot."""
    tracking,end,start,mappings=_validate_view(projects,selected,days,through,tracking_start)
    records=scan["records"]
    source_rows=copy.deepcopy(scan["sources"])
    global_issues=list(scan["issues"])
    available=scan["available"]
    max_seconds=scan["max_seconds"]
    # Consolidate copied histories by session and event identity without assigning
    # sessions whose workspace evidence conflicts.
    sessions={}
    for record in records:
        target=sessions.setdefault(record["session"],{"workspaces":set(),"events":{},"issues":set(),"conflicts":set()})
        if record.get("workspace"):target["workspaces"].add(_normal(record["workspace"]))
        target["issues"].update(record.get("issues",[]))
        target["conflicts"].update(record.get("conflict_identities",[]))
        for identity in target["conflicts"]:target["events"].pop(identity,None)
        for event in record.get("events",[]):_merge_event(target["events"],target["conflicts"],event)
        if target["conflicts"]:target["issues"].add("conflicting_event_observation")
    for value in sessions.values():
        dependent=[key for key,event in value["events"].items()
                   if event.get("baseline_identity") in value["conflicts"]]
        if dependent:value["issues"].add("conflicted_counter_baseline_excluded")
        for key in dependent:value["events"].pop(key)
    selected_events={};selected_sessions=0;ambiguous=0;out_of_scope=0;unassigned=0;relevant_issues=[]
    device_scope=selected is None
    device_conflicts=set()
    for session,value in sessions.items():
        matches=[]
        if len(value["workspaces"])!=1:
            unassigned+=1
            if not device_scope:
                relevant_issues.extend(value["issues"]);continue
        else:
            workspace=next(iter(value["workspaces"]))
            matches=[key for key,workspace_roots in mappings.items() if any(_inside(workspace,root) for root in workspace_roots)]
            if len(matches)>1:
                ambiguous+=1
                if not device_scope:continue
            elif not matches:
                unassigned+=int(device_scope)
        if not device_scope and matches!=[selected]:
            out_of_scope+=1;continue
        selected_sessions+=1
        relevant_issues.extend(value["issues"])
        device_conflicts.update(value["conflicts"])
        for identity in device_conflicts:selected_events.pop(identity,None)
        for event in value["events"].values():_merge_event(selected_events,device_conflicts,event)
    in_window=[event for event in selected_events.values() if start.isoformat()<=event["day"]<=end.isoformat() and (tracking is None or _stamp(event["timestamp"])>=tracking)]
    boundary=dt.datetime.combine(start,dt.time.min,dt.timezone.utc)
    effective_start=max(boundary,tracking) if tracking is not None else boundary
    crossing=[event for event in in_window if event.get("interval_start") is not None
              and _stamp(event["interval_start"])<effective_start]
    if crossing:
        relevant_issues.append("inferred_counter_interval_crosses_report_start")
        in_window=[event for event in in_window if event not in crossing]
    if tracking is not None:
        if any(event["kind"]=="counter-inferred-baseline" for event in in_window):
            relevant_issues.append("prospective_counter_baseline_unavailable")
            in_window=[event for event in in_window if event["kind"]!="counter-inferred-baseline"]
    daily={};models={};classes={key:0 for key in TOKEN_KEYS}
    for event in in_window:
        day=daily.setdefault(event["day"],{"date":event["day"],"tokens":0,**{key:0 for key in TOKEN_KEYS}})
        model=models.setdefault(event["model"],{"provider":"openai","client":"codex","service_route":"unknown","model":event["model"],"tokens":0,**{key:0 for key in TOKEN_KEYS}})
        day["tokens"]+=event["tokens"];model["tokens"]+=event["tokens"]
        for key in TOKEN_KEYS:
            day[key]+=event["classes"][key];model[key]+=event["classes"][key];classes[key]+=event["classes"][key]
    if tracking is not None and tracking > dt.datetime.combine(start,dt.time.min,dt.timezone.utc):
        global_issues.append("tracking_started_within_report_window")
    partial=bool(global_issues or relevant_issues or ambiguous or unassigned)
    coverage_status="unavailable" if not available else "partial" if partial else "complete"
    conflicts=[]
    conflicting=sum(len(value["conflicts"]) for value in sessions.values())
    if conflicting:conflicts.append({"source":"codex","detail":f"{conflicting} conflicting event identity(s) excluded"})
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
    now=scan["finished_at"]
    status="unavailable" if not available else "partial" if partial else "current"
    issues=global_issues+sorted(set(relevant_issues))
    project_rows=[{"project_id":"device" if device_scope else selected,"project_code":"device" if device_scope else selected,
                   "attribution":"explicit-source-roots-device" if device_scope else "workspace-evidence","period":period}] if period else []
    return {"contract":"spend-outcomes-observation-v1","producer":"spend-outcomes-codex","status":status,
            "generation":{"finished_at":now},"projects":project_rows,
            "sources":source_rows,"coverage":{"status":coverage_status,"issues":issues,"ambiguous_sessions":ambiguous,
                "unassigned_sessions":unassigned,"out_of_scope_sessions":out_of_scope,
                "privacy":"metadata-only; prompt, response, instruction, and tool content excluded"},
            "conflicts":{"total":len(conflicts),"items":conflicts},"units":{"tokens":"observed input plus output; cache/reasoning are subsets"},
            "collection":{"triggered":False,"roots":"explicit-only","tracking_start":tracking_start,"deadline_seconds":max_seconds,"deadline_enforcement":"cooperative between bounded reads; OS I/O may block"},"pricing":{"status":"unavailable"},
            "accounting":{"shared":None,"totals":None,"coverage_gaps":issues,"repositories":None}}


def observe_codex(roots, projects, selected, days=7, through=None, *, tracking_start=None,
                  max_seconds=30, max_files=10000, max_file_bytes=64*1024*1024,
                  max_line_bytes=1024*1024):
    """Normalize one explicitly permitted source scan to the receipt shape."""
    _,end,_,_=_validate_view(projects,selected,days,through,tracking_start)
    scan=_scan_codex(roots,tracking_start=tracking_start,max_seconds=max_seconds,max_files=max_files,
                     max_file_bytes=max_file_bytes,max_line_bytes=max_line_bytes)
    return _derive_codex(scan,projects,selected,days,end.isoformat(),tracking_start)


def observe_codex_views(roots, projects, days=7, through=None, tracking_start=None, **limits):
    """Return device and project observations derived from ONE metadata scan.

    All views use the same scan completion time and UTC window. This is a
    sequential filesystem observation, not an atomic snapshot of live files.
    The intermediate snapshot contains only parser-allowlisted metadata and
    does not escape this call or persist raw log records.
    """
    _,end,_,mappings=_validate_view(projects,None,days,through,tracking_start)
    for key in mappings:_validate_view(projects,key,days,end.isoformat(),tracking_start)
    scan=_scan_codex(roots,tracking_start=tracking_start,**limits)
    return {"device":_derive_codex(scan,projects,None,days,end.isoformat(),tracking_start),
            "projects":{key:_derive_codex(scan,projects,key,days,end.isoformat(),tracking_start)
                        for key in mappings}}
