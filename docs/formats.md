# Episode data format

Episodes use `monoradio/news-1`. An episode JSON contains `opening`, `news`, `closing`, `lines_timed`, and `segments`. Each timed cue has numeric `start`/`end`, non-empty `show`, and a zero-based `part` pointing to its segment.

`news[].link.image` is optional and must be a repository-relative path with a documented public-use basis. If rights are not confirmed, omit the image and keep the article link.

`episodes.json` is the public index. Drafts live under `editorial/work/` and are never registered automatically.
