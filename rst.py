#!/usr/bin/python

import json
import sys
import itertools

def restify(nb):
    out = []
    for w in nb['worksheets']:
        for c in w['cells'][1:]:
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
                    if line == '##':
                        continue
                    if line.startswith('!['):
                        cap, link = line.split('](',1)
                        cap = cap[2:]
                        link = link[:-1]
                        out.extend(['.. image:: ' + link, '   :alt: ' + cap])
                        continue

                    if not line.startswith('### '):
                        out.append(line.replace('`', '``'))
                        continue

                    line = line[4:]
                    target = '-'.join(''.join(chars)
                        for k, chars in itertools.groupby(line.lower(),
                        lambda x: 'a' <= x <= 'z') if k)
                    out.extend(['.. _' + target + ':', ''])
                    out.append('`' + line + '`__')
                    out.append('-' * (len(line) + 4))
                    out.extend(['', '__ ' + target + '_'])

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
