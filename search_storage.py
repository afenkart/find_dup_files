#!/usr/bin/env python
import sqlite3 as lite
import sys, os
import subprocess
import string
from storage import *


db = Storage(memory=False)
db.recreate()

class FindFiles:

    def sha1(self, name):
        ret = subprocess.check_output(["/usr/bin/sha1sum", name],
                                     stderr=subprocess.STDOUT)
        return ret.split()[0];


    def visit(self):
        for root, dirs, files in os.walk("/home/afenkart"):
            if '.git' in dirs:
                dirs.remove('.git')
            if '.svn' in dirs:
                dirs.remove('.svn')
            for f in files:
                full = os.path.join(root, f)
                if os.path.islink(full):
                    print "link %s" % full
                    continue
                sha1 = self.sha1(full)
                db.add_file(sha1, full)


find = FindFiles()
find.visit()

for f in db.duplicates():
    print f;
