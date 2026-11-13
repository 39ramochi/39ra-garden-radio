#!/usr/bin/env python3
"""Read-only validator for monoradio/news-1 episode drafts and index files."""
from __future__ import annotations
import argparse, json, math, os, re, shutil, subprocess, sys, wave
from pathlib import Path
from urllib.parse import urlparse

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUSES = {"PASS", "WARN", "FAIL", "NOT VERIFIED"}

def result(status, message): return {"status": status, "message": message}
def add(out, status, message): out.append(result(status, message))
def finite(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
def http_url(v):
    try: return urlparse(v).scheme in ("http", "https") and bool(urlparse(v).netloc)
    except Exception: return False

def audio_duration(path):
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w: return w.getnframes() / w.getframerate()
        except Exception: return None
    if path.suffix.lower() == ".mp3" and shutil.which("ffprobe"):
        try:
            p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, timeout=15)
            return float(p.stdout.strip()) if p.returncode == 0 else None
        except Exception: return None
    return None

def validate_episode(root: Path, ep_path: Path):
    out=[]; name=ep_path.name
    m=re.match(r"^(\d{4}-\d{2}-\d{2})-([A-Za-z0-9_-]+)\.json$", name)
    try: data=json.loads(ep_path.read_text(encoding="utf-8"))
    except Exception as e: return [result("FAIL", f"JSON parse: {e}")]
    add(out,"PASS","JSON parse")
    for k in ("format","date","lang","title","seconds","opening","news","closing","lines_timed","segments","audio"):
        if k not in data: add(out,"FAIL",f"missing key: {k}")
    if data.get("format") != "monoradio/news-1": add(out,"FAIL","format must be monoradio/news-1")
    else: add(out,"PASS","format")
    if not isinstance(data.get("date"),str) or not DATE_RE.fullmatch(data.get("date","")): add(out,"FAIL","date must be YYYY-MM-DD")
    elif m and data["date"] != m.group(1): add(out,"FAIL","date does not match filename")
    else: add(out,"PASS","date/filename")
    if not isinstance(data.get("lang"),str) or not data.get("lang"): add(out,"FAIL","lang must be non-empty")
    if not isinstance(data.get("title"),str) or not data.get("title" ).strip(): add(out,"FAIL","title must be non-empty")
    if not finite(data.get("seconds")) or data["seconds"] <= 0: add(out,"FAIL","seconds must be positive")
    sections=["opening","news","closing"]
    if not all(isinstance(data.get(k),list) for k in sections): add(out,"FAIL","opening/news/closing must be arrays")
    else:
        if not data["news"]: add(out,"WARN","news is empty")
        for sec_name in ("opening","closing"):
            for j,line in enumerate(data[sec_name]):
                if not isinstance(line,dict) or not isinstance(line.get("say"),str) or not isinstance(line.get("show"),str) or not line.get("say","").strip() or not line.get("show","").strip(): add(out,"FAIL",f"{sec_name}[{j}] requires non-empty say/show")
        for i,n in enumerate(data["news"]):
            if not isinstance(n,dict): add(out,"FAIL",f"news[{i}] must be object"); continue
            for k in ("label","points","lines","url"):
                if k not in n: add(out,"FAIL",f"news[{i}] missing {k}")
            if not isinstance(n.get("points"),list) or not isinstance(n.get("lines"),list): add(out,"FAIL",f"news[{i}] points/lines must be arrays")
            for j,line in enumerate(n.get("lines",[])):
                if not isinstance(line,dict) or not isinstance(line.get("say"),str) or not isinstance(line.get("show"),str) or not line.get("say","").strip() or not line.get("show","").strip(): add(out,"FAIL",f"news[{i}] line[{j}] requires non-empty say/show")
            if "details" in n and (not isinstance(n["details"],list) or len(n["details"]) != len(n.get("points",[]))): add(out,"FAIL",f"news[{i}] details length mismatch")
            if not http_url(n.get("url","")): add(out,"FAIL",f"news[{i}] url must be http/https")
            for lk in ("link",):
                if lk in n:
                    if not isinstance(n[lk],dict) or not http_url(n[lk].get("url","")): add(out,"FAIL",f"news[{i}] link.url invalid")
                    if isinstance(n[lk],dict):
                        for asset_key in ("image","icon"):
                            asset=n[lk].get(asset_key)
                            if asset and not http_url(asset):
                                apath=(root/asset).resolve()
                                if root.resolve() not in apath.parents and apath != root.resolve(): add(out,"FAIL",f"news[{i}] {asset_key} path escapes project")
                                elif not apath.is_file(): add(out,"FAIL",f"news[{i}] {asset_key} missing: {asset}")
        add(out,"PASS","news structure")
    times=[]
    for key in ("lines_timed","segments"):
        arr=data.get(key)
        if not isinstance(arr,list): continue
        prev=-1.0
        for i,x in enumerate(arr):
            if not isinstance(x,dict) or not finite(x.get("start")) or not finite(x.get("end")): add(out,"FAIL",f"{key}[{i}] start/end invalid"); continue
            a,b=x["start"],x["end"]
            if a<0 or b<=a or a<prev: add(out,"FAIL",f"{key}[{i}] time ordering/overlap invalid")
            prev=a; times.append((a,b,key))
        add(out,"PASS",f"{key} timing scan")
    segs=data.get("segments",[]) if isinstance(data.get("segments"),list) else []
    expected=[]
    for i,s in enumerate(segs):
        if s.get("kind") not in ("opening","news","closing"): add(out,"FAIL",f"segments[{i}] kind invalid")
        if s.get("kind") == "news" and (not isinstance(s.get("index"),int) or s["index"]<0 or s["index"]>=len(data.get("news",[]))): add(out,"FAIL",f"segments[{i}] news index invalid")
        expected.append((s.get("kind"), -1 if s.get("kind") in ("opening","closing") else s.get("index")))
    wanted=[("opening",-1)]+[("news",i) for i in range(len(data.get("news",[])))]+[("closing",-1)]
    if expected != wanted: add(out,"FAIL","segments order/index must be opening, news[0..N], closing")
    for i,line in enumerate(data.get("lines_timed",[]) if isinstance(data.get("lines_timed"),list) else []):
        if not isinstance(line.get("show"),str) or not line.get("show","").strip(): add(out,"FAIL",f"lines_timed[{i}] show must be non-empty")
        if not isinstance(line.get("part"),int) or line["part"]<0 or line["part"]>=len(segs): add(out,"FAIL",f"lines_timed[{i}] part out of range")
        else:
            seg=segs[line["part"]]
            if finite(line.get("start")) and finite(line.get("end")) and (line["start"] < seg.get("start",0)-0.05 or line["end"] > seg.get("end",0)+0.05): add(out,"FAIL",f"lines_timed[{i}] outside segment part {line['part']}")
    if "example.invalid" in json.dumps(data,ensure_ascii=False): add(out,"FAIL","test URL is not allowed in production episode")
    audio = data.get("audio")
    if isinstance(audio,str):
        ap=(root/audio).resolve()
        if root.resolve() not in ap.parents and ap != root.resolve(): add(out,"FAIL","audio path escapes project")
        elif not ap.is_file(): add(out,"FAIL",f"audio missing: {audio}")
        else:
            d=audio_duration(ap)
            if d is None: add(out,"NOT VERIFIED","audio duration unavailable (WAV/ffprobe required)")
            elif abs(d-data.get("seconds",0))<=0.5: add(out,"PASS",f"audio duration {d:.3f}s")
            else: add(out,"FAIL",f"audio duration {d:.3f}s differs from seconds {data.get('seconds')}")
    else: add(out,"FAIL","audio must be a relative path string")
    for a,b,_ in times:
        if b>data.get("seconds",0): add(out,"FAIL","timing exceeds seconds")
    return out

