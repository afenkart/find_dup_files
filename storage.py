#!/usr/bin/env python
import sqlite3 as lite
import sys, os
import subprocess
import string

class Storage:
    def __init__(self):
        #self.con = lite.connect('files.db')
        self.con = lite.connect(':memory:')
        self.con.row_factory = lite.Row
        #self.con.text_factory = str
        self.create_db()
        self.sha1_hash = {}
        self.files = []

    def create_db(self):
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Files")
        cur.execute("CREATE TABLE Files(SHA1 TEXT, Name TEXT)")
        self.con.commit();


    def add_file(self, sha1, name):
        try:
            cur = self.con.cursor()
            cur.execute("INSERT INTO Files VALUES(?, ?)", (sha1, name))
            self.con.commit();
        except lite.Error, e:
            print "Error %s: name: %s" % (e.args[0], name)
            self.con.rollback()

    def all_rows(self):
        cur = self.con.cursor()
        return cur.execute("SELECT * FROM Files")

    def dump(self):
        for line in self.con.iterdump():
            print line

    def duplicates(self):
        cur = self.con.cursor()
        return cur.execute("SELECT COUNT(*), sha1, Name FROM Files GROUP BY \
                           sha1 HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC")

    def filenames(self, sha1):
        cur = self.con.cursor()
        return cur.execute("SELECT sha1, Name FROM Files")

    def __repr__(self):
        ret = ""
        for (sha1, name) in self.files:
            ret += sha1 + "|" + name + "\n"

        for (sha1) in self.sha1_hash:
            ret += sha1 + "|%d\n" % self.sha1_hash[sha1]

        return ret

def build_test_corpus(db):
    print "test_corpus"
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', 'ida_-_Vylet_na_prehradu/IMAG0167.jpg')
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', 'et_na_prehradu/IM.jpg')
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', '_na_prehradu/IM.jpg')
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd565', 'erehradu/IM.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea2','cii_Empik_hleda_Foxika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea2','i_Empik_hleda_Foxika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea5','i_E_Foxika/P1080538.jpg')


if __name__ == "__main__":
    db = Storage()
    build_test_corpus(db)
    #print db
    #print len(db.all_rows())

    print "\ncollisions"
    for row in db.duplicates():
        print row

    print "\nfiles for one sha1"
    for row in db.filenames('9db39b5c8b9eb70149801f8c9112c3ef50dcd562'):
        print row

