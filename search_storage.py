#!/usr/bin/env python
from storage import *

import sqlite3 as lite
import sys, os, stat
import socket
import subprocess
import string
import md5
import traceback
import socket


db = Storage(memory=False)
db.recreate()

class FindFiles:

    def sha1(self, name):
        ret = subprocess.check_output(["/usr/bin/sha1sum", name],
                                     stderr=subprocess.STDOUT)
        return ret.split()[0];


    def visit(self, path):
        problem_files = []
        for root, dirs, files in os.walk(path):
            if '.git' in dirs:
                dirs.remove('.git')
            if '.svn' in dirs:
                dirs.remove('.svn')
            for f in files:
                full = os.path.join(root, f)
                if os.path.islink(full):
                    #print "ignore link %s" % full
                    continue
                try:
                    sha1 = self.sha1(full)
                    db.add_file(sha1, full)
                except subprocess.CalledProcessError, e:
                    mode = os.stat(full).st_mode
                    if stat.S_ISSOCK(mode):
                        print "ignore sock", full
                        continue

                    print "problem file", full
                    problem_files.append(full)

find = FindFiles()

def unit_test():
    find.sha1('/etc/passwd')
    try:
        find.sha1('000_unit_test_not_exist')
    except subprocess.CalledProcessError, e:
        print traceback.format_exc()

    try:
        os.unlink('test-files/test-socket')
    except Exception:
        pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind('test-files/test-socket')
    find.visit('./test-files')
    sock.close()
    os.unlink('test-files/test-socket')

unit_test()
#sys.exit(-1)


problem_files = find.visit('/home/afenkart')


print "\nduplicate keys:"
for f in db.duplicates():
    sha1 = f['sha1']
    print sha1
    for g in db.filenames(sha1):
        print "\t", g

print "\nproblem files:"
for f in problem_files:
    print f


#if __name__ == "__main__"
