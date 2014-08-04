#!/usr/bin/env python

"""
Index files in subfolder
"""

import os, stat
import subprocess
import socket
import logging
from crc32 import crc32

from storage import Storage

TIMESTMP_FMT = ("%H:%M:%S") # no %f for msecs
FORMAT = '%(asctime)s.%(msecs)03d %(name)-5s %(message)s'
logging.basicConfig(format=FORMAT, datefmt=TIMESTMP_FMT, level=logging.INFO)

VISIT_LOG = open('visit.log', 'w', buffering=0)

def sha1(name):
    """
    Does not belong here
    1.4GB in 3.8 sec
    """
    ret = subprocess.check_output(["/usr/bin/sha1sum", name],
                                  stderr=subprocess.STDOUT).strip()
    return str(ret).split(' ')[0]

class FindFiles:
    """
    Class FindFiles
    """
    def __init__(self, dbs):
        self.problem_files = []
        self.log = logging.getLogger("FindFiles")
        self.dbs = dbs

    def visit_inode(self, _stat, full_name):
        """
        Check if inode is already indexed, or mtime has changed
        otherwise calculate sha1 and update
        """
        log = self.log
        dbs = self.dbs
        hard_link = dbs.lookup_inode(_stat.st_dev, _stat.st_ino)

        if hard_link:
            mtime = hard_link['st_mtime']

            if mtime == _stat.st_mtime:
                log.debug("hard link %s mtime %r valid, skip...", full_name,
                          mtime)
                return
            else:
                log.info("hard link %s mtime %r changed, reindex...", full_name,
                         mtime)

        try:
            _sha1 = "no-sha1" #sha1(full_name)
            _crc32 = crc32(full_name)
            # stat.n_link
            dbs.add_inode(_stat.st_dev, _stat.st_ino, _stat.st_mtime,
                          _stat.st_size, _crc32, _sha1)
            return
        except subprocess.CalledProcessError:
            print "problem file", full_name
            self.problem_files.append(full_name)


    def visit(self, full_name):
        """
        Check regular file and add to database
        """
        log = self.log
        dbs = self.dbs

        if os.path.islink(full_name):
            # if link is invalid os.stat fails
            log.info("ignore symbolic link: %s", full_name)
            return

        _stat = os.stat(full_name)
        if stat.S_ISSOCK(_stat.st_mode):
            log.info("ignore socket: %s", full_name)
            return
        elif stat.S_ISCHR(_stat.st_mode):
            log.info("ignore character special device file: %s", full_name)
            return
        elif stat.S_ISBLK(_stat.st_mode):
            log.info("ignore block special device file: %s", full_name)
            return
        elif stat.S_ISFIFO(_stat.st_mode):
            log.info("ignore FIFO (named pipe): %s", full_name)
            return
        elif stat.S_ISLNK(_stat.st_mode):
            log.debug("ignore symbolic link: %s", full_name)
            return
        assert stat.S_ISREG(_stat.st_mode)


        try:
            self.visit_inode(_stat, full_name)
            dbs.add_file(full_name, _stat.st_dev, _stat.st_ino)
        except subprocess.CalledProcessError:
            print "problem file", full_name
            self.problem_files.append(full_name)

    def search(self, path):
        """
        Search folder
        """
        for root, dirs, files in os.walk(path):
            if '.git' in dirs:
                dirs.remove('.git')
            if '.svn' in dirs:
                dirs.remove('.svn')

            for fna in files:
                VISIT_LOG.write(("%s/%s\n" % (root, fna)))
                full_name = os.path.join(root, fna)
                self.visit(full_name)


def print_duplicates(dbs):
    """
    Print duplicates with filename
    """
    for row in dbs.duplicates():
        print row

def unit_test():
    """
    Common errors, special files
    ff
    """
    sha1('/etc/passwd')
    try:
        sha1('000_unit_test_not_exist')
    except subprocess.CalledProcessError, err:
        print err

    dbm = Storage(memory=True)
    dbm.recreate()

    _iter = FindFiles(dbm)

    try:
        os.unlink('test-files/test-socket')
    except OSError:
        pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind('test-files/test-socket')
    _iter.search('./test-files')
    sock.close()
    os.unlink('test-files/test-socket')

    os.system("echo a > test-files/hard_link1.txt")
    os.system("cp test-files/hard_link1.txt test-files/copy_hard_link1.txt")
    _iter.search('./test-files')
    os.unlink("test-files/copy_hard_link1.txt")

    print "\nduplicate keys:"
    print_duplicates(dbm)

    os.system("echo a > test-files/crc32-test.txt")
    _crc32 = crc32("test-files/crc32-test.txt")
    os.unlink("test-files/crc32-test.txt")
    print "crc32 %d" % _crc32


if __name__ == "__main__":

    unit_test()
    #os.abort()

    DB2 = Storage(memory=False)
    #DB2.recreate() # TODO

    __ITER__ = FindFiles(DB2)

    DB2.begin_transaction()
    PROBLEM_FILES = __ITER__.search('/home/afenkart')
    # TODO, do not commit every insertion, but do not rollback everything
    DB2.commit_transaction()

    print "\nduplicate keys:"
    print_duplicates(DB2)

    print "\nproblem files:"
    for f in PROBLEM_FILES:
        print f