def validate_index(root: Path):
    out=[]; p=root/"episodes.json"
    try: arr=json.loads(p.read_text(encoding="utf-8"))
    except Exception as e: return [result("FAIL",f"episodes.json parse: {e}")]
    if not isinstance(arr,list): return [result("FAIL","episodes.json must be array")]
    seen=set(); prev="9999-99-99"
    for i,row in enumerate(arr):
        if not isinstance(row,dict) or not DATE_RE.fullmatch(str(row.get("date",""))): add(out,"FAIL",f"index row {i} invalid date"); continue
        d=row["date"]
        if d>prev: add(out,"FAIL","episodes.json is not descending")
        prev=d
        langs=[k for k in row if k not in ("date","title","seconds")]
        if not langs and "title" in row: langs=["legacy"]
        for lang in langs:
            if (d,lang) in seen: add(out,"FAIL",f"duplicate registration {d}/{lang}")
            seen.add((d,lang))
    add(out,"PASS","episodes.json structure")
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("episode",nargs="?",help="episode JSON; omit for index only"); ap.add_argument("--root",default="."); ap.add_argument("--all",action="store_true",help="scan episodes/ explicitly"); ap.add_argument("--json",action="store_true"); args=ap.parse_args()
    root=Path(args.root).resolve(); checks=validate_index(root)
    if args.episode: checks += validate_episode(root,Path(args.episode).resolve())
    elif args.all and (root/"episodes.json").exists():
        for p in sorted((root/"episodes").glob("*.json")): checks += validate_episode(root,p)
    overall="FAIL" if any(x["status"]=="FAIL" for x in checks) else ("NOT VERIFIED" if any(x["status"]=="NOT VERIFIED" for x in checks) else "PASS")
    payload={"overall":overall,"checks":checks}
    if args.json: print(json.dumps(payload,ensure_ascii=False,indent=2))
    else:
        print(f"OVERALL: {overall}")
        for x in checks: print(f"[{x['status']}] {x['message']}")
    return 1 if overall=="FAIL" else 0
if __name__=="__main__": sys.exit(main())
