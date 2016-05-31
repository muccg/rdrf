#!/usr/bin/env python
"""
Validates CDE calculation javascript in registry YAML files.
"""

from __future__ import print_function
import io
import sys
import yaml
from rdrf.utils import check_calculation

yaml.add_constructor(u'tag:yaml.org,2002:str',
                     yaml.constructor.Constructor.construct_python_unicode)

def main():
    for infile in sys.argv[1:]:
        check_file(infile)

def check_file(filename):
    data = yaml.load(io.open(filename, errors="replace"))
    for cde in data.get("cdes") or []:
        calc = cde.get("calculation")
        if calc:
            result = check_calculation(calc)
            for error in filter(None, result.strip().split("\n")):
                print("%s %s: '%s'" % (filename, cde.get("code", ""), error))

if __name__ == '__main__':
    main()
