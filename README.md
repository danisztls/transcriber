# Transcriber

Scrape Web content into markdown. 

## Cases 

- making notes
- bypassing paywalls *(not robust)*
- recovery or migration of a site content where
  - official toolset is broken/lacking
  - server access is restricted as with web hosting platforms

## Install

```sh
uv tool install git+https://github.com/danisztls/transcriber
```

Or run from a clone without installing:

```sh
git clone https://github.com/danisztls/transcriber
cd transcriber
uv sync
uv run transcribe -t <URL>
```

## Usage

By default the markdown goes to STDOUT, so the tool composes with pipes and
redirects. Diagnostics (URLs, timing) go to STDERR and don't pollute the pipe.

```sh
# Scrape a URL, print to STDOUT
transcribe -t https://en.wikipedia.org/wiki/Transcription

# Redirect or pipe the markdown
transcribe -t <URL> > note.md
transcribe -t <URL> | less

# Save to disk under output/<host>/<path>/index.md instead of printing
transcribe -w -t <URL>

# Scrape multiple URLs (repeat -t, or point -t at a YAML list)
transcribe -t <URL1> -t <URL2>
transcribe -t urls.yml

# Also download images/videos/audio locally and rewrite refs to ./filename
transcribe --scrape -w -t <URL>

# Tune concurrency and politeness
transcribe -j 8 --delay 0.5 -w -t urls.yml
```

### Flags

| Flag | Default | What it does |
|---|---|---|
| `-t`, `--target` | — | URL to scrape, or path to a YAML file with a top-level list of URLs. Repeatable. |
| `-w`, `--write` | off | Save the markdown to disk instead of printing to STDOUT. |
| `-d`, `--debug` | off | Dump intermediate `.raw.html`, `.content.html`, `.filtered.html`, `.raw.md` alongside the output (implies `--write`). |
| `--scrape` | off | Download linked images/videos/audio next to the markdown and rewrite refs to `./filename`. Without it, refs stay as absolute original URLs. |
| `-j`, `--workers` | 4 | Max concurrent HTTP requests (pages + assets share the same pool). |
| `--delay` | 0 | Seconds each request slot waits after a response. Combined with `--workers` this caps the rate at workers/delay requests per second. |
