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

    def begin_transaction(self):
        pass # implicit by non select statement

    def commit_transaction(self):
        self.con.commit()

    def rollback_transaction(self):
        self.con.rollback()

    def create_db(self):
        """
        recreates files/inodes table
        """
        cur = self.con.cursor()
        cur.execute("DROP TABLE IF EXISTS Files")
        cur.execute("DROP TABLE IF EXISTS Inodes")
        cur.execute("CREATE TABLE Files(name TEXT PRIMARY KEY, st_dev INTEGER, st_inode INTEGER)")
        # constraint fk_files_dev_inode foreign key (st_dev, st_inode) reference inode(st_dev, st_inode)
        cur.execute("CREATE TABLE Inodes(st_dev INTEGER, st_inode INTEGER, crc32 INTEGER, sha1 Text, st_mtime FLOAT, st_size INTEGER, constraint inodes_pk PRIMARY KEY (st_dev, st_inode))")

        # use the index luke!
        # CREATE INDEX inodes_crc32_idx ON Inodes (crc32);
        # CREATE INDEX inodes_inodes_idx ON Inodes (st_dev, st_inode);
        # CREATE INDEX files_inodes_idx ON Files(st_dev, st_inode);

        cur.execute("CREATE VIEW FileInodeView AS SELECT i.st_dev, i.st_inode, i.crc32, i.sha1, i.st_size, f.name FROM Inodes i JOIN Files f ON f.st_dev = i.st_dev and i.st_inode = f.st_inode")
        self.con.commit()

    def lookup_file(self, name):
        """
        check if dev/inode tuple exists
        """
        cur = self.con.cursor()
        cur.execute("SELECT * FROM Files WHERE name = ?", (name.decode('utf-8'),))
        return cur.fetchone()

    def add_file(self, name, dev, inode):
        """
        filename -> dev/inode connections
        """
        log = self.log
        try:
            f = self.lookup_file(name)

            if f and (f['st_inode'] == inode and f['st_dev'] == dev):
                # nothing to be done
                return

            cur = self.con.cursor()
            if not f:
                log.debug("Adding file name %r", name)
                cur.execute("INSERT INTO Files VALUES(?, ?, ?)",
                        (name.decode('utf-8'), dev, inode))
            else:
                # inode/dev tuple changed
                cur.execute("UPDATE Files SET st_dev = ?, st_inode = ? WHERE name = ?",
                            (dev, inode, name))
            #self.con.commit()
        except lite.Error, err:
            print "Error %s: name: %s" % (err.args[0], name)
            print traceback.format_exc()
            #self.con.rollback()
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
                cur.execute("UPDATE Inodes SET crc32 = ?, sha1 = ?, st_mtime = ?, \
                                st_size = ? \
                            WHERE st_dev = ? and st_inode = ?",
                            (crc32, sha1, mtime, size, dev, inode))
            else:
                cur.execute("INSERT INTO Inodes VALUES(?, ?, ?, ?, ?, ?)",
                            (dev, inode, crc32, sha1, mtime, size))
            #self.con.commit()
        except lite.Error, err:
            print "Error %s: inode: %s--" % (err.args[0], inode)
            #self.con.rollback()
            return False

    def files_by_crc32(self, crc32):
        cur = self.con.cursor()
        return cur.execute("SELECT * FROM FileInodeView WHERE crc32 = ?", (crc32,))

    def duplicates(self, size = 0): # filter by size / number of duplicates
        """
        Find inodes with equal crc32/sha1, but different st_dev/st_inode
        and all filenames, including hard links
        """
        cur = self.con.cursor()
        # search duplicates on Inodes, will not count hardlinks, which is
        # confusing if the top level view in the gui says duplicate count is 2,
        # but in the detail view there are suddenly 3 files
        return cur.execute("Select COUNT() Count, * FROM FileInodeView WHERE st_size > ? GROUP BY crc32 HAVING COUNT(*) > 1 ORDER BY st_size desc, count desc, name", (size,))

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
