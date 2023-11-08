# Transcriber

Scrape Web content into markdown. 

## Cases 

- making notes
- bypassing paywalls *(not robust)*
- recovery or migration of a site content where
  - official toolset is broken/lacking
  - server access is restricted as with web hosting platforms

## Install

`pipx install git+https://github.com/danisztls/transcriber`

## Usage

```sh
# Scrape a URL
transcribe -t https://en.wikipedia.org/wiki/Transcription

# Scrape a list of URLS
transcribe -l urls.yml

# Verbose, print to STDOUT
transcribe -v -t <URL>

# Dry run, do not save to disk
transcribe -n -t <URL>
```

## See also

- [autoscraper](https://github.com/alirezamika/autoscraper)
