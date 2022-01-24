#!/usr/bin/env python

"""
Scrape URL content to Markdown
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

# generate output dir
def gen_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)

outdir = str(pathlib.Path().absolute()) + '/out'
gen_dir(outdir)

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', dest='target', help="URL to scrap")
parser.add_argument('-l', '--list', dest='list', help="YAML list of URLs to scrap")
parser.add_argument('-n', '--dry-run', dest='dry_run', default=False, help="dry run mode (don't save)", action="store_true")
parser.add_argument('-v', '--verbose', dest='verbose', default=False, help="verbose mode (print to stdout)", action="store_true")
args = parser.parse_args()

"""Make a GET request and return HTML excerpt"""
http = urllib3.PoolManager()
def get_html(url):
    # TODO: Use a custom request header
    response = http.request("GET", url)
    if response.status == 200:
        html = BeautifulSoup(response.data, 'html.parser')
        html(html.prettify())

        for tag in ['article', 'main', 'body']:
            article = html.find(tag)
            if article:
                break
            
        return article 


"""Parse HTML into Markdown"""
def parse_html(html):
    content = MarkdownConverter().convert_soup(html)
    content = content.strip() # remove leading and trailing lines
    # content = re.sub('\s+\n', '\n', content) # remove whitespace from empty lines
    return content

"""Generate file path from URL"""
def gen_path(url):
    # parse url
    tree = re.match("http[s]://(.*)", url).group(1).split('/')
    dir = tree[0]

    # gen uuid if no path 
    if len(tree) > 0:
        file = tree[-1]
        file = re.sub("\..*", "", file) # remove extension
    else:
        file = str(uuid.uuid4())
    
    dir_path = outdir + '/' + dir
    gen_dir(dir_path)

    file_path = dir_path + '/' + file + '.md' 
    return file_path

"""Save content to disk"""
def save_file(url, content):
    with open(gen_path(url), 'w') as file:
        print(content, file=file)

"""Measure execution time of function"""
class chronometer:
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            print("%s seconds" % str(round(end - start, 2)))
            
            return result
        return wrapper

"""Scrape URL and save content to disk as Markdown"""
@chronometer()
def scrape(url):
    # TODO: Scrape images and rewrite URL 
    print(f"\n{url}")

    html = get_html(url)

    if html:
        content = parse_html(html)

        if args.verbose == True:
            print(content)

        if args.dry_run == False:
            save_file(url, content)

if args.target:
      print("Scraping URL...\n")
      scrape(args.target)

if args.list: 
    with open(args.list, 'r') as file:
        urls = yaml.safe_load(file)

    for url in urls:
      print("Scraping list of URLs...\n")
      scrape(url)

if not args.target and not args.list:
    print("No URL to scrape. Please input an URL or Yaml list.")
