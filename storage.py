#!/usr/bin/env python

"""
Map storage/retrieval needs to sqlite
"""

import sqlite3 as lite
import traceback
import logging

TIMESTMP_FMT = ("%H:%M:%S") # no %f for msecs
FORMAT = '%(asctime)s.%(msecs)03d %(name)-5s %(message)s'
logging.basicConfig(format=FORMAT, datefmt=TIMESTMP_FMT, level=logging.INFO)

class Storage:
    """
    Do it all class
    """
    def __init__(self, memory, filename = "files.db"):
        self.log = logging.getLogger("Storage")

        if memory:
            self.con = lite.connect(':memory:')
        else:
            self.con = lite.connect(filename, isolation_level="EXCLUSIVE")
        self.con.row_factory = lite.Row
        #self.con.text_factory = str

    def recreate(self):
        """
        TODO drop
        """
        self.create_db()

    def create_db(self):
        """
        recreates files/inodes table
        """
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Files")
        cur.execute("DROP TABLE IF EXISTS Inodes")
        cur.execute("CREATE TABLE Files(id INTEGER PRIMARY KEY, name TEXT, \
                    st_dev INTEGER, st_inode INTEGER)")
        # TODO st_dev/st_ino shall be primary key
        cur.execute("CREATE TABLE Inodes(id INTEGER PRIMARY KEY, \
                    st_dev INTEGER, st_inode INTEGER, st_mtime FLOAT, \
                    st_size INTEGER, CRC32 Text, SHA1 Text)")
        self.con.commit()

    def add_file(self, name, dev, inode):
        """
        filename -> dev/inode connections
        """
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
            self.con.commit()
        except lite.Error, err:
            print "Error %s: name: %s" % (err.args[0], name)
            print traceback.format_exc()
            self.con.rollback()
        except UnicodeDecodeError, err:
            print traceback.format_exc()
            print name


    def lookup_inode(self, dev, inode):
        """
        check if dev/inode tuple exists
        """
        cur = self.con.cursor()
        cur.execute("SELECT * FROM Inodes WHERE st_dev = ? and st_inode = ?",
                           (dev, inode))
        return cur.fetchone()

    def add_inode(self, dev, inode, mtime, size, crc32, sha1):
        """
        add dev/inode tuple
        """
        try:
            cur = self.con.cursor()
            if self.lookup_inode(dev, inode):
                cur.execute("UPDATE Inodes SET st_mtime = ?, crc32 = ?, \
                                    sha1 = ? \
                            WHERE  st_dev = ? and st_inode = ?",
                            (mtime, crc32, sha1, dev, inode))
            else:
                cur.execute("INSERT INTO Inodes VALUES(NULL, ?, ?, ?, ?, ?, ?)",
                            (dev, inode, mtime, size, crc32, sha1))
            self.con.commit()
        except lite.Error, err:
            print "Error %s: inode: %s--" % (err.args[0], inode)
            self.con.rollback()
            return False


    def update_duplicates(self): # filter by size / number of duplicates
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Duplicates")
        cur.execute("DROP TABLE IF EXISTS Tmp")
        cur.execute("CREATE TABLE Tmp(crc32 TEXT, count INTEGER)")
        cur.execute("CREATE TABLE Duplicates (st_dev INTEGER, \
                    st_inode INTEGER, count INTEGER)")
        # Inodes contains no hard links, returns real double disk usage
        cur.execute("INSERT INTO Tmp(crc32, count) \
                     SELECT crc32, COUNT(*) Count \
                     FROM Inodes \
                     GROUP BY crc32 \
                     HAVING COUNT(*) > 1 \
                     ORDER BY COUNT(*) DESC")
        cur.execute("INSERT INTO Duplicates(st_dev, st_inode, count) \
                     SELECT st_dev, st_inode, tmp.Count \
                     FROM Inodes \
                     JOIN Tmp \
                     ON Inodes.crc32=Tmp.crc32")
        self.con.commit()

    def duplicates(self, size = 0): # filter by size / number of duplicates
        """
        Find inodes with equal crc32/sha1, but different st_dev/st_inode
        and all filenames, including hard links
        """
        cur = self.con.cursor()
        return cur.execute("SELECT Duplicates.count, Inodes.sha1, \
                           Inodes.crc32, Files.st_dev, Files.st_inode, \
                           Inodes.st_size, Files.Name  \
                           FROM Files \
                           JOIN Duplicates \
                           ON Files.st_dev=Duplicates.st_dev AND \
                              Files.st_inode = Duplicates.st_inode \
                           JOIN Inodes \
                           ON Files.st_dev=Inodes.st_dev AND \
                              Files.st_inode = Inodes.st_inode \
                           WHERE Inodes.st_size > ? \
                           ORDER BY Duplicates.count, Inodes.sha1, \
                                    Inodes.crc32, Inodes.st_size, Files.Name \
                           ", (size,))

    def remove(self, sha1, name):
        """
        non-functional
        """
        try:
            cur = self.con.cursor()
            cur.execute("DELETE FROM Files WHERE sha1 = ? and Name = ?",
                        (sha1, name))
            self.con.commit()
        except lite.Error, err:
            print "Error %s: name: %s" % (err.args[0], name)
            self.con.rollback()



def unit_test():
    """
    unit test
    """
    dbm = Storage(memory=True)
    dbm.recreate()
    #build_test_corpus(dbm)

    print "\ncollisions"
    for row in dbm.duplicates():
        print row

    print "\nremove one of above"
    for row in dbm.duplicates():
        print row


if __name__ == "__main__":
    unit_test()
