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

# Scrape a list of URLS
transcribe -l urls.yml

# Verbose, print content to STDOUT
transcribe -v -t <URL>

# CLI mode, only print content to STDOUT
transcribe -c -t <URL>
```
