#!/usr/bin/env python3
"""Safe episode registration helper. Dry-run is the default; --apply is explicit."""
from __future__ import annotations
import argparse, json, os, shutil, tempfile
from pathlib import Path
from validate_episode import validate_episode

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("episode"); ap.add_argument("--project",default="."); ap.add_argument("--apply",action="store_true"); ap.add_argument("--confirm",action="store_true"); ap.add_argument("--verified",action="store_true",help="explicitly attest human review is complete"); args=ap.parse_args()
    root=Path(args.project).resolve(); ep=Path(args.episode).resolve()
    if not ep.is_file(): print(f"REGISTRATION REFUSED: episode does not exist: {ep}"); return 1
    checks=validate_episode(root,ep)
    for x in checks: print(f"[{x['status']}] {x['message']}")
    if any(x["status"] in ("FAIL","NOT VERIFIED") for x in checks): print("REGISTRATION REFUSED: validation is not complete"); return 1
    if not args.verified: print("REGISTRATION REFUSED: --verified is required after human review"); return 1
    data=json.loads(ep.read_text(encoding="utf-8")); idx=root/"episodes.json"; rows=json.loads(idx.read_text(encoding="utf-8")); date=data["date"]; lang=data["lang"]
    if any(r.get("date")==date and (lang in r or (lang=="ja" and "title" in r)) for r in rows): print(f"REGISTRATION REFUSED: duplicate {date}/{lang}"); return 1
    row={"date":date,lang:{"title":data["title"],"seconds":data["seconds"]}}; new=sorted([row]+[r for r in rows if r.get("date")!=date],key=lambda r:r.get("date",""),reverse=True)
    print("DRY-RUN: would add",json.dumps(row,ensure_ascii=False));
    if not args.apply: return 0
    if not args.confirm: print("REGISTRATION REFUSED: --apply requires --confirm"); return 1
    backup=idx.with_suffix(idx.suffix+".bak"); shutil.copy2(idx,backup)
    fd,tmp=tempfile.mkstemp(prefix="episodes-",suffix=".json",dir=str(idx.parent)); os.close(fd)
    Path(tmp).write_text(json.dumps(new,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,idx); print(f"UPDATED: {idx}\nBACKUP: {backup}"); return 0
if __name__=="__main__": raise SystemExit(main())
