#!/usr/bin/env python
from storage import *

import sqlite3 as lite
import sys, os
import subprocess
import string
import md5

db = Storage(memory=False)

def dup_1(name):
    return name.endswith("-1.jpg")

for row in db.duplicates():
    names = []
    mark = False
    for d in db.filenames(row['sha1']):
        if dup_1(d['name']):
            mark = True
            names.append(d['name'])

    if not mark:
        continue

    for d in db.filenames(row['sha1']):
        if d['name'] in names:
            print d, "<- remove"
        else:
            print d

    continue

    print "Really remove"
    for i in names:
        print "deleting %s" % i
        #os.remove(i)
        db.remove(row['sha1'], i)

