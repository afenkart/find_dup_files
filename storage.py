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
    def __init__(self, memory, filename = "files.db"):
        self.log = logging.getLogger("Storage")

        if memory:
            self.con = lite.connect(':memory:')
        else:
            self.con = lite.connect(filename)
        self.con.row_factory = lite.Row
        #self.con.text_factory = str

    def recreate(self):
        self.create_db()

    def create_db(self):
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Files")
        cur.execute("DROP TABLE IF EXISTS Inodes")
        cur.execute("CREATE TABLE Files(id INTEGER PRIMARY KEY, name TEXT, \
                    st_dev INTEGER, st_inode INTEGER)")
        # TODO st_dev/st_ino shall be primary key
        cur.execute("CREATE TABLE Inodes(id INTEGER PRIMARY KEY, \
                    st_dev INTEGER, st_inode INTEGER, st_mtime FLOAT, \
                    st_size INTEGER, CRC32 Text, SHA1 Text)")
        self.con.commit();

    def add_file(self, name, dev, inode):
        log = self.log
        try:
            cur = self.con.cursor()
            cur.execute("SELECT * FROM Files WHERE name = ? AND st_dev = ? AND \
                        st_inode = ?", (name.decode('utf-8'), dev, inode))
            if not cur.fetchone():
                log.debug("Adding file name %r", name)
                cur.execute("INSERT INTO Files VALUES(NULL, ?, ?, ?)",
                        (name.decode('utf-8'), dev, inode))
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

    def add_inode(self, dev, inode, mtime, size, sha1):
        try:
            cur = self.con.cursor()
            if self.lookup_inode(dev, inode):
                cur.execute("UPDATE Inodes SET st_mtime = ?, sha1 = ? WHERE \
                            st_dev = ? and st_inode = ?", (mtime, sha1, dev, inode))
            else:
                cur.execute("INSERT INTO Inodes VALUES(NULL, ?, ?, ?, ?, ?, ?)",
                            (dev, inode, mtime, size, "no-crc32", sha1))
            self.con.commit();
        except lite.Error, e:
            print "Error %s: inode: %s--" % (e.args[0], inode)
            self.con.rollback()
            return False


    def duplicates(self): # filter by size / number of duplicates
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Duplicates")
        cur.execute("DROP TABLE IF EXISTS Tmp")
        cur.execute("CREATE TABLE Tmp(sha1 INTEGER, count INTEGER)")
        cur.execute("CREATE TABLE Duplicates (st_dev INTEGER, st_inode INTEGER, \
                    count INTEGER)")
        # Inodes contains no hard links, returns real double disk usage
        cur.execute("INSERT INTO Tmp(sha1, count) \
                     SELECT sha1, COUNT(*) Count \
                     FROM Inodes \
                     GROUP BY sha1 \
                     HAVING COUNT(*) > 1 \
                     ORDER BY COUNT(*) DESC")
        cur.execute("INSERT INTO Duplicates(st_dev, st_inode, count) \
                     SELECT st_dev, st_inode, tmp.Count \
                     FROM Inodes \
                     JOIN Tmp \
                     ON Inodes.sha1=Tmp.sha1")

        return cur.execute("SELECT Duplicates.count, Inodes.sha1, Inodes.crc32, \
                           Files.st_dev, Files.st_inode, Files.Name  \
                           FROM Files \
                           JOIN Duplicates \
                           ON Files.st_dev=Duplicates.st_dev AND \
                              Files.st_inode = Duplicates.st_inode \
                           JOIN Inodes \
                           ON Files.st_dev=Inodes.st_dev AND \
                              Files.st_inode = Inodes.st_inode \
                           ORDER BY Duplicates.count, Files.Name")

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
