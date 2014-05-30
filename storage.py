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
        cur.execute("CREATE TABLE Files(name TEXT, st_dev INTEGER, st_inode INTEGER)")
        # constraint pk_files_name PRIMARY KEY (name)
        # constraint fk_files_dev_inode foreign key (st_dev, st_inode) reference inode(st_dev, st_inode)
        cur.execute("CREATE TABLE Inodes(st_dev INTEGER, st_inode INTEGER, crc32 INTEGER, sha1 Text, st_mtime FLOAT, st_size INTEGER, constraint inodes_pk PRIMARY KEY (st_dev, st_inode))")

        # use the index luke!
        # CREATE INDEX inodes_crc32_idx ON Inodes (crc32);
        # CREATE INDEX inodes_inodes_idx ON Inodes (st_dev, st_inode);
        # CREATE INDEX files_inodes_idx ON Files(st_dev, st_inode);

        cur.execute("CREATE VIEW FileInodeView AS SELECT i.st_dev, i.st_inode, i.crc32, i.sha1, i.st_size, f.name FROM Inodes i JOIN Files f ON f.st_dev = i.st_dev and i.st_inode = f.st_inode")
        cur.execute("CREATE VIEW DuplicatesView AS SELECT st_dev, st_inode, crc32, sha1, COUNT(*) Count, st_size, name FROM FileInodeView GROUP BY crc32 HAVING COUNT(*) > 1")
        #cur.execute("CREATE VIEW DuplicatesView AS SELECT st_dev, st_inode, crc32, COUNT(*) Count, st_size FROM Inodes GROUP BY crc32 HAVING COUNT(*) > 1")
        # search duplicates on Inodes, will not count hardlinks, which is confusing if count is 2, but in the gui suddenly there are 3 files
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

    def filename_by_crc32(self, crc32):
        cur = self.con.cursor()
        return cur.execute("SELECT name FROM Files \
                           JOIN Inodes \
                           ON Files.st_dev=Inodes.st_dev AND \
                              Files.st_inode = Inodes.st_inode \
                           WHERE crc32 = ?", (crc32,))

    def duplicates(self, size = 0): # filter by size / number of duplicates
        """
        Find inodes with equal crc32/sha1, but different st_dev/st_inode
        and all filenames, including hard links
        """
        cur = self.con.cursor()
        #return cur.execute("SELECT * from DuplicatesView WHERE st_size > ? ORDER BY st_size desc, count desc, name", (size,))
        return cur.execute("SELECT Count() as count, * from (SELECT * FROM Inodes WHERE st_size > ?) as d JOIN Files f ON d.st_dev = f.st_dev and d.st_inode = f.st_inode  GROUP BY crc32 HAVING count() > 1 ORDER BY d.st_size desc, count desc, f.name", (size,));

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
