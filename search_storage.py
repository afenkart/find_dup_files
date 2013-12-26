#!/usr/bin/env python

"""
Index files in subfolder
"""


import os, stat
import subprocess
import traceback
import socket
import logging

from storage import Storage

TIMESTMP_FMT = ("%H:%M:%S") # no %f for msecs
FORMAT = '%(asctime)s.%(msecs)03d %(name)-5s %(message)s'
logging.basicConfig(format=FORMAT, datefmt=TIMESTMP_FMT, level=logging.INFO)

DB = Storage(memory=False)
DB.recreate()

VISIT_LOG = open('visit.log', 'w', buffering = 0)

def sha1(name):
    """
    Does not belong here
    """
    log = logging.getLogger("sha1")
    ret = subprocess.check_output(["/usr/bin/sha1sum", name],
                                 stderr=subprocess.STDOUT)
    return str(ret).split(' ')[0]


class FindFiles:
    """
    Class FindFiles
    """
    def __init__(self):
        self.problem_files = []
        self.log = logging.getLogger("FindFiles")

    def process_inode(self, _stat, full_name):
        """
        Check if inode is already indexed, or mtime has changed
        """
        log = self.log
        hard_link = DB.lookup_inode(_stat.st_dev, _stat.st_ino)

        if hard_link:
            mtime = hard_link['st_mtime']

            if mtime == _stat.st_mtime:
                log.info("hard link %s mtime %r valid, skip...", full_name, mtime)
                return
            else:
                log.info("hard link %s mtime %r changed, reindex...", full_name, mtime)

        try:
            _sha1 = sha1(full_name)
            DB.add_inode(_stat.st_dev, _stat.st_ino, _stat.st_mtime, _sha1)
        except subprocess.CalledProcessError:
            print "problem file", full_name
            self.problem_files.append(full_name)


    def visit(self, full_name):
        """
        Check regular file and add to database
        """
        log = self.log

        if os.path.islink(full_name):
            # if link is invalid os.stat fails
            log.info("ignore symbolic link: %s" % full_name)
            return

        _stat = os.stat(full_name)
        if stat.S_ISSOCK(_stat.st_mode):
            log.info("ignore socket: %s", full_name)
            return
        elif stat.S_ISCHR(_stat.st_mode):
            log.info("ignore character special device file: %s" % full_name)
            return
        elif stat.S_ISBLK(_stat.st_mode):
            log.info("ignore block special device file: %s" % full_name)
            return
        elif stat.S_ISFIFO(_stat.st_mode):
            log.info("ignore FIFO (named pipe): %s" % full_name)
            return
        elif stat.S_ISLNK(_stat.st_mode):
            log.info("ignore symbolic link: %s" % full_name)
            return
        assert(stat.S_ISREG(_stat.st_mode))

        try:
            _sha1 = sha1(full_name)
            DB.add_file(_sha1, full_name)
            self.process_inode(_stat, full_name)
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


__ITER__ = FindFiles()

def unit_test():
    """
    Common errors, special files
    """
    sha1('/etc/passwd')
    try:
        sha1('000_unit_test_not_exist')
    except subprocess.CalledProcessError, e:
        print e

    try:
        os.unlink('test-files/test-socket')
    except OSError:
        pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind('test-files/test-socket')
    __ITER__.search('./test-files')
    sock.close()
    os.unlink('test-files/test-socket')

    os.system("echo a > test-files/hard_link1.txt")
    __ITER__.search('./test-files')

unit_test()


PROBLEM_FILES = __ITER__.search('/home/afenkart')


print "\nduplicate keys:"
for f in DB.duplicates():
    sha1 = f['sha1']
    print sha1
    for g in DB.filenames(sha1):
        print "\t", g

print "\nproblem files:"
for f in PROBLEM_FILES:
    print f


#if __name__ == "__main__"
