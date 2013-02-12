#!/usr/bin/python

import json
import sys

def restify(nb):
    out = []
    for w in nb['worksheets']:
        for c in w['cells']:
            if c['cell_type'] == 'code':
                out.extend(['', '.. sourcecode:: python', ''])
                out.extend('    ' + line for line in c['input'])
                out.extend(['', '::', ''])
                for o in c['outputs']:
                    if 'text' in o:
                        out.extend('    ' + line for line in o['text'])
                    elif 'traceback' in o:
                        for line in o['traceback']:
                            uf = unfunk(line)
                            out.extend('    ' + l for l in uf.split('\n'))
                if out[-2:] == ['::', '']:
                    del out[-2:]
            elif c['cell_type'] == 'markdown':
                out.append('')
                for line in c['source']:
                    if line == '-----':
                        return out
                    out.append(line.replace('`', '``'))
                if out[-1] and out[-1][-1] == ':':
                    out[-1] = out[-1][:-1] + ': '

def unfunk(s):
    f = not_funk()
    f.next()
    return ''.join(c for c in s if f.send(c))

def not_funk():
    nf = True
    while True:
        while True:
            c = yield nf
            nf = True
            if c == u'\u001b':
                break
        nf = False
        while True:
            c = yield nf
            if 'a' <= c <= 'z':
                break

with open(sys.argv[1]) as f:
    nb = json.load(f)

with open(sys.argv[2], 'w') as f:
    for line in restify(nb):
        f.write(line.encode('utf-8') + '\n')
