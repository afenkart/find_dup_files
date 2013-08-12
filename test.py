#!/usr/bin/env python
import sqlite3 as lite
import sys, os
import subprocess
import string

class Storage:
    def __init__(self):
        #self.con = lite.connect('files.db')
        self.con = lite.connect(':memory:')
        #self.con.text_factory = str
        self.create_db()

    def create_db(self):
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Files")
        cur.execute("CREATE TABLE Files(SHA1 TEXT PRIMARY KEY, Name TEXT)")
        cur.execute("CREATE TABLE Duplicates(Id INT PRIMARY KEY, SHA1 TEXT, Name TEXT)")
        self.con.commit();

    def is_dup_of(self, sha1, name):
        cur = self.con.cursor()
        rows = cur.execute("SELECT Name FROM Files WHERE SHA1=?", (sha1,))
        primary = rows.fetchone()
        if not primary:
            return None

        print "%s %s(dup) %s" % (primary[0], name, sha1)
        return primary;

    def add_dup(self, sha1, dup, primary):
        cur = self.con.cursor()
        cur.execute("INSERT INTO Duplicates(SHA1, Name) VALUES(?, ?)", (sha1, dup))
        pass

    def add_file(self, sha1, name):
        prime = self.is_dup_of(sha1, name)
        if (prime):
            self.add_dup(sha1, name, prime)
            return
        try:
            cur = self.con.cursor()
            cur.execute("INSERT INTO Files VALUES(?, ?)", (sha1, name))
            self.con.commit();
        except lite.Error, e:
            print e
            print "Error %s: name: %s" % (e.args[0], name)
            self.con.rollback()

    def get_duplicates(self):
            cur = self.con.cursor()
            rows = cur.execute("SELECT * FROM Duplicates")
            return rows.fetchall()


db = Storage()


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

for f in db.get_duplicates():
    print f;
