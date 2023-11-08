#!/usr/bin/env python

"""
Scrape Web content into markdown
"""

__author__  = "Daniel Souza <me@posix.dev.br>"
__license__ = "GPLv3"

import argparse, re, uuid, os, pathlib, time

import urllib3
# https://urllib3.readthedocs.io/en/stable/

from markdownify import MarkdownConverter
# https://github.com/matthewwithanm/python-markdownify/

from bs4 import BeautifulSoup
# https://beautiful-soup-4.readthedocs.io/en/latest/

import yaml
# https://github.com/yaml/pyyaml

from rich import print
# https://github.com/Textualize/rich
# https://github.com/Textualize/rich/blob/master/rich/_emoji_codes.py

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', dest='target', help="URL to scrap")
parser.add_argument('-l', '--list', dest='list', help="YAML list of URLs to scrap")
parser.add_argument('-n', '--dry-run', dest='dry_run', default=False, help="dry run mode (don't save)", action="store_true")
parser.add_argument('-v', '--verbose', dest='verbose', default=False, help="verbose mode (print to stdout)", action="store_true")
parser.add_argument('-d', '--debug', dest='debug', default=False, help="debug mode", action="store_true")
args = parser.parse_args()

output_path = str(pathlib.Path().absolute()) + '/output'

http = urllib3.PoolManager()

"""Traverse a path and create nonexistent dirs"""
def mkdir(path):
    dirs = path.strip('/').split('/')
    path = ''

    for dir in dirs:
        path += '/' + dir 
        if not os.path.exists(path):
            os.mkdir(path)

"""Make a GET request and return HTML excerpt"""
def get_html(url):
    try:
        if re.match("https?://.*", url):
            # TODO: Use a custom request header
            response = http.request("GET", url)
            html = BeautifulSoup(response.data, 'html.parser')

        elif re.match("file://.*", url): 
            path = re.sub("^file://", "", url)

            with open(path, 'r') as file:
                data = file.read()
                html = BeautifulSoup(data, 'html.parser')
            
    except Exception as error:
        print(f"[red]ERROR:[/red] {error}")
        data = "<strong>Bad boy, no page for you.</strong>"
        data += f"\n<p>{error}</p>"

        if args.debug == True:
            print("\n[deep_pink3]DEBUG: Failed to get HTML[/deep_pink3]\n")

        return BeautifulSoup(data, "html.parser")

    html(html.prettify())

    for tag in ['article', 'main', 'body']:
        content = html.find(tag)
        if content:
            if args.debug == True:
                print("\n[deep_pink3]DEBUG: Printing HTML content[/deep_pink3]\n")
                print(content)

            return content

"""Make a GET request and return file data"""
def get_file(url):
    try:
        response = http.request("GET", url)
        data = response.data

    except Exception as e:
        data = None
    
    return data 

"""Filter HTML to remove non-content"""
def filter_html(html):
    tags = [html.style, html.script, html.iframe]

    for tag in tags:
        if tag:
            tag.decompose()

    # TODO: Improve performance
    for tag in html.find_all():
        del tag['style']

    return html

"""Parse HTML into Markdown"""
def parse_html(html):
    mkd = MarkdownConverter(heading_style="ATX", newline_style="backslash").convert_soup(html)

    if args.debug == True:
        print("\n[deep_pink3]DEBUG: Printing Markdown[/deep_pink3]\n")
        print(mkd)

    return mkd


"""Filter Markdown to remove undesirables"""
def filter_mkdown(mkdown):
    mkdown = mkdown.strip() # remove leading and trailing lines
    # mkdown = re.sub('\s+\n', '\n', mkdown) # remove whitespace from empty lines

    # TODO: Make some filters modular

    # remove link obfuscators
    google_pattern = re.compile(r"\(https://www.google.com/url\?q=(https?://.*?)&.*\)")
    mkdown = re.sub(google_pattern, r"(\1)", mkdown)

    return mkdown

"""Generate file path from URL"""
def gen_path(url):
    # parse url
    tree = re.match("(https?|file)://(.*)", url).group(2).split('/')

    # http(s)://
    if re.match("https?://.*", url):
        
        # remove trailing slash
        if tree[-1] == '':
            tree.pop()

        # construct path
        path = tree[0]

    # file://
    elif re.match("file://.*", url): 
        path = "local/" + tree[-2]
    
    path = output_path + '/' + path + '/'
    mkdir(path)

    file = re.sub("\..*", "", tree[-1]) + '.md' # substitute extension

    return [path, file]

"""Save data to disk"""
def save_file(path, data, overwrite=False):
    if not os.path.exists(path) or overwrite:
        with open(path, 'w') as file:
            file.write(data)
    
    else:
        print(f"[gray]{path}[/gray] [yellow]already exists![/yellow]")

"""Download assets referenced in the Markdown content and rewrite URLs to point to local files"""
def get_assets(path, mkdown):
    # find in content all URLs that ends with a extension

    # TODO: Add support for fetching local files?

    # TODO: Improve this
    assets = re.findall("\((http.*?\.jpg|JPG|jpeg|JPEG|png|PNG|webp|WEBP|avif|AVIF|pdf|PDF)\)", mkdown)
    
    # pop what's not an HTML page
    # is_html = re.compile("^.*\.(html|htm)$")
    # for url in enumerate(assets):
    #     if is_html.match(url[1]):
    #         assets.pop(url[0])

    # get assets
    for url in assets:
        print(f"\n:paperclip: [gray]{url}[/gray]")
        data = get_file(url)
        file = re.match("^.*\/(.*?)$", url).group(1)

        if data:
            save_file(path + file, data)
            mkdown = mkdown.replace(url, '../' + file)
            
    return mkdown

"""Measure execution time of function"""
class chronometer:
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            print("[green]%s seconds[/green]" % str(round(end - start, 2)))
            
            return result
        return wrapper

"""Scrape URL and save Makdown content to disk"""
@chronometer()
def scrape(url):
    print(f"\n:page_facing_up: [purple]{url}[/purple]")
    path = gen_path(url)
    html = get_html(url)
    html = filter_html(html)
    mkdown = parse_html(html)
    mkdown = filter_mkdown(mkdown)
    
    if args.verbose == True:
        print(mkdown)

    if args.dry_run == False:
        mkdown = get_assets(path[0], mkdown)
        save_file(path[0] + path[1], mkdown, True)

def main():
    print(":spider: scraping...")
    if args.target:
        scrape(args.target)

    if args.list: 
        with open(args.list, 'r') as file:
            urls = yaml.safe_load(file)

        for url in urls:
          scrape(url)
   
    if not args.target and not args.list:
        print("[red]No URL to scrape. Please input an URL or Yaml list.[/red]")
