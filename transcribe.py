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

# TODO: Make this an argument
# TODO: Strip and readd '/' to avoid confusions
root_path = str(pathlib.Path().absolute()) + '/out'

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', dest='target', help="URL to scrap")
parser.add_argument('-l', '--list', dest='list', help="YAML list of URLs to scrap")
parser.add_argument('-n', '--dry-run', dest='dry_run', default=False, help="dry run mode (don't save)", action="store_true")
parser.add_argument('-v', '--verbose', dest='verbose', default=False, help="verbose mode (print to stdout)", action="store_true")
args = parser.parse_args()

# TODO: Modify dry-run and verbose as to make more sense

"""Traverse a path and create nonexistent dirs"""
def mkdir(path):
    dirs = path.strip('/').split('/')
    path = ''

    for dir in dirs:
        path += '/' + dir 
        if not os.path.exists(path):
            os.mkdir(path)

"""Make a GET request and return HTML excerpt"""
http = urllib3.PoolManager()
def get_html(url):
    # TODO: Use a custom request header
    
    try:
        response = http.request("GET", url)

        html = BeautifulSoup(response.data, 'html.parser')
        html(html.prettify())

        for tag in ['article', 'main', 'body']:
            article = html.find(tag)
            if article:
                break

    except Exception as e:
        bucket = "<strong>Bad boy, no page for you.</strong>"
        bucket += f"\n<p>{e}</p>"
        article = BeautifulSoup(bucket, "html.parser")
    
    return article 

"""Parse HTML into Markdown"""
def parse_html(html):
    content = MarkdownConverter(heading_style="ATX", newline_style="backslash").convert_soup(html)
    content = content.strip() # remove leading and trailing lines
    # content = re.sub('\s+\n', '\n', content) # remove whitespace from empty lines
    return content

"""Generate file path from URL"""
def gen_path(url):
    # parse url
    tree = re.match("https?://(.*)", url).group(1).split('/')
    
    # remove trailing slash
    if tree[-1] == '':
        tree.pop()

    # construct path
    path = tree[0]

    if len(tree) > 0:
        file = tree[-1]
        file = re.sub("\..*", "", file) # remove extension

    # gen uuid if no name 
    else:
        file = str(uuid.uuid4())
    
    path = root_path + '/' + path + '/'
    mkdir(path)

    file = file + '.md' 
    
    return [path, file]

"""Save content to disk"""
def save_file(path, data):
    # TODO: Check if file does not already exist
    with open(path, 'w') as file:
        print(data, file=file)
        
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
    print(f"\n{url}")
    path = gen_path(url)
    html = get_html(url)
    content = parse_html(html)
    
    if args.verbose == True:
        print(content)

    if args.dry_run == False:
        save_file(path[0] + path[1], content)

def main():
    if args.target:
          print("Scraping URL...")
          scrape(args.target)

    if args.list: 
        with open(args.list, 'r') as file:
            urls = yaml.safe_load(file)

        for url in urls:
          print("Scraping list of URLs...")
          scrape(url)

    if not args.target and not args.list:
        print("No URL to scrape. Please input an URL or Yaml list.")

main()
