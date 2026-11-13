# EP002以降の制作・公開運用

この手順は、39ra Garden Radioを不定期に制作するための補助運用です。`new` は未公開の草稿ワークスペースだけを作成し、`episodes.json`や公開済みEP001を変更しません。

## Windowsでの開始

リポジトリのフォルダを開き、次を実行します。

```powershell
.\RADIO_EPISODE.cmd new EP002 2026-11-20
```

日付は実際の放送日に置き換えてください。同じ日付の公開回や同じ草稿がある場合は安全のため拒否します。

草稿JSON、台本、出典台帳、QAチェックリストを埋め、音声をプロジェクトの `audio/YYYY-MM-DD-ja.mp3` に置いた後、静的検証を実行します。

```powershell
.\RADIO_EPISODE.cmd check EP002 2026-11-20
.\RADIO_EPISODE.cmd preview EP002 2026-11-20
```

`preview` は別フォルダへコピーしたローカルプレビューだけを作ります。表示確認は `file://` ではなく、表示されたコマンドでlocalhost HTTPサーバーを起動して行います。

## 字幕レビュー

`tools/subtitle_editor.html` をブラウザで開き、JSONファイルと統合音声をそれぞれ選択します。外部通信は行わず、選択した `monoradio/news-1` JSON全体を保持したまま `lines_timed` の開始・終了・表示文・partを編集できます。検証後、`YYYY-MM-DD-ja.reviewed.json` として保存します。

字幕の確認済みチェックは人間の試聴記録を置き換えません。権利、出典、音声との一致、390/375px、`?embed=1` はQAで別途確認してください。

## 公開ゲート

台本承認、音声確認、reviewed字幕確認、画像の利用根拠確認、validator PASS、非公開プレビュー、ユーザーによる登録承認、一般公開承認を別々に記録します。承認前に `episodes.json` や本番 `episodes/` を更新しません。

公開時は必要な差分だけを通常commit/pushします。`tools/publish.sh` のforce pushは使用しません。`editorial/work`、内部レポート、未許諾画像、秘密情報は公開領域へ含めません。
