#!/usr/bin/env python3
"""39ra Garden Radio: safe, on-demand episode draft/scaffolding helper.

This helper never registers an episode, commits code, pushes, or publishes.
It reuses the project's existing task-005 validator and preview tools.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

EP_RE = re.compile(r"^EP\d{3,}$")


def safe_date(value: str) -> str:
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO date: {value}") from exc
    if result.isoformat() != value:
        raise argparse.ArgumentTypeError(f"Date must be YYYY-MM-DD: {value}")
    return value


def safe_ep(value: str) -> str:
    value = value.upper()
    if not EP_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("Episode ID must be EP002, EP003, ...")
    return value


def ensure_project(root: Path) -> None:
    if not (root / "episodes.json").is_file():
        raise SystemExit(f"Project root is missing episodes.json: {root}")
    if not (root / "tools" / "validate_episode.py").is_file():
        raise SystemExit("Project root is missing tools/validate_episode.py")


def draft_dir(root: Path, episode: str, day: str) -> Path:
    return root / "editorial" / "work" / f"{episode}-{day}"


def draft_json(root: Path, episode: str, day: str) -> Path:
    return draft_dir(root, episode, day) / f"{day}-ja.json"


def registered(root: Path, day: str) -> bool:
    try:
        rows = json.loads((root / "episodes.json").read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Cannot read episodes.json: {exc}") from exc
    if not isinstance(rows, list):
        raise SystemExit("episodes.json must be an array")
    return any(isinstance(row, dict) and row.get("date") == day and ("ja" in row or "title" in row) for row in rows)


def new_episode(root: Path, episode: str, day: str) -> int:
    ensure_project(root)
    if registered(root, day) or (root / "episodes" / f"{day}-ja.json").exists():
        print(f"REFUSED: {day}/ja is already present in the published index or episodes directory")
        return 2
    target = draft_dir(root, episode, day)
    if target.exists():
        print(f"REFUSED: draft already exists: {target}")
        return 2
    work_root = target.parent
    work_root.mkdir(parents=True, exist_ok=True)
    ignore = work_root / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")
    target.mkdir(parents=True)
    data = {
        "format": "monoradio/news-1",
        "date": day,
        "lang": "ja",
        "seconds": 0,
        "title": "",
        "audio": f"audio/{day}-ja.mp3",
        "made_at": "",
        "opening": [],
        "news": [],
        "closing": [],
        "lines_timed": [],
        "segments": [],
    }
    draft_json(root, episode, day).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "script.md").write_text(
        f"# {episode} / {day} 台本\n\n状態: 草稿（未承認）\n\n"
        "| 発話ID | 章 | 読み上げ say | 表示 show | 一次出典ID |\n"
        "|---|---|---|---|---|\n"
        "| opening-01 | opening |  |  |  |\n"
        "| news-01-01 | news |  |  |  |\n"
        "| closing-01 | closing |  |  |  |\n\n"
        "台本確定後に音声を制作します。未確認の日時・事実を補完しないでください。\n",
        encoding="utf-8",
    )
    with (target / "sources.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "category", "topic", "source_url", "source_title", "published_at", "checked_at", "event_timezone", "rights_evidence", "adoption", "notes"])
    (target / "QA.md").write_text(
        f"# {episode} / {day} 出稿チェック\n\n"
        "- [ ] 各話題の一次情報URL・発表日・確認日が揃っている\n"
        "- [ ] イベントの開催日時・締切・タイムゾーン・応募条件を確認した\n"
        "- [ ] 台本をユーザーが確認・承認した\n"
        "- [ ] 元の音声ファイルを保管し、統合MP3/WAVの実尺を確認した\n"
        "- [ ] 原稿と音声の発話内容を照合した\n"
        "- [ ] 字幕の開始時刻・章・表示内容を聴取確認した\n"
        "- [ ] reviewed字幕JSONを最終データへ反映した\n"
        "- [ ] サムネイルごとに再利用許可・引用根拠を確認した（未確認なら画像なし）\n"
        "- [ ] validatorにFAILとNOT VERIFIEDが残っていない\n"
        "- [ ] 非公開プレビューのPC 1440pxで再生・シーク・カードを確認した\n"
        "- [ ] モバイル390pxと375pxで横スクロール・字幕の重なりを確認した\n"
        "- [ ] ?embed=1 / 章移動 / 終了部分 / 外部リンクを確認した\n"
        "- [ ] ユーザーが番組登録を承認した\n"
        "- [ ] ユーザーが一般公開を別途承認した\n"
        "- [ ] 公開後に音声・字幕・ニュース画像とリンク・旧回再生を確認した\n\n"
        "未確認の項目を自動でチェック済みにしてはいけません。\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        f"# {episode}（{day}）制作ワークスペース\n\n"
        f"JSON草稿: `{day}-ja.json`\n"
        f"最終音声予定: `audio/{day}-ja.mp3`（プロジェクトルートからの相対パス）\n\n"
        "ここにある草稿は未公開です。`episodes.json`へは自動登録されません。\n"
        "音声をプロジェクトのaudio/へ配置してからcheck/previewします。\n"
        "公開用ファイルにeditorial/workを含めないこと。\n",
        encoding="utf-8",
    )
    print(f"CREATED DRAFT: {target}\nNO PUBLIC DATA WAS CHANGED.")
    return 0


def qa_summary(target: Path) -> None:
    qa = target / "QA.md"
    if qa.exists():
        text = qa.read_text(encoding="utf-8")
        checked = len(re.findall(r"^- \[[xX]\]", text, re.M))
        unchecked = len(re.findall(r"^- \[ \]", text, re.M))
        print(f"HUMAN QA: {checked} complete / {unchecked} pending (manual verification required)")


def check_episode(root: Path, episode: str, day: str) -> int:
    ensure_project(root)
    candidate = draft_json(root, episode, day)
    if not candidate.is_file():
        print(f"MISSING DRAFT: {candidate}")
        return 2
    code = subprocess.run([sys.executable, str(root / "tools" / "validate_episode.py"), str(candidate), "--root", str(root)], cwd=root, check=False).returncode
    qa_summary(candidate.parent)
    print("Static checks are NOT proof of news truth, image rights, or human listening approval.")
    return code


def preview_episode(root: Path, episode: str, day: str) -> int:
    ensure_project(root)
    candidate = draft_json(root, episode, day)
    if not candidate.is_file():
        print(f"MISSING DRAFT: {candidate}")
        return 2
    preview_script = root / "tools" / "preview_episode.py"
    if not preview_script.is_file():
        print(f"MISSING TOOL: {preview_script}")
        return 2
    # A fresh sibling folder avoids modifying source or deleting previous previews.
    out = root.parent / "radio-local-previews" / f"{episode}-{day}-{uuid.uuid4().hex[:8]}"
    out.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(preview_script), str(candidate), "--project", str(root), "--output", str(out), "--serve"]
    print("RUNNING ISOLATED PREVIEW (local only):", " ".join(command))
    code = subprocess.run(command, cwd=root, check=False).returncode
    if code == 0:
        print("\nNEXT: Open a PowerShell window and run:")
        print(f'py -3 -m http.server 8780 --bind 127.0.0.1 --directory "{out}"')
        print("Then open: http://127.0.0.1:8780/")
        print("Press Ctrl+C in PowerShell to stop the preview server.")
    return code


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except OSError:
            pass
    ap = argparse.ArgumentParser(description="39ra Radio episode draft helper; never publishes")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="path to radio repo root")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("new", "check", "preview"):
        p = sub.add_parser(name)
        p.add_argument("episode", type=safe_ep, help="EP002, EP003, ...")
        p.add_argument("date", type=safe_date, help="YYYY-MM-DD")
    args = ap.parse_args()
    root = args.root.resolve()
    return {"new": new_episode, "check": check_episode, "preview": preview_episode}[args.command](root, args.episode, args.date)


if __name__ == "__main__":
    raise SystemExit(main())
