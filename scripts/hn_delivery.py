#!/usr/bin/env python3
"""Deterministic Cherry Meter archive builder.

Despite the compatibility module name used by older product tests, this file has
no delivery or publication capability.
"""
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile


FIXED_TIME = (2020, 1, 1, 0, 0, 0)


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n").encode("utf-8")


def _entry(name, data):
    info=zipfile.ZipInfo(name,FIXED_TIME)
    info.compress_type=zipfile.ZIP_DEFLATED
    info.create_system=3
    info.external_attr=(0o100644 << 16)
    return info,data


def build(root, revision):
    """Build only committed application source from an exact Git object."""
    root=Path(root).resolve()
    if not isinstance(revision,str) or not re.fullmatch(r"[0-9a-f]{40,64}",revision):
        raise ValueError("full candidate object id required")
    subprocess.run(["git","cat-file","-e",revision+"^{commit}"],cwd=root,check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    archive=subprocess.check_output(["git","archive","--format=tar",revision,"spend_outcomes"],cwd=root)
    entries=[]
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in sorted(source.getmembers(),key=lambda item:item.name):
            if member.isfile() and member.name.endswith(".py"):
                entries.append(_entry(member.name,source.extractfile(member).read()))
    init=next((data for info,data in entries if info.filename=="spend_outcomes/__init__.py"),None)
    if init is None:raise ValueError("candidate package is missing")
    tree=ast.parse(init.decode("utf-8"))
    versions=[ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
              and any(isinstance(target,ast.Name) and target.id=="__version__" for target in node.targets)]
    if len(versions)!=1 or not isinstance(versions[0],str) or not re.fullmatch(r"\d+\.\d+\.\d+",versions[0]):
        raise ValueError("candidate version is missing or invalid")
    entries.extend([
        _entry("SOURCE.json",_encoded({"product":"spend-outcomes","source_revision":revision,"version":versions[0]})),
        _entry("__main__.py",b"from spend_outcomes.__main__ import main\nraise SystemExit(main())\n"),
    ])
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as target:
        for info,data in sorted(entries,key=lambda item:item[0].filename):target.writestr(info,data)
    data=output.getvalue()
    return {"bytes":data,"sha256":hashlib.sha256(data).hexdigest(),
            "source_revision":revision,"version":versions[0]}


def read_artifact(path, expected_sha256):
    data=Path(path).read_bytes();actual=hashlib.sha256(data).hexdigest()
    if actual!=expected_sha256:raise ValueError("release artifact digest mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        identity=json.loads(archive.read("SOURCE.json"))
    return {"identity":identity,"sha256":actual}
