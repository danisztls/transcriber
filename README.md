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

```sh
# Scrape a URL
transcribe -t https://en.wikipedia.org/wiki/Transcription

# Scrape multiple URLs (repeat -t, or point -t at a YAML list)
transcribe -t <URL1> -t <URL2>
transcribe -t urls.yml

# Verbose, also print content to STDOUT
transcribe -v -t <URL>

# CLI mode, only print content to STDOUT (diagnostics go to STDERR)
transcribe -c -t <URL>

# Also download images/videos/audio locally and rewrite refs to ./filename
transcribe --scrape -t <URL>

# Tune concurrency and politeness
transcribe -w 8 --delay 0.5 -t urls.yml
```

### Flags

| Flag | Default | What it does |
|---|---|---|
| `-t`, `--target` | — | URL to scrape, or path to a YAML file with a top-level list of URLs. Repeatable. |
| `-c`, `--cli-mode` | off | Only the markdown content goes to STDOUT; diagnostics go to STDERR. |
| `-v`, `--verbose` | off | Print markdown content in addition to writing it to disk. |
| `-d`, `--debug` | off | Dump intermediate `.raw.html`, `.content.html`, `.filtered.html`, `.raw.md` alongside the output. |
| `--scrape` | off | Download linked images/videos/audio next to the markdown and rewrite refs to `./filename`. Without it, refs stay as absolute original URLs. |
| `-w`, `--workers` | 4 | Max concurrent HTTP requests (pages + assets share the same pool). |
| `--delay` | 0 | Seconds each request slot waits after a response. Combined with `--workers` this caps the rate at workers/delay requests per second. |
