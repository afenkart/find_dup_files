#!/usr/bin/env python
import sqlite3 as lite
import sys, os
import subprocess
import string
import traceback
import logging

TIMESTMP_FMT = ("%H:%M:%S") # no %f for msecs
FORMAT = '%(asctime)s.%(msecs)03d %(name)-5s %(message)s'
logging.basicConfig(format=FORMAT, datefmt=TIMESTMP_FMT, level=logging.INFO)

class Storage:
    def __init__(self, memory):
        self.log = logging.getLogger("Storage")

        if memory:
            self.con = lite.connect(':memory:')
        else:
            self.con = lite.connect('files.db')
        self.con.row_factory = lite.Row
        #self.con.text_factory = str

    def recreate(self):
        self.create_db()

    def create_db(self):
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Files")
        cur.execute("DROP TABLE IF EXISTS Inodes")
        cur.execute("CREATE TABLE Files(id INTEGER PRIMARY KEY, name TEXT, \
                    st_dev INTEGER, st_inode INTEGER, SHA1 Text)")
        # TODO st_dev/st_ino shall be primary key
        cur.execute("CREATE TABLE Inodes(id INTEGER PRIMARY KEY, st_dev INTEGER, \
                    st_inode INTEGER, st_mtime, SHA1 Text)")
        self.con.commit();

    def add_file(self, name, dev, inode, _sha1):
        log = self.log
        try:
            cur = self.con.cursor()
            cur.execute("SELECT * FROM Files WHERE name = ? and st_dev = ? and st_inode = ?",
                        (name.decode('utf-8'), dev, inode))
            if not cur.fetchone():
                log.debug("Adding file name %r", name)
                cur.execute("INSERT INTO Files VALUES(NULL, ?, ?, ?, ?)",
                        (name.decode('utf-8'), dev, inode, _sha1))
            else:
                log.debug("Existing file name %r\n", name)
            self.con.commit();
        except lite.Error, e:
            print "Error %s: name: %s" % (e.args[0], name)
            print traceback.format_exc()
            self.con.rollback()
        except UnicodeDecodeError, e:
            print traceback.format_exc()
            print name


    def lookup_inode(self, dev, inode):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM Inodes WHERE st_dev = ? and st_inode = ?",
                           (dev, inode))
        return cur.fetchone()

    def add_inode(self, dev, inode, mtime, sha1):
        try:
            cur = self.con.cursor()
            if self.lookup_inode(dev, inode):
                cur.execute("UPDATE Inodes SET st_mtime = ?, sha1 = ? WHERE \
                            st_dev = ? and st_inode = ?", (mtime, sha1, dev, inode))
            else:
                cur.execute("INSERT INTO Inodes VALUES(NULL, ?, ?, ?, ?)",
                            (dev, inode, mtime, sha1))
            self.con.commit();
        except lite.Error, e:
            print "Error %s: inode: %s--" % (e.args[0], inode)
            self.con.rollback()
            return False


    def dump(self):
        for line in self.con.iterdump():
            print line

    # TODO duplicate_keys
    def duplicates(self):
        cur = self.con.cursor()
        # Inodes contains no hard links, returns real double disk usage
        return cur.execute("SELECT COUNT(*) Count, sha1, st_dev, st_inode \
                           FROM Inodes \
                           GROUP BY sha1 \
                           HAVING COUNT(*) > 1 \
                           ORDER BY COUNT(*) DESC")

    def filenames(self, sha1):
        cur = self.con.cursor()
        return cur.execute("SELECT Files.sha1, Files.st_dev, Files.st_inode, Files.Name  \
                           FROM Files \
                           WHERE Files.sha1 = ? \
                           ORDER BY sha1, st_dev, st_inode", (sha1,))

    def remove(self, sha1, name):
        try:
            cur = self.con.cursor()
            cur.execute("DELETE FROM Files WHERE sha1 = ? and Name = ?", (sha1, name))
            self.con.commit();
        except lite.Error, e:
            print "Error %s: name: %s" % (e.args[0], name)
            self.con.rollback()



def build_test_corpus(db):
    print "test_corpus"
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', 'ida_-_Vylet_na_prehradu/IMAG0167.jpg')
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', 'et_na_prehradu/IM.jpg')
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', '_na_prehradu/IM.jpg')
    db.add_file('9db39b5c8b9eb70149801f8c9112c3ef50dcd565', 'erehradu/IM.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea2','cii_Empik_hleda_Foxika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea2','i_Empik_hleda_Foxika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea5','i_E_Foxika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea2','i_Empik_hledaFika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea2','i_Empik_hledaFika/P1080538.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea5','i_Foxika/P15038.jpg')
    db.add_file('881d34fd4fc2d55af571e9f8c587108bf4d45ea5','i_Eoxika/P15038.jpg')


if __name__ == "__main__":
    db = Storage(memory=True)
    db.recreate()
    build_test_corpus(db)
    #print db
    #print len(db.all_rows())

    print "\ncollisions"
    for row in db.duplicates():
        print row

    print "\nfiles for one sha1"
    for row in db.filenames('9db39b5c8b9eb70149801f8c9112c3ef50dcd562'):
        print row

    print "\nremove one of above"
    db.remove('9db39b5c8b9eb70149801f8c9112c3ef50dcd562', '_na_prehradu/IM.jpg')
    for row in db.filenames('9db39b5c8b9eb70149801f8c9112c3ef50dcd562'):
        print row
