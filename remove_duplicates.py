#!/usr/bin/env python
from storage import *

import sqlite3 as lite
import sys, os
import subprocess
import string
import md5
import traceback

db = Storage(memory=False)


def show_marked_for_removal(sha1, names):
    for d in db.filenames(sha1):
        if d['name'] in names:
            print d, "<- remove"
        else:
            print d

def do_remove(sha1, names):
    print "Removing files:"
    for i in names:
        print "deleting %s" % i
        try:
            os.remove(i)
            db.remove(sha1, i)
        except Exception, e:
            print traceback.format_exc()

def f_spot():
    for row in db.duplicates(): # keys
        sha1 = row['sha1']

        names = []
        mark = False
        for d in db.filenames(sha1):
            name = d['name']
            if 'Photos' in name:
                mark = True
            else:
                names.append(name)

        if not mark:
            continue

        show_marked_for_removal(sha1, names)
        print
        #do_remove(sha1, names)


def dup_1(name):
    return name.endswith("_1.jpg")


def dup_1_do():
    for row in db.duplicates():
        names = []
        mark = False
        for d in db.filenames(row['sha1']):
            if dup_1(d['name']):
                mark = True
                names.append(d['name'])

        if not mark:
            continue

        show_marked_for_removal(row['sha1'], names)
        print

        #do_remove(row['sha1'], names)


def list_duplicates():
    for row in db.duplicates():
        for d in db.filenames(row['sha1']):
            print d
        print

if __name__ == "__main__":
    #f_spot()
    dup_1_do()
    #list_duplicates()
