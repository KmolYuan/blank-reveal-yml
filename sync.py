# -*- coding: utf-8 -*-

from os import remove
from os.path import join
from distutils.dir_util import copy_tree, mkpath
from glob import glob
from tempfile import TemporaryDirectory
from tarfile import open as tgz
from yaml import safe_load
from json import dump
from reveal_yaml.utility import dl


def reveal_cdn(ver: str) -> None:
    """Download Reveal.js from NPMjs."""
    with TemporaryDirectory() as path:
        dl(f"https://registry.npmjs.org/reveal.js/-/reveal.js-{ver}.tgz",
           join(path, 'reveal.tgz'))
        with tgz(join(path, 'reveal.tgz'), 'r:gz') as f:
            f.extractall(path)
        for f in glob(join(path, 'package', '**', '*.esm.js*'), recursive=True):
            remove(f)
        for f in glob(join(path, 'package', '**', 'plugin.js'), recursive=True):
            remove(f)
        copy_tree(join(path, 'package', 'dist'), "reveal_yaml/static/reveal.js")
        copy_tree(join(path, 'package', 'plugin'), "reveal_yaml/static/plugin")


def cdn(url: str, to: str) -> None:
    """Download from CDNjs."""
    to += url.rsplit('/', maxsplit=1)[-1]
    dl("https://cdnjs.cloudflare.com/ajax/libs/" + url, to)


def main():
    reveal_cdn("4.0.2")
    path = "reveal_yaml/static/js/"
    mkpath(path)
    cdn("jquery/3.5.1/jquery.min.js", path)
    path = "reveal_yaml/static/ace/"
    mkpath(path)
    cdn("ace/1.4.12/ace.min.js", path)
    cdn("ace/1.4.12/ext-searchbox.min.js", path)
    cdn("ace/1.4.12/ext-whitespace.min.js", path)
    cdn("ace/1.4.12/ext-language_tools.min.js", path)
    cdn("ace/1.4.12/mode-yaml.min.js", path)
    cdn("ace/1.4.12/theme-chrome.min.js", path)
    cdn("ace/1.4.12/theme-monokai.min.js", path)
    cdn("js-yaml/3.14.0/js-yaml.min.js", path)
    # Generate JSON schema
    with open("reveal_yaml/schema.yaml", 'r') as f:
        data = safe_load(f)
    with open("reveal_yaml/schema.json", 'w+') as f:
        dump(data, f, indent=4)


if __name__ == '__main__':
    main()
