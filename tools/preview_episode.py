#!/usr/bin/env python3
"""Create an isolated, non-public preview copy without changing project data."""
from __future__ import annotations
import argparse, json, shutil, tempfile
from pathlib import Path
from validate_episode import validate_episode

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("episode"); ap.add_argument("--project",default="."); ap.add_argument("--output"); ap.add_argument("--station"); ap.add_argument("--only",action="store_true",help="show only the candidate in the preview list"); ap.add_argument("--serve",action="store_true"); args=ap.parse_args()
    project=Path(args.project).resolve(); ep=Path(args.episode).resolve()
    checks=validate_episode(project,ep)
    if any(x["status"]=="FAIL" for x in checks):
        print("Preview refused: validator FAIL"); [print(f"[{x['status']}] {x['message']}") for x in checks]; return 1
    out=Path(args.output).resolve() if args.output else Path(tempfile.mkdtemp(prefix="myradio-preview-"))
    if out == project or project in out.parents: raise SystemExit("output must be outside the source project")
    if out.exists() and any(out.iterdir()): raise SystemExit(f"output is not empty: {out}")
    shutil.copytree(project,out,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git","__pycache__","editorial","tests"))
    target=out/"episodes"/ep.name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ep,target)
    if args.station: shutil.copy2(Path(args.station).resolve(), out/"station.json")
    data=json.loads((out/"episodes.json").read_text(encoding="utf-8")); row={"date":json.loads(ep.read_text(encoding="utf-8"))["date"],"ja":{"title":json.loads(ep.read_text(encoding="utf-8")).get("title",""),"seconds":json.loads(ep.read_text(encoding="utf-8")).get("seconds",0)}}
    data=[] if args.only else [x for x in data if x.get("date")!=row["date"]]; data.insert(0,row); (out/"episodes.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"ISOLATED PREVIEW: {out}")
    print("No source project or public list was changed.")
    if args.serve: print("Serve with: python -m http.server 8780 --bind 127.0.0.1 --directory \"%s\"" % out)
    return 0
if __name__=="__main__": raise SystemExit(main())
