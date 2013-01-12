#!/usr/bin/python

import json
import sys

with open("Iterables, Iterators, Generators.ipynb") as f:
    nb = json.load(f)

for w in nb['worksheets']:
    for c in w['cells']:
        if c['cell_type'] != 'code':
            continue
        if c['input'][:1] != ['##']:
            continue
        for line in c['input']:
            print line
